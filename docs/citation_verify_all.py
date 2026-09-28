#!/usr/bin/env python3
"""对 refs.bib 全部条目做逐条引用核验，**三条互相独立的书目源**：
  1. Crossref          api.crossref.org/works/<doi>     （出版方登记的 DOI 元数据）
  2. Semantic Scholar  api.semanticscholar.org/graph/v1 （DOI 或 arXiv id 均可查）
  3. OpenAlex          api.openalex.org/works/doi:<doi> （独立的开放书目库）

（DBLP 在本环境不可达；`https://dblp.org` 直连失败 —— 已在报告里写明，不假装查过。
 arXiv 官方 API 在本环境只回 301 空体，故 arXiv-only 条目走 S2 的 `arXiv:<id>` 入口。）

输出 docs/citation_verification_all.md，逐条列「声称值 vs 各源回读值」+ 逐字段判定。
**不做「差不多就算过」** —— 每个字段单独判；判不了的写 `?`（不是 ✓）。
用法：从仓库根目录 `python3 docs/citation_verify_all.py`
"""
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIB = os.path.join(ROOT, "paper", "refs.bib")
OUT = os.path.join(ROOT, "docs", "citation_verification_all.md")
CACHE = "/tmp/xref_cache_v2.json"
UA = "foyer-citation-check/1.0 (mailto:noreply@example.org)"


def fetch(url, timeout=35, tries=5):
    """带退避重试 —— S2 免费档会回 429，不重试就会把限流误记成「查无此条」"""
    delay = 3.0
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < tries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise


def parse_bib(path):
    txt = open(path, encoding="utf-8").read()
    raw = re.findall(r"@(\w+)\s*\{\s*([^,]+),(.*?)\n\}", txt, re.S)
    out = []

    def fld(body, name):
        m = re.search(name + r"\s*=\s*\{(.*?)\}\s*,?\s*\n", body, re.S | re.I)
        if not m:
            m = re.search(name + r'\s*=\s*[{"]([^"}]*)[}"]', body, re.I)
        return re.sub(r"\s+", " ", m.group(1)).strip() if m else None

    for typ, key, body in raw:
        out.append(dict(
            key=key.strip(), typ=typ, title=fld(body, "title"), author=fld(body, "author"),
            year=fld(body, "year"), venue=fld(body, "booktitle") or fld(body, "journal"),
            pages=fld(body, "pages"), doi=fld(body, "doi"), eprint=fld(body, "eprint")))
    return out


_ACC = {"\\'e": "e", "\\'a": "a", "\\'o": "o", "\\'i": "i", "\\'u": "u", '\\"o': "o",
        '\\"a': "a", '\\"u': "u", "\\'c": "c", "\\`e": "e", "\\~n": "n", "\\'ı": "i"}


def norm(s):
    if not s:
        return ""
    s = s.replace("$^2$", "2").replace("$^\\dagger$", "")
    for k, v in _ACC.items():
        s = s.replace(k, v)
    s = s.replace("\\&", "and").replace("~", " ")
    s = re.sub(r"\\[a-zA-Z]+\s*", "", s)
    s = s.replace("{", "").replace("}", "")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def sim(a, b):
    A, B = set(norm(a).split()), set(norm(b).split())
    return len(A & B) / len(A | B) if A and B else 0.0


def surnames(s):
    if not s:
        return []
    out = []
    for p in re.split(r"\s+and\s+", s):
        p = p.strip()
        if not p:
            continue
        out.append(norm(p.split(",")[0]) if "," in p else norm(p.split()[-1]))
    return out


# ---------------- sources ----------------
def crossref(doi, c):
    if doi in c:
        return c[doi]
    r = None
    try:
        m = json.loads(fetch("https://api.crossref.org/works/" + urllib.parse.quote(doi)))["message"]
        yr = None
        for k in ("published-print", "published-online", "issued", "created"):
            dp = m.get(k, {}).get("date-parts", [[None]])[0]
            if dp and dp[0]:
                yr = dp[0]
                break
        r = dict(ok=True, title=(m.get("title") or [""])[0],
                 authors=[(a.get("family", "") + ", " + a.get("given", "")).strip(", ")
                          for a in (m.get("author") or [])],
                 year=yr, venue=(m.get("container-title") or [""])[0] or "",
                 page=m.get("page"), volume=m.get("volume"), type=m.get("type"),
                 publisher=m.get("publisher"))
    except Exception as e:
        r = dict(ok=False, err=f"{type(e).__name__}: {e}")
    c[doi] = r
    return r


def s2(ident, c):
    k = "s2:" + ident
    if k in c:
        return c[k]
    r = None
    try:
        u = ("https://api.semanticscholar.org/graph/v1/paper/"
             + urllib.parse.quote(ident, safe=":") + "?fields=title,year,venue,authors,externalIds,journal,publicationVenue")
        d = json.loads(fetch(u))
        r = dict(ok=True, title=d.get("title"), year=d.get("year"),
                 venue=d.get("venue") or (d.get("journal") or {}).get("name") or "",
                 authors=[a.get("name", "") for a in (d.get("authors") or [])],
                 pages=(d.get("journal") or {}).get("pages"), doi=(d.get("externalIds") or {}).get("DOI"))
    except Exception as e:
        r = dict(ok=False, err=f"{type(e).__name__}: {e}")
    c[k] = r
    return r


