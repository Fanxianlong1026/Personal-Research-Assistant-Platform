"""
论文元数据导入：根据 DOI 或 arXiv 标识，从 Crossref / arXiv 拉取并归一化为表单字段。
返回的 dict 键与前端表单一致：title/authors/abstract/journal/year/doi/url。
"""
import re
import xml.etree.ElementTree as ET

import httpx

_ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _clean(text: str) -> str:
    """去除 JATS/HTML 标签与多余空白。"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _detect_arxiv_id(identifier: str):
    """从输入中提取 arXiv id（如 2301.12345 或 hep-th/9901001），非 arXiv 返回 None。"""
    s = identifier.strip()
    m = re.search(r"arxiv\.org/(?:abs|pdf)/([^\s?#]+?)(?:v\d+)?(?:\.pdf)?(?:[?#].*)?$", s, re.I)
    if m:
        return m.group(1)
    m = re.match(r"(?:arxiv:)?\s*(\d{4}\.\d{4,5})(?:v\d+)?$", s, re.I)
    if m:
        return m.group(1)
    m = re.match(r"(?:arxiv:)?\s*([a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?$", s, re.I)
    if m:
        return m.group(1)
    return None


def _extract_doi(identifier: str):
    """从输入中提取 DOI（10.xxxx/...），无则返回 None。"""
    m = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", identifier, re.I)
    return m.group(0).rstrip(".") if m else None


async def _fetch_arxiv(arxiv_id: str) -> dict:
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    root = ET.fromstring(resp.text)
    entry = root.find("atom:entry", _ARXIV_NS)
    if entry is None or entry.find("atom:title", _ARXIV_NS) is None:
        raise ValueError("未找到该 arXiv 论文")
    title = _clean(entry.findtext("atom:title", default="", namespaces=_ARXIV_NS))
    summary = _clean(entry.findtext("atom:summary", default="", namespaces=_ARXIV_NS))
    authors = [
        _clean(a.findtext("atom:name", default="", namespaces=_ARXIV_NS))
        for a in entry.findall("atom:author", _ARXIV_NS)
    ]
    published = entry.findtext("atom:published", default="", namespaces=_ARXIV_NS)
    year = int(published[:4]) if published[:4].isdigit() else None
    doi = _clean(entry.findtext("{http://arxiv.org/schemas/atom}doi", default="", namespaces={}))
    journal = _clean(entry.findtext("{http://arxiv.org/schemas/atom}journal_ref", default="", namespaces={}))
    return {
        "title": title,
        "authors": ", ".join(a for a in authors if a),
        "abstract": summary,
        "journal": journal or "arXiv",
        "year": year,
        "doi": doi,
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",  # arXiv PDF 直链，可下载
    }


async def _fetch_crossref(doi: str) -> dict:
    url = f"https://api.crossref.org/works/{doi}"
    headers = {"User-Agent": "ResearchAssistant/1.0 (mailto:research@example.com)"}
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 404:
            raise ValueError("未找到该 DOI 对应的论文")
        resp.raise_for_status()
    msg = resp.json().get("message", {})
    title_list = msg.get("title") or []
    title = _clean(title_list[0]) if title_list else ""
    if not title:
        raise ValueError("该 DOI 未返回有效标题")
    authors = []
    for a in msg.get("author", []) or []:
        name = " ".join(p for p in [a.get("given", ""), a.get("family", "")] if p).strip()
        if name:
            authors.append(name)
    container = msg.get("container-title") or []
    journal = _clean(container[0]) if container else ""
    year = None
    for key in ("published", "published-print", "published-online", "issued"):
        parts = (msg.get(key) or {}).get("date-parts") or []
        if parts and parts[0] and isinstance(parts[0][0], int):
            year = parts[0][0]
            break
    # Crossref 的 link 里偶有开放获取 PDF 直链（多数为付费墙，尽力而为）
    pdf_url = ""
    for link in msg.get("link", []) or []:
        if link.get("content-type") == "application/pdf" and link.get("URL"):
            pdf_url = link["URL"]
            break
    return {
        "title": title,
        "authors": ", ".join(authors),
        "abstract": _clean(msg.get("abstract", "")),
        "journal": journal,
        "year": year,
        "doi": msg.get("DOI", doi),
        "url": msg.get("URL", ""),
        "pdf_url": pdf_url,
    }


async def fetch_metadata(identifier: str) -> dict:
    """根据 DOI 或 arXiv 标识拉取元数据。优先按 arXiv 识别，其次 DOI。"""
    identifier = (identifier or "").strip()
    if not identifier:
        raise ValueError("请输入 DOI 或 arXiv 链接/编号")

    arxiv_id = _detect_arxiv_id(identifier)
    if arxiv_id:
        return await _fetch_arxiv(arxiv_id)

    doi = _extract_doi(identifier)
    if doi:
        return await _fetch_crossref(doi)

    raise ValueError("无法识别输入，请粘贴有效的 DOI 或 arXiv 链接/编号")


async def download_pdf(url: str, max_bytes: int) -> bytes:
    """从 url 下载 PDF 并校验。失败抛 ValueError（供路由转 4xx），返回原始字节。"""
    if not url:
        raise ValueError("缺少 PDF 链接")
    headers = {"User-Agent": "ResearchAssistant/1.0 (mailto:research@example.com)"}
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        raise ValueError(f"下载失败：{e}")
    content = resp.content
    if len(content) > max_bytes:
        raise ValueError("PDF 文件过大，超过上传上限")
    # 校验确实是 PDF：按 content-type 或文件头 %PDF 判断（付费墙常返回 HTML 登录页）
    ctype = resp.headers.get("content-type", "").lower()
    if "application/pdf" not in ctype and not content[:5].startswith(b"%PDF"):
        raise ValueError("该链接未返回 PDF（可能需要订阅/登录或无开放全文）")
    return content
