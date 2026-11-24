#!/usr/bin/env python3
"""Generate a self-contained, human-readable HTML view for the risk-knowledge-base skill.

Reads ``skills/risk-knowledge-base/manifest.json`` + the markdown docs and emits a
single OFFLINE HTML file (embedded CSS/JS, no network fetch) featuring:

  * left category tree (mirrors the skill's NN_<category> folders, incl. empty ones)
  * MagiBook-style card gallery (title / summary / doc_type badge / tags)
  * reading view with SQL/code syntax highlighting (pygments)
  * top search box filtering cards by title / tags / summary

No new dependencies: mistune (already vendored) + pygments + stdlib. The output can
be opened directly in a browser, or embedded in Jupyter via
``IPython.display.IFrame(path, width='100%', height=800)``.

Regenerate after editing the KB:  ``.venv/bin/python scripts/kb_view.py``
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

import mistune
from mistune import HTMLRenderer
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

PROJECT = Path(__file__).resolve().parent.parent
SKILL_DIR = PROJECT / "skills" / "risk-knowledge-base"
MANIFEST = SKILL_DIR / "manifest.json"

_FRONTMATTER_RE = re.compile(r"^---\s*\r?\n.*?\r?\n---\s*(?:\r?\n|$)", re.DOTALL)
_CAT_DIR_RE = re.compile(r"^\d{2}_")
_TITLE_TAG_RE = re.compile(r"<title>.*?</title>", re.DOTALL)


class _Highlight(HTMLRenderer):
    """HTML renderer that syntax-highlights fenced code blocks via pygments."""

    def block_code(self, code: str, info: str | None = None) -> str:
        lang = (info or "").strip().split(None, 1)[0] if info else ""
        if lang:
            try:
                lexer = get_lexer_by_name(lang, stripall=False)
                return highlight(code, lexer, HtmlFormatter())
            except ClassNotFound:
                pass
        return "<pre class='code-plain'><code>%s</code></pre>" % html.escape(code)


_md = mistune.create_markdown(
    renderer=_Highlight(escape=False),
    plugins=["table", "strikethrough", "url"],
)


def _strip_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1).lstrip()


def _clean_body(text: str) -> str:
    """Drop lark-provenance <title> tags that would otherwise leak into the DOM."""
    return _TITLE_TAG_RE.sub("", text)


def _category_label(dirname: str) -> str:
    """``01_风控总览`` -> ``风控总览`` (strip the ordering prefix)."""
    return _CAT_DIR_RE.sub("", dirname, count=1)


def _load_docs() -> list[dict]:
    items = json.loads(MANIFEST.read_text(encoding="utf-8"))
    docs: list[dict] = []
    for i, it in enumerate(items):
        rel = it["path"]
        prefix = rel.split("/", 1)[0]
        raw = (SKILL_DIR / rel).read_text(encoding="utf-8")
        body_html = _md(_clean_body(_strip_frontmatter(raw)))
        docs.append(
            {
                "id": f"doc{i}",
                "title": it.get("title", ""),
                "cat_dir": prefix,
                "category": it.get("category", ""),
                "doc_type": it.get("doc_type", ""),
                "tags": it.get("tags", []),
                "metrics": it.get("metrics", []),
                "summary": it.get("summary", ""),
                "source_url": it.get("source_url", ""),
                "source_type": it.get("source_type", ""),
                "html": body_html,
            }
        )
    return docs


def _category_dirs() -> list[str]:
    return sorted(
        d.name for d in SKILL_DIR.iterdir() if d.is_dir() and _CAT_DIR_RE.match(d.name)
    )


def _e(s: str) -> str:
    return html.escape(str(s), quote=True)


# ---- HTML fragment builders --------------------------------------------------


def _build_sidebar(cat_dirs: list[str], counts: dict[str, int]) -> str:
    rows = [
        '<a class="nav-item" data-cat="__all__" href="#">'
        f'<span>全部</span><span class="count">{sum(counts.values())}</span></a>'
    ]
    for d in cat_dirs:
        n = counts.get(d, 0)
        cls = "nav-item" + ("" if n else " empty")
        rows.append(
            f'<a class="{cls}" data-cat="{_e(d)}" href="#">'
            f"<span>{_e(_category_label(d))}</span>"
            f'<span class="count">{n}</span></a>'
        )
    return '<nav class="sidebar">' + "".join(rows) + "</nav>"


def _build_gallery(docs: list[dict], cat_dirs: list[str]) -> str:
    by_cat: dict[str, list[dict]] = {}
    for doc in docs:
        by_cat.setdefault(doc["cat_dir"], []).append(doc)

    sections = []
    for d in cat_dirs:
        group = by_cat.get(d, [])
        head = (
            f'<h2 class="cat-head" data-cat="{_e(d)}">'
            f"{_e(_category_label(d))}"
            f'<span class="cat-count">{len(group)}</span></h2>'
        )
        if not group:
            body = '<p class="empty-note">（预留空目录，源索引暂无文档）</p>'
        else:
            cards = []
            for doc in group:
                tags = "".join(
                    f'<span class="tag">{_e(t)}</span>' for t in doc["tags"][:6]
                )
                cards.append(
                    f'<article class="card" data-id="{doc["id"]}" '
                    f'data-search="{_e((doc["title"] + " " + doc["summary"] + " " + " ".join(doc["tags"])).lower())}">'
                    f'<div class="card-badge">{_e(doc["doc_type"])}</div>'
                    f'<h3 class="card-title">{_e(doc["title"])}</h3>'
                    f'<p class="card-summary">{_e(doc["summary"])}</p>'
                    f'<div class="card-tags">{tags}</div>'
                    f"</article>"
                )
            body = '<div class="card-grid">' + "".join(cards) + "</div>"
        sections.append(f'<section class="cat-section" data-cat="{_e(d)}">{head}{body}</section>')
    return '<div id="gallery">' + "".join(sections) + "</div>"


def _build_store(docs: list[dict]) -> str:
    parts = []
    for doc in docs:
        metrics = "".join(f'<span class="metric">{_e(m)}</span>' for m in doc["metrics"])
        tags = "".join(f'<span class="tag">{_e(t)}</span>' for t in doc["tags"])
        src = ""
        if doc["source_url"]:
            src = (
                f'<a class="src-link" href="{_e(doc["source_url"])}" target="_blank" '
                f'rel="noopener">原文 · {_e(doc["source_type"])} ↗</a>'
            )
        meta = (
            f'<div class="reader-badge">{_e(doc["doc_type"])} · {_e(doc["category"])}</div>'
            f'<h1 class="reader-title">{_e(doc["title"])}</h1>'
            f'<p class="reader-summary">{_e(doc["summary"])}</p>'
            + (f'<div class="reader-metrics"><b>指标：</b>{metrics}</div>' if doc["metrics"] else "")
            + f'<div class="reader-tags">{tags}</div>'
            + (f'<div class="reader-src">{src}</div>' if src else "")
        )
        parts.append(
            f'<div id="store-{doc["id"]}" class="store-item">'
            f'<div class="store-meta">{meta}</div>'
            f'<article class="doc-body">{doc["html"]}</article>'
            f"</div>"
        )
    return '<div id="store" hidden>' + "".join(parts) + "</div>"


# ---- static chunks -----------------------------------------------------------

_HEAD = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>风控知识库 · Risk Knowledge Base</title>
"""