def openalex_search(title, c):
    """无 DOI 的条目：按标题检索 OpenAlex，取相似度最高的一条"""
    k = "oas:" + norm(title)
    if k in c:
        return c[k]
    r = None
    try:
        u = "https://api.openalex.org/works?search=" + urllib.parse.quote(title[:200]) + "&per-page=8"
        d = json.loads(fetch(u))
        best, bs = None, 0.0
        for w in d.get("results", []):
            s = sim(title, w.get("title") or w.get("display_name") or "")
            if s > bs:
                best, bs = w, s
        if best is None:
            r = dict(ok=False, err="no hit")
        else:
            src = ((best.get("primary_location") or {}).get("source") or {})
            b = best.get("biblio") or {}
            pg = None
            if b.get("first_page"):
                pg = b["first_page"] + ("--" + b["last_page"] if b.get("last_page") else "")
            r = dict(ok=True, title=best.get("title") or best.get("display_name"), score=round(bs, 3),
                     year=best.get("publication_year"), venue=src.get("display_name") or "",
                     authors=[a["author"]["display_name"] for a in (best.get("authorships") or [])],
                     pages=pg, doi=(best.get("doi") or "").replace("https://doi.org/", ""))
    except Exception as e:
        r = dict(ok=False, err=f"{type(e).__name__}: {e}")
    c[k] = r
    return r


def s2_search(title, c):
    k = "s2s:" + norm(title)
    if k in c:
        return c[k]
    r = None
    try:
        u = ("https://api.semanticscholar.org/graph/v1/paper/search?query="
             + urllib.parse.quote(title[:200]) + "&limit=8&fields=title,year,venue,authors,externalIds,journal")
        d = json.loads(fetch(u))
        best, bs = None, 0.0
        for w in d.get("data", []):
            s = sim(title, w.get("title") or "")
            if s > bs:
                best, bs = w, s
        if best is None:
            r = dict(ok=False, err="no hit")
        else:
            r = dict(ok=True, title=best.get("title"), year=best.get("year"),
                     venue=best.get("venue") or (best.get("journal") or {}).get("name") or "",
                     authors=[a.get("name", "") for a in (best.get("authors") or [])],
                     pages=(best.get("journal") or {}).get("pages"),
                     doi=(best.get("externalIds") or {}).get("DOI"), score=round(bs, 3))
    except Exception as e:
        r = dict(ok=False, err=f"{type(e).__name__}: {e}")
    c[k] = r
    return r


