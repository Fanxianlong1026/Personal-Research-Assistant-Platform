"""
全文搜索索引（SQLite FTS5）

中文检索方案：SQLite 内置分词器对中文支持差——unicode61 会把一整段中文当成
一个 token（无法子串匹配），trigram 又要求查询至少 3 个字符（"模型""实验" 这类
2 字常用词搜不到）。这里采用「单字分词 + unicode61」：把中文逐字用空格切开后
入索引，每个汉字成为一个 token；查询时把中文词转成相邻短语（phrase）匹配，这样
2 字词也能命中，且保持子串语义。英文按词（token）匹配。

索引维护：启动时 rebuild_all 全量重建；运行时由 papers/notes 路由的增删改调用
index_* / delete_* 增量更新。
"""
import re
from typing import List, Dict

from sqlalchemy import text
from sqlalchemy.orm import Session

# CJK 统一表意文字及扩展区、兼容区
_CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
# FTS5 查询语法中的特殊字符，构造 MATCH 时需剔除，避免语法错误/注入
_FTS_SPECIAL = re.compile(r'["()*:^]')


def _segment(s: str) -> str:
    """把文本中的每个汉字用空格隔开，英文/数字保持原样。"""
    if not s:
        return ""
    out = []
    for ch in s:
        if _CJK.match(ch):
            out.append(" " + ch + " ")
        else:
            out.append(ch)
    return re.sub(r"\s+", " ", "".join(out)).strip()


def build_match_query(q: str):
    """把用户查询转换为安全的 FTS5 MATCH 表达式。

    每个空格分隔的词 → 一个「分词后的引号短语」，多个词之间为 AND。
    例： "BERT模型 实验" -> '"BERT 模 型" "实 验"'
    """
    if not q:
        return None
    phrases = []
    for term in q.split():
        clean = _FTS_SPECIAL.sub("", term)
        seg = _segment(clean)
        if seg:
            phrases.append('"' + seg + '"')
    return " ".join(phrases) if phrases else None


# ========== 索引表 DDL ==========
_DDL = [
    "CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(content, tokenize='unicode61')",
    "CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(content, tokenize='unicode61')",
]


def ensure_tables(db: Session) -> None:
    for stmt in _DDL:
        db.execute(text(stmt))
    db.commit()


def _paper_index_text(p) -> str:
    parts = [p.title, p.authors, p.abstract, p.journal, p.doi, p.notes_text,
             getattr(p, "fulltext", "")]
    return _segment(" ".join(str(x) for x in parts if x))


def _note_index_text(n) -> str:
    parts = [n.title, n.content, n.folder]
    return _segment(" ".join(str(x) for x in parts if x))


def index_paper(db: Session, paper) -> None:
    db.execute(text("DELETE FROM papers_fts WHERE rowid = :id"), {"id": paper.id})
    db.execute(
        text("INSERT INTO papers_fts(rowid, content) VALUES (:id, :c)"),
        {"id": paper.id, "c": _paper_index_text(paper)},
    )
    db.commit()


def delete_paper_index(db: Session, paper_id: int) -> None:
    db.execute(text("DELETE FROM papers_fts WHERE rowid = :id"), {"id": paper_id})
    db.commit()


def index_note(db: Session, note) -> None:
    db.execute(text("DELETE FROM notes_fts WHERE rowid = :id"), {"id": note.id})
    db.execute(
        text("INSERT INTO notes_fts(rowid, content) VALUES (:id, :c)"),
        {"id": note.id, "c": _note_index_text(note)},
    )
    db.commit()


def delete_note_index(db: Session, note_id: int) -> None:
    db.execute(text("DELETE FROM notes_fts WHERE rowid = :id"), {"id": note_id})
    db.commit()


def rebuild_all(db: Session) -> None:
    """全量重建索引（启动时调用），保证索引与数据一致。"""
    from app.models.paper import Paper
    from app.models.note import Note

    ensure_tables(db)
    db.execute(text("DELETE FROM papers_fts"))
    db.execute(text("DELETE FROM notes_fts"))

    for p in db.query(Paper).all():
        db.execute(
            text("INSERT INTO papers_fts(rowid, content) VALUES (:id, :c)"),
            {"id": p.id, "c": _paper_index_text(p)},
        )
    for n in db.query(Note).all():
        db.execute(
            text("INSERT INTO notes_fts(rowid, content) VALUES (:id, :c)"),
            {"id": n.id, "c": _note_index_text(n)},
        )
    db.commit()


def _make_snippet(raw: str, terms: List[str], width: int = 80) -> str:
    """在原文中定位首个命中词，截取上下文片段（纯文本，前端再做高亮）。"""
    if not raw:
        return ""
    flat = re.sub(r"\s+", " ", raw).strip()
    low = flat.lower()
    pos = -1
    for t in terms:
        if not t:
            continue
        i = low.find(t.lower())
        if i != -1 and (pos == -1 or i < pos):
            pos = i
    if pos == -1:
        return flat[:width] + ("…" if len(flat) > width else "")
    start = max(0, pos - width // 3)
    end = min(len(flat), pos + width)
    snippet = flat[start:end]
    if start > 0:
        snippet = "…" + snippet
    if end < len(flat):
        snippet = snippet + "…"
    return snippet


def search(db: Session, q: str, types: set, limit: int = 30) -> List[Dict]:
    """跨字段、跨实体全文检索，返回按 bm25 相关度排序的结果。"""
    mq = build_match_query(q)
    if not mq:
        return []

    terms = [t for t in q.split() if t]
    results: List[Dict] = []

    if "papers" in types:
        from app.models.paper import Paper

        rows = db.execute(
            text(
                "SELECT rowid, bm25(papers_fts) AS score FROM papers_fts "
                "WHERE papers_fts MATCH :q ORDER BY score LIMIT :lim"
            ),
            {"q": mq, "lim": limit},
        ).fetchall()
        if rows:
            score_map = {r[0]: r[1] for r in rows}
            papers = db.query(Paper).filter(Paper.id.in_(list(score_map.keys()))).all()
            for p in papers:
                raw = " ".join(
                    str(x) for x in [p.title, p.authors, p.abstract, p.journal,
                                     p.notes_text, getattr(p, "fulltext", "")] if x
                )
                results.append({
                    "type": "paper",
                    "id": p.id,
                    "title": p.title,
                    "snippet": _make_snippet(raw, terms),
                    "score": score_map[p.id],
                    "meta": {
                        "authors": p.authors,
                        "year": p.year,
                        "journal": p.journal,
                        "status": p.status,
                    },
                })

    if "notes" in types:
        from app.models.note import Note

        rows = db.execute(
            text(
                "SELECT rowid, bm25(notes_fts) AS score FROM notes_fts "
                "WHERE notes_fts MATCH :q ORDER BY score LIMIT :lim"
            ),
            {"q": mq, "lim": limit},
        ).fetchall()
        if rows:
            score_map = {r[0]: r[1] for r in rows}
            notes = db.query(Note).filter(Note.id.in_(list(score_map.keys()))).all()
            for n in notes:
                raw = " ".join(str(x) for x in [n.title, n.content] if x)
                results.append({
                    "type": "note",
                    "id": n.id,
                    "title": n.title,
                    "snippet": _make_snippet(raw, terms),
                    "score": score_map[n.id],
                    "meta": {
                        "folder": n.folder,
                        "paper_id": n.paper_id,
                    },
                })

    # bm25 分值越小越相关，统一升序
    results.sort(key=lambda r: r["score"])
    return results[:limit]