_STYLE_TMPL = """<style>
:root{--accent:#6b4eff;--accent-soft:#efeaff;--bg:#f6f7fb;--panel:#fff;--line:#e8e8ef;--txt:#1c1c28;--muted:#6b6b7b;}
*{box-sizing:border-box;}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",Segoe UI,sans-serif;background:var(--bg);color:var(--txt);}
.topbar{display:flex;align-items:center;gap:16px;padding:14px 24px;background:var(--panel);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:10;}
.brand{font-weight:700;font-size:18px;display:flex;align-items:center;gap:8px;}
.brand .dot{width:22px;height:22px;border-radius:7px;background:linear-gradient(135deg,#6b4eff,#a78bfa);}
.search{margin-left:auto;flex:0 0 320px;max-width:40vw;}
.search input{width:100%;padding:9px 14px;border:1px solid var(--line);border-radius:10px;font-size:14px;outline:none;}
.search input:focus{border-color:var(--accent);}
.layout{display:flex;min-height:calc(100vh - 57px);}
.sidebar{flex:0 0 220px;background:var(--panel);border-right:1px solid var(--line);padding:16px 12px;position:sticky;top:57px;height:calc(100vh - 57px);overflow:auto;}
.nav-item{display:flex;justify-content:space-between;align-items:center;padding:9px 12px;border-radius:9px;color:var(--txt);text-decoration:none;font-size:14px;margin-bottom:2px;}
.nav-item:hover{background:var(--bg);}
.nav-item.active{background:var(--accent-soft);color:var(--accent);font-weight:600;}
.nav-item.empty{color:#b3b3c0;}
.nav-item .count{font-size:12px;color:var(--muted);background:var(--bg);border-radius:20px;padding:1px 9px;}
.nav-item.active .count{background:#fff;color:var(--accent);}
.main{flex:1;padding:24px 32px;overflow:auto;}
.cat-section{margin-bottom:34px;}
.cat-head{font-size:16px;font-weight:700;margin:0 0 14px;display:flex;align-items:center;gap:8px;}
.cat-count{font-size:12px;font-weight:500;color:var(--muted);background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:1px 9px;}
.empty-note{color:#b3b3c0;font-size:13px;margin:0;}
.card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;cursor:pointer;transition:.15s;position:relative;}
.card:hover{border-color:var(--accent);box-shadow:0 6px 22px rgba(107,78,255,.10);transform:translateY(-2px);}
.card-badge{display:inline-block;font-size:11px;color:var(--accent);background:var(--accent-soft);border-radius:6px;padding:2px 8px;margin-bottom:8px;}
.card-title{font-size:15px;margin:0 0 8px;line-height:1.4;}
.card-summary{font-size:13px;color:var(--muted);margin:0 0 12px;line-height:1.55;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;}
.card-tags{display:flex;flex-wrap:wrap;gap:6px;}
.tag{font-size:11px;color:var(--muted);background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:1px 8px;}
.metric{font-size:11px;color:#1f7a4d;background:#e9f8ef;border:1px solid #cdeeda;border-radius:6px;padding:1px 8px;margin:0 4px 4px 0;display:inline-block;}
#reader{display:none;max-width:900px;margin:0 auto;}
.back-btn{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:7px 14px;font-size:13px;cursor:pointer;margin-bottom:18px;}
.back-btn:hover{border-color:var(--accent);color:var(--accent);}
.store-meta{border-bottom:1px solid var(--line);padding-bottom:16px;margin-bottom:20px;}
.reader-badge{font-size:12px;color:var(--accent);background:var(--accent-soft);border-radius:6px;padding:2px 10px;display:inline-block;margin-bottom:10px;}
.reader-title{font-size:24px;margin:0 0 10px;}
.reader-summary{color:var(--muted);font-size:14px;margin:0 0 12px;line-height:1.6;}
.reader-metrics{font-size:12px;margin:10px 0;}
.reader-tags{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0;}
.reader-src{margin-top:10px;}
.src-link{font-size:13px;color:var(--accent);text-decoration:none;}
.src-link:hover{text-decoration:underline;}
.doc-body{font-size:15px;line-height:1.75;color:#2a2a38;}
.doc-body h1{font-size:22px;margin:28px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line);}
.doc-body h2{font-size:19px;margin:24px 0 10px;}
.doc-body h3{font-size:16px;margin:20px 0 8px;}
.doc-body p{margin:10px 0;}
.doc-body ul,.doc-body ol{padding-left:22px;}
.doc-body li{margin:5px 0;}
.doc-body table{border-collapse:collapse;width:100%;margin:14px 0;font-size:13px;}
.doc-body th,.doc-body td{border:1px solid var(--line);padding:7px 10px;text-align:left;}
.doc-body th{background:var(--bg);}
.doc-body code{background:var(--bg);border-radius:4px;padding:1px 5px;font-size:13px;font-family:SFMono-Regular,Menlo,Consolas,monospace;}
.doc-body pre,.doc-body .highlight{background:#1e1e2e;border-radius:10px;padding:14px 16px;overflow:auto;margin:14px 0;}
.doc-body pre code,.doc-body .highlight pre{background:transparent;padding:0;color:#e6e6f0;font-size:13px;line-height:1.6;}
.code-plain{background:#1e1e2e;color:#e6e6f0;border-radius:10px;padding:14px 16px;overflow:auto;}
.no-results{color:var(--muted);padding:40px;text-align:center;display:none;}
/* pygments */
__PYGMENTS__
</style>
"""

