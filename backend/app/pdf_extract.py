"""
PDF 正文提取（PyMuPDF / fitz）

用于把上传的论文 PDF 抽成纯文本，写入 papers.fulltext 并进 FTS5 索引，
让全文搜索能命中正文，而不仅是标题/摘要。

依赖 PyMuPDF（装在 conda 环境 pytorch_nightly，backend/venv 未装）。
import 做成软依赖：缺库时 extract_text 返回空串而非抛错，保证纯 CRUD 流程
（用 venv 启动）不会因为缺 fitz 而崩溃。
"""
from pathlib import Path

try:
    import fitz  # PyMuPDF
    _AVAILABLE = True
except ImportError:  # venv 无 PyMuPDF 时降级
    fitz = None
    _AVAILABLE = False

# 单篇正文进索引的字符上限，防止超长 PDF 把 FTS5 表撑爆
_MAX_CHARS = 500_000


def is_available() -> bool:
    return _AVAILABLE


def extract_text(file_path: str) -> str:
    """抽取 PDF 全文为纯文本；失败或缺库时返回空串（绝不抛错）。"""
    if not _AVAILABLE or not file_path:
        return ""
    p = Path(file_path)
    if not p.exists() or p.suffix.lower() != ".pdf":
        return ""
    try:
        parts = []
        total = 0
        with fitz.open(str(p)) as doc:
            for page in doc:
                t = page.get_text("text")
                if not t:
                    continue
                parts.append(t)
                total += len(t)
                if total >= _MAX_CHARS:
                    break
        return "".join(parts)[:_MAX_CHARS].strip()
    except Exception:
        return ""