def openalex(doi, c):
    k = "oa:" + doi
    if k in c:
        return c[k]
    r = None
    try:
        d = json.loads(fetch("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi)))
        src = ((d.get("primary_location") or {}).get("source") or {})
        b = d.get("biblio") or {}
        pg = None
        if b.get("first_page"):
            pg = b["first_page"] + ("--" + b["last_page"] if b.get("last_page") else "")
        r = dict(ok=True, title=d.get("title"), year=d.get("publication_year"),
                 venue=src.get("display_name") or "",
                 authors=[a["author"]["display_name"] for a in (d.get("authorships") or [])],
                 pages=pg, volume=b.get("volume"), doi=(d.get("doi") or "").replace("https://doi.org/", ""))
    except Exception as e:
        r = dict(ok=False, err=f"{type(e).__name__}: {e}")
    c[k] = r
    return r


# ---------------- field verdicts ----------------
def v_title(claimed, got):
    if not got:
        return "?"
    s = sim(claimed, got)
    return "✓" if s >= 0.85 else ("~" + f"{s:.2f}" if s >= 0.6 else f"✗{s:.2f}")


def v_year(claimed, got):
    if not got:
        return "?"
    return "✓" if str(claimed) == str(got) else f"✗({got})"


def v_authors(claimed, got):
    if not got:
        return "?"
    c, g = surnames(claimed), [norm(x.split()[-1]) for x in got if x.strip()]
    if not c or not g:
        return "?"
    inter = len(set(c) & set(g))
    if set(c) == set(g):
        return "✓"
    if inter >= min(len(c), len(g)):
        return f"✓⊂({len(c)}v{len(g)})"      # 一方是另一方的前缀/子集（截断写法）
    if inter:
        return f"~({inter}/{len(c)})"
    return "✗"


def v_pages(claimed, got):
    if not claimed or not got:
        return "?"
    a = set(re.findall(r"\d+", norm(claimed)))
    b = set(re.findall(r"\d+", norm(str(got))))
    if not a or not b:
        return "?"
    return "✓" if a & b else f"✗({got})"


def v_venue(claimed, got):
    if not claimed or not got:
        return "?"
    stop = {"on", "of", "the", "in", "and", "for", "a", "an", "proceedings", "international",
            "conference", "symposium", "annual", "technical", "usenix", "advances", "neural",
            "information", "processing", "systems", "workshop", "ieee", "acm", "edition"}
    cc = set(norm(claimed).split()) - stop
    gg = set(norm(got).split()) - stop
    if not cc or not gg:
        return "?"
    return "✓" if (cc & gg) else f"?[{got[:46]}]"


def main():
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    ents = parse_bib(BIB)
    rows = []
    for i, e in enumerate(ents, 1):
        cr = crossref(e["doi"], cache) if e["doi"] else None
        ident = ("DOI:" + e["doi"]) if e["doi"] else (("arXiv:" + e["eprint"]) if e["eprint"] else None)
        s = s2(ident, cache) if ident else None
        if not (s and s.get("ok")):
            s = s2_search(e["title"], cache)          # 无 DOI / 查不到 ⇒ 退回标题检索
        oa = openalex(e["doi"], cache) if e["doi"] else None
        if not (oa and oa.get("ok")):
            oa = openalex_search(e["title"], cache)
        time.sleep(1.6)
        rows.append((e, cr, s, oa))
        print(f"[{i:2d}/46] {e['key']:24s} CR={'Y' if cr and cr.get('ok') else '-'} "
              f"S2={'Y' if s and s.get('ok') else '-'} OA={'Y' if oa and oa.get('ok') else '-'}", flush=True)
        json.dump(cache, open(CACHE, "w"))

    L = ["# refs.bib 46 条逐条引用核验（Crossref / Semantic Scholar / OpenAlex 三源）\n",
         "生成脚本：`docs/citation_verify_all.py`（从仓库根目录跑，可复现）。\n",
         "**判定口径**：每个字段**单独判**，不写「差不多就算过」。`?` = 该源无此字段或写法差异大到"
         "无法判（**不是**通过）；`~` = 部分相符；`✗` = 不符。\n",
         "⚠ **本环境查不到的源**（不许当成「查过了」）：`dblp.org` 直连失败；"
         "`export.arxiv.org/api` 只回 301 空体 —— 故 arXiv-only 条目走 S2 的 `arXiv:<id>` 入口。\n",
         f"生成时间：{time.strftime('%Y-%m-%d %H:%M %Z')}\n"]

    n = lambda lst: sum(1 for x in lst if x and x.get("ok"))
    cri = [c for _, c, _, _ in rows if c]
    s2i = [s for _, _, s, _ in rows if s]
    oai = [o for _, _, _, o in rows if o]
    L.append(f"命中：Crossref **{n(cri)}**/{len(cri)}（有 DOI 的条目）｜"
             f"Semantic Scholar **{n(s2i)}**/{len(s2i)}｜OpenAlex **{n(oai)}**/{len(oai)}。\n")

    for e, cr, s, oa in rows:
        L.append(f"\n## `{e['key']}`\n")
        L.append("| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |")
        L.append("|---|---|---|---|---|")
        g = lambda d, k: (str(d.get(k)) if d and d.get("ok") and d.get(k) else "") or "—"
        L.append(f"| 标题 | {e['title']} | {g(cr,'title')} | {g(s,'title')} | {g(oa,'title')} |")
        L.append(f"| 年 | {e['year']} | {g(cr,'year')} | {g(s,'year')} | {g(oa,'year')} |")
        L.append(f"| 作者 | {e['author']} | {'; '.join((cr or {}).get('authors') or []) or '—'} | "
                 f"{'; '.join((s or {}).get('authors') or []) or '—'} | "
                 f"{'; '.join((oa or {}).get('authors') or []) or '—'} |")
        L.append(f"| venue | {e['venue']} | {g(cr,'venue')} | {g(s,'venue')} | {g(oa,'venue')} |")
        L.append(f"| 页码 | {e['pages']} | {g(cr,'page')} | {g(s,'pages')} | {g(oa,'pages')} |")
        L.append(f"| DOI | {e['doi']} | {'✓ 解析成功' if (cr and cr.get('ok')) else ('无 DOI 字段' if not e['doi'] else '✗ 查不到')} | "
                 f"{g(s,'doi')} | {g(oa,'doi')} |")
        L.append("")
        vt = "标题 " + v_title(e["title"], g(cr, "title") if g(cr, "title") != "—" else
                               (g(s, "title") if g(s, "title") != "—" else g(oa, "title")))
        vy = "年 " + v_year(e["year"], next((g(d, "year") for d in (cr, s, oa)
                                            if g(d, "year") != "—"), None))
        va = "作者 " + v_authors(e["author"], next(((d or {}).get("authors") for d in (cr, s, oa)
                                                    if (d or {}).get("authors")), None))
        parts = [vt, vy, va]
        if e["pages"]:
            parts.append("页码 " + v_pages(e["pages"], next((g(d, "pages" if d is not cr else "page")
                                                             for d in (cr, s, oa)
                                                             if g(d, "pages" if d is not cr else "page") != "—"), None)))
        if e["doi"]:
            parts.append("DOI " + ("✓" if (cr and cr.get("ok")) else "✗"))
        L.append("**判定**：" + " ｜ ".join(parts) + "\n")

    open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(cache, open(CACHE, "w"))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