_SCRIPT = """<script>
(function(){
  var gallery=document.getElementById('gallery');
  var reader=document.getElementById('reader');
  var store=document.getElementById('store');
  var main=document.getElementById('main');
  var search=document.getElementById('search');
  var navItems=Array.prototype.slice.call(document.querySelectorAll('.nav-item'));
  var noRes=document.getElementById('noRes');

  function openDoc(id){
    var src=document.getElementById('store-'+id);
    if(!src) return;
    reader.innerHTML='<button class="back-btn" id="back">← 返回列表</button>'+src.innerHTML;
    gallery.style.display='none';
    reader.style.display='block';
    main.scrollTop=0;
    document.getElementById('back').onclick=showGallery;
  }
  function showGallery(){
    reader.style.display='none';
    gallery.style.display='block';
  }
  document.querySelectorAll('.card').forEach(function(c){
    c.addEventListener('click',function(){openDoc(c.getAttribute('data-id'));});
  });

  // Deep-link: host (gallery widget) posts {type:'kb-open',id} to jump
  // straight to a doc. srcdoc iframes have an opaque origin and no usable URL,
  // so postMessage is the channel. We announce readiness so the host knows
  // when its listener-then-send handshake can fire.
  window.addEventListener('message',function(e){
    var d=e.data||{};
    if(d&&d.type==='kb-open'&&d.id) openDoc(d.id);
  });
  try{ (window.parent||window).postMessage({type:'kb-ready'},'*'); }catch(_){}

  function filterCat(cat){
    navItems.forEach(function(n){n.classList.toggle('active',n.getAttribute('data-cat')===cat);});
    document.querySelectorAll('.cat-section').forEach(function(s){
      s.style.display=(cat==='__all__'||s.getAttribute('data-cat')===cat)?'':'none';
    });
    showGallery();
  }
  navItems.forEach(function(n){
    n.addEventListener('click',function(e){e.preventDefault();filterCat(n.getAttribute('data-cat'));});
  });
  filterCat('__all__');

  search.addEventListener('input',function(){
    var q=search.value.trim().toLowerCase();
    var shown=0;
    document.querySelectorAll('.card').forEach(function(c){
      var hit=!q||c.getAttribute('data-search').indexOf(q)>=0;
      c.style.display=hit?'':'none';
      if(hit)shown++;
    });
    document.querySelectorAll('.cat-section').forEach(function(s){
      var any=s.querySelectorAll('.card').length===0?false:
        Array.prototype.some.call(s.querySelectorAll('.card'),function(c){return c.style.display!=='none';});
      if(q){s.style.display=any?'':'none';}
    });
    if(q){navItems.forEach(function(n){n.classList.remove('active');});}
    else{filterCat('__all__');}
    noRes.style.display=(q&&shown===0)?'block':'none';
  });
})();
</script>
</body></html>
"""


