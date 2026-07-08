"""
BibTeX 导出/导入（零依赖）。
- to_bibtex: 把 Paper 列表序列化为 .bib 文本
- parse_bibtex: 解析 .bib 文本为论文字段 dict 列表（供建库）
"""
import re


def _cite_key(paper, used: set) -> str:
    """生成 citation key：首作者姓 + 年份 + 标题首词，去重。"""
    authors = (paper.authors or "").strip()
    first = authors.split(",")[0].strip() if authors else ""
    family = first.split()[-1] if first else "anon"
    year = str(paper.year) if paper.year else "nd"
    title_word = ""
    for w in re.findall(r"[A-Za-z一-鿿]+", paper.title or ""):
        title_word = w
        break
    base = re.sub(r"[^0-9A-Za-z一-鿿]", "", f"{family}{year}{title_word}") or "ref"
    key = base
    i = 1
    while key in used:
        i += 1
        key = f"{base}{i}"
    used.add(key)
    return key


def _authors_to_bib(authors: str) -> str:
    """逗号分隔的作者串转 BibTeX 的 ' and ' 分隔。"""
    parts = [a.strip() for a in (authors or "").split(",") if a.strip()]
    return " and ".join(parts)


def to_bibtex(papers) -> str:
    """把 Paper 列表（ORM 对象或具备同名属性的对象）序列化为 .bib 文本。"""
    used: set = set()
    blocks = []
    for p in papers:
        key = _cite_key(p, used)
        fields = []
        if p.title:
            fields.append(("title", p.title))
        authors = _authors_to_bib(p.authors)
        if authors:
            fields.append(("author", authors))
        if p.year:
            fields.append(("year", str(p.year)))
        if p.journal:
            fields.append(("journal", p.journal))
        if p.doi:
            fields.append(("doi", p.doi))
        if p.url:
            fields.append(("url", p.url))
        if p.abstract:
            fields.append(("abstract", p.abstract))
        body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields)
        blocks.append(f"@article{{{key},\n{body}\n}}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def _split_entries(text: str):
    """按顶层 @type{...} 切分条目，正确匹配大括号嵌套。"""
    entries = []
    i = 0
    n = len(text)
    while i < n:
        at = text.find("@", i)
        if at == -1:
            break
        brace = text.find("{", at)
        if brace == -1:
            break
        etype = text[at + 1:brace].strip().lower()
        depth = 0
        j = brace
        while j < n:
            c = text[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if depth != 0:
            break
        entries.append((etype, text[brace + 1:j]))
        i = j + 1
    return entries


def _strip_value(v: str) -> str:
    v = v.strip().rstrip(",").strip()
    if v.startswith("{") and v.endswith("}"):
        v = v[1:-1]
    elif v.startswith('"') and v.endswith('"'):
        v = v[1:-1]
    return re.sub(r"\s+", " ", v).strip()


def _parse_fields(inner: str) -> dict:
    """解析条目内部 key = {value} / key = "value" / key = value 列表。"""
    fields = {}
    # 跳过 citation key（第一个逗号前）
    comma = inner.find(",")
    body = inner[comma + 1:] if comma != -1 else ""
    i = 0
    n = len(body)
    while i < n:
        eq = body.find("=", i)
        if eq == -1:
            break
        key = body[i:eq].strip().lower()
        j = eq + 1
        while j < n and body[j] in " \t\r\n":
            j += 1
        if j >= n:
            break
        if body[j] == "{":
            depth = 0
            start = j
            while j < n:
                if body[j] == "{":
                    depth += 1
                elif body[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            raw = body[start:j + 1]
            i = j + 1
        elif body[j] == '"':
            start = j
            j += 1
            while j < n and body[j] != '"':
                j += 1
            raw = body[start:j + 1]
            i = j + 1
        else:
            start = j
            while j < n and body[j] != ",":
                j += 1
            raw = body[start:j]
            i = j
        if key:
            fields[key] = _strip_value(raw)
        nxt = body.find(",", i)
        if nxt == -1:
            break
        i = nxt + 1
    return fields


def parse_bibtex(text: str):
    """解析 .bib 文本，返回论文字段 dict 列表（键与 PaperCreate 一致）。"""
    results = []
    for _etype, inner in _split_entries(text or ""):
        f = _parse_fields(inner)
        title = f.get("title", "").strip()
        if not title:
            continue
        raw_authors = " ".join(f.get("author", "").split())
        names = []
        for a in re.split(r"\s+and\s+", raw_authors):
            a = a.strip()
            if not a:
                continue
            if "," in a:  # BibTeX "Family, Given" -> "Given Family"
                family, _, given = a.partition(",")
                a = f"{given.strip()} {family.strip()}".strip()
            names.append(a)
        authors = ", ".join(names)
        year = None
        ym = re.search(r"\d{4}", f.get("year", ""))
        if ym:
            year = int(ym.group(0))
        results.append({
            "title": title,
            "authors": authors,
            "abstract": f.get("abstract", ""),
            "journal": f.get("journal", "") or f.get("booktitle", ""),
            "year": year,
            "doi": f.get("doi", ""),
            "url": f.get("url", ""),
        })
    return results