def build_html() -> str:
    docs = _load_docs()
    cat_dirs = _category_dirs()
    counts: dict[str, int] = {}
    for doc in docs:
        counts[doc["cat_dir"]] = counts.get(doc["cat_dir"], 0) + 1

    pyg_css = HtmlFormatter(style="monokai").get_style_defs(".highlight")
    style = _STYLE_TMPL.replace("__PYGMENTS__", pyg_css)

    topbar = (
        '<div class="topbar">'
        '<div class="brand"><span class="dot"></span>风控知识库 <span style="color:#b3b3c0;font-weight:400;font-size:13px;">Risk Knowledge Base</span></div>'
        '<div class="search"><input id="search" type="search" placeholder="搜索标题 / 标签 / 摘要…"></div>'
        "</div>"
    )
    layout = (
        '<div class="layout">'
        + _build_sidebar(cat_dirs, counts)
        + '<div class="main" id="main">'
        + _build_gallery(docs, cat_dirs)
        + '<div id="reader"></div>'
        + '<div class="no-results" id="noRes">没有匹配的文档</div>'
        + "</div></div>"
    )
    return (
        _HEAD
        + style
        + "</head><body>"
        + topbar
        + layout
        + _build_store(docs)
        + _SCRIPT
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        default="/tmp/risk_kb_view.html",
        help="output HTML path (default: /tmp/risk_kb_view.html)",
    )
    args = ap.parse_args()
    out = Path(args.out)
    out.write_text(build_html(), encoding="utf-8")
    docs_n = len(json.loads(MANIFEST.read_text(encoding="utf-8")))
    print(f"✓ wrote {out}  ({docs_n} docs, {out.stat().st_size // 1024} KB)")
    print("  open in browser:  file://" + str(out.resolve()))
    print("  embed in Jupyter: from IPython.display import IFrame; "
          f"IFrame('{out}', width='100%', height=800)")


if __name__ == "__main__":
    main()
