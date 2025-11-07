#!/usr/bin/env python3
# exl_research.py — Shared research pipeline (UI-free)
# Unifies: LinkedIn scrape, DDG person/company, page enrichment, sitemap helpers.
# Persists into the same DB using exl_common.* save/list functions.

from __future__ import annotations

import os, re, time, json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
from xml.etree import ElementTree as ET

# Optional deps for enrichment
try:
    import requests
except Exception:
    requests = None
try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

# Pull shared bits from your existing module
from exl_common import (
    migrate_db_schema,
    # CSV helpers already exist here if you need them in callers:
    # suggest_mapping, apply_mapping,
    # Selenium attach + LinkedIn scrape:
    attach_driver, linkedin_scrape_all,
    # DuckDuckGo search helpers:
    ddg_text, ddg_person_smart,
    # DB writers:
    save_prospect_insight, save_company_insight,
)

# -------------------- Tunables --------------------
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36"
KEY_INTEREST = re.compile(
    r"\b(ai|analytics?|data\s+governance|genai|governance|testing|automation|cloud|risk|controls?|quality|release|"
    r"cycle\s*time|customer\s+experience|cx|cost|efficien|productivity|data\s+platform|lineage)\b",
    re.I
)

# -------------------- URL utils --------------------
def norm_url(u: str) -> str:
    try:
        o = urlparse(u or "")
        if not o.scheme:
            return "https://" + (u or "").lstrip("/")
        return u
    except Exception:
        return u or ""

def domain_of(u: str) -> str:
    try:
        host = urlparse(u or "").netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""

# -------------------- Page enrichment --------------------
def _meta_from_soup(soup) -> Dict:
    if not soup: return {}
    def meta_get(name=None, prop=None):
        if name:
            el = soup.find("meta", attrs={"name": name})
            if el and el.get("content"): return el["content"].strip()
        if prop:
            el = soup.find("meta", attrs={"property": prop})
            if el and el.get("content"): return el["content"].strip()
        return ""

    title = (soup.title.get_text(strip=True) if soup and soup.title else "")
    desc = meta_get(name="description")
    og_title = meta_get(prop="og:title")
    og_desc = meta_get(prop="og:description")

    # H1/H2
    h1s = []
    for h in soup.find_all(["h1","h2"], limit=5):
        tx = h.get_text(" ", strip=True)
        if tx and len(tx) > 6:
            h1s.append(tx[:160])

    # body sample
    body_text = ""
    for sel in ["article", "main", "section", "div"]:
        node = soup.find(sel)
        if node:
            body_text = node.get_text(" ", strip=True)
            if len(body_text) > 400:
                break
    if not body_text:
        body_text = soup.get_text(" ", strip=True)[:1200]

    # quick date hint
    date_hint = ""
    try:
        for tag, attrs in [("meta", {"property": "article:published_time"}),
                           ("meta", {"name": "date"}), ("time", {})]:
            for el in soup.find_all(tag, attrs=attrs):
                val = (el.get("content") or el.get_text(" ", strip=True) or "").strip()
                if re.search(r"\d{4}-\d{2}-\d{2}", val) or re.search(
                    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b",
                    val, re.I
                ):
                    date_hint = val[:100]; raise StopIteration
    except StopIteration:
        pass

    # quick keywords
    text_for_k = " ".join([title, desc, og_title, og_desc, " ".join(h1s), body_text])
    kws = []
    if text_for_k:
        words = re.findall(r"[A-Za-z][A-Za-z\-\&]{2,}", text_for_k.lower())
        stop = set("""a about after all also an and any are as at be been being
            between both but by can could did do does doing done down during each either
            for from further get got had has have having here how i if in into is it
            its itself just like may more most must no nor not now of off on once only
            or other our out over own same should since so some such than that the
            their them then there these they this those through to under until up upon
            use used using was we were what when where which while who will with within
            without you your""".split())
        freq = {}
        for w in words:
            if w in stop: continue
            freq[w] = freq.get(w, 0) + 1
        kws = [w for w,_ in sorted(freq.items(), key=lambda kv: kv[1], reverse=True)[:12]]

    return {
        "title": title[:220],
        "meta_description": desc[:300],
        "og_title": og_title[:220],
        "og_description": og_desc[:300],
        "h1_h2": h1s[:5],
        "top_keywords": kws,
        "date_hint": date_hint,
        "text_sample": body_text[:800]
    }

def harvest_with_requests(url: str, timeout: int) -> Dict:
    if not (requests and BeautifulSoup):
        return {}
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=timeout, allow_redirects=True)
        if "html" not in (resp.headers.get("Content-Type","")).lower():
            return {"status_code": resp.status_code, "content_type": resp.headers.get("Content-Type","")}
        soup = BeautifulSoup(resp.text or "", "html.parser")
        meta = _meta_from_soup(soup)
        meta.update({"status_code": resp.status_code, "content_type": resp.headers.get("Content-Type","")})
        return meta
    except Exception:
        return {}

def harvest_with_browser(driver, url: str, timeout: int) -> Dict:
    if not (driver and BeautifulSoup):
        return {}
    try:
        driver.get(url)
        t0 = time.time()
        while time.time() - t0 < min(6, timeout):
            time.sleep(0.6)
        soup = BeautifulSoup(driver.page_source or "", "html.parser")
        meta = _meta_from_soup(soup)
        meta.update({"status_code": 200, "content_type": "text/html; rendered"})
        return meta
    except Exception:
        return {}

def enrich_hit(url: str, *, use_browser: bool, driver, timeout: int) -> Dict:
    u = norm_url(url)
    info = {"url": u, "domain": domain_of(u)}
    meta = {}
    if use_browser and driver:
        meta = harvest_with_browser(driver, u, timeout)
    if not meta:
        meta = harvest_with_requests(u, timeout)
    info["meta"] = meta or {}
    txt = " ".join([
        meta.get("title",""), meta.get("meta_description",""),
        meta.get("og_title",""), meta.get("og_description",""),
        " ".join(meta.get("h1_h2", []))
    ])
    m = KEY_INTEREST.findall(txt or "")
    score = min(
        100,
        40 + len(m)*10
        + (10 if "investor" in info["domain"] else 0)
        + (5 if "/press" in u or "/news" in u else 0)
    )
    info["relevance_score"] = score
    return info

# -------------------- Company URL helpers --------------------
def fetch_sitemap_urls(base_url: str, cap: int = 20, timeout: int = 10) -> List[str]:
    urls = []
    try:
        root = urlparse(norm_url(base_url))
        guess = f"{root.scheme}://{root.netloc}/sitemap.xml"
        if requests:
            r = requests.get(guess, headers={"User-Agent": UA}, timeout=timeout)
            if r.status_code == 200 and r.text.strip().startswith("<"):
                try:
                    tree = ET.fromstring(r.text)
                    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
                    locs = [el.text for el in tree.findall(".//sm:loc", ns) if el is not None and el.text]
                    for loc in locs:
                        if any(k in loc.lower() for k in ["news", "press", "blog", "insights"]):
                            urls.append(loc)
                            if len(urls) >= cap: break
                    if not urls:
                        urls = locs[:cap]
                except Exception:
                    pass
    except Exception:
        pass
    # de-dup
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            out.append(u); seen.add(u)
    return out[:cap]

def candidate_company_pages(company: str, site_root: str) -> List[str]:
    roots = []
    try:
        o = urlparse(norm_url(site_root))
        base = f"{o.scheme}://{o.netloc}"
        for p in ["/investors", "/investor", "/investor-relations", "/ir",
                  "/news", "/press", "/press-releases", "/media",
                  "/blog", "/insights", "/resources", "/stories"]:
            roots.append(urljoin(base, p))
    except Exception:
        pass
    seen, out = set(), []
    for u in roots:
        if u not in seen:
            out.append(u); seen.add(u)
    return out

# -------------------- Core research steps --------------------
def research_prospect_one(
    user_id: str,
    campaign_id: str,
    row: Dict,
    *,
    use_linkedin_scrape: bool,
    driver,                # Selenium driver or None
    max_person_hits: int,
    debug: bool = False
) -> Dict:
    """
    Collects: LI about/activity (if allowed + URL), DDG-person snippets.
    Saves to DB (prospect_insights). Returns brief summary dict for UI/logging.
    """
    about_text, articles, activity = "", [], []
    ddg_snips, sources = [], []

    li_url = row.get("Linkedin ID URL","") or row.get("Linkedin_ID_URL","")

    # LinkedIn scrape
    if use_linkedin_scrape and li_url and driver is not None:
        try:
            li_data = linkedin_scrape_all(driver, str(li_url))
            about_text = li_data.get("about_text","")
            articles = li_data.get("articles",[])
            activity = li_data.get("activity",[])
        except Exception as e:
            if debug: print(f"[prospect LI scrape error] {e}")

    # DDG person
    full_name = row.get("fullName","")
    title = row.get("Title","")
    company = row.get("companyName","") or row.get("Company","")
    try:
        hits = ddg_person_smart(full_name=full_name, title=title, company=company, max_results=int(max_person_hits))
    except Exception:
        hits = []
    for h in hits:
        href = (h.get("href") or "").strip()
        ddg_snips.append({
            "title": (h.get("title") or "").strip(),
            "body": (h.get("body") or "").strip(),
            "href": href
        })
        if href:
            sources.append(href)

    # Persist
    try:
        save_prospect_insight(
            user_id=user_id,
            campaign_id=campaign_id,
            row=row,
            about_text=about_text,
            articles=articles,
            activity=activity,
            ddg_snips=ddg_snips,
            sources=sources
        )
    except Exception as e:
        if debug: print(f"[prospect save error] {e}")

    return {
        "fullName": full_name, "Title": title, "Company": company,
        "about_len": len(about_text or ""),
        "articles": len(articles or []), "activity": len(activity or []),
        "ddg_person_hits": len(ddg_snips)
    }

def research_company_one(
    user_id: str,
    campaign_id: str,
    company: str,
    *,
    do_company: bool,
    fetch_page_meta: bool,
    use_browser: bool,
    driver,                 # Selenium driver or None
    max_company_hits: int,
    max_company_meta: int,
    timeout_sec: int,
    polite_sleep_ms: int,
    debug: bool = False
) -> Dict:
    """
    Runs DDG for company, enriches pages, guesses filings/website, tries sitemap/news/blog pages.
    Saves to DB (company_insights). Returns brief summary dict.
    """
    if not do_company or not company:
        return {"Company": company or "", "kept": 0, "filings": 0, "website": 0}

    ddg_snips_c: List[Dict] = []
    filings: List[Dict] = []
    website: List[Dict] = []
    sources_c: List[str] = []

    comp_qs = [
        f"{company} site:investor.* 10-K OR 10-Q OR annual report",
        f"{company} earnings call transcript",
        f"{company} press release analytics OR AI OR data governance",
        f"{company} official website"
    ]

    # DDG company
    hits_c = []
    for q in comp_qs:
        try:
            hits_c += ddg_text(q, max_results=int(max_company_hits))
        except Exception:
            pass
        if polite_sleep_ms:
            time.sleep(polite_sleep_ms/1000.0)

    # enrich + categorize
    seen = set(); base_site = ""
    for h in hits_c:
        href = norm_url(h.get("href",""))
        if not href or href in seen: continue
        seen.add(href)
        item = {
            "title": (h.get("title") or "").strip(),
            "body": (h.get("body") or "").strip(),
            "href": href
        }
        dom = domain_of(href)
        if not base_site and company.lower().split()[0] in dom:
            base_site = f"https://{dom}"

        enriched = {}
        if fetch_page_meta:
            enriched = enrich_hit(
                href, use_browser=bool(use_browser), driver=driver, timeout=int(timeout_sec)
            )
        item["enriched"] = enriched
        ddg_snips_c.append(item)
        sources_c.append(href)

        low = (h.get('title','').lower() + " " + h.get('href','').lower())
        if any(k in low for k in ["10-k", "10q", "annual report"]):
            filings.append(item)
        if dom and company.lower().split()[0] in dom:
            website.append(item)

    # sitemap/company hubs
    extra_urls = []
    if base_site:
        if fetch_page_meta:
            extra_urls += fetch_sitemap_urls(base_site, cap=int(max_company_meta), timeout=int(timeout_sec))
        extra_urls += candidate_company_pages(company, base_site)
    # unique + cap
    uniq = []
    seen2 = set()
    for u in extra_urls:
        u2 = norm_url(u)
        if u2 not in seen2:
            uniq.append(u2); seen2.add(u2)
    uniq = uniq[:int(max_company_meta)]

    for u in uniq:
        enriched = {}
        if fetch_page_meta:
            enriched = enrich_hit(
                u, use_browser=bool(use_browser), driver=driver, timeout=int(timeout_sec)
            )
        item = {
            "title": (enriched.get("meta", {}) or {}).get("title", ""),
            "body": (enriched.get("meta", {}) or {}).get("meta_description", "")
                    or (enriched.get("meta", {}) or {}).get("og_description",""),
            "href": u,
            "enriched": enriched
        }
        ddg_snips_c.append(item)
        sources_c.append(u)
        if polite_sleep_ms:
            time.sleep(polite_sleep_ms/1000.0)

    # Persist
    try:
        save_company_insight(
            user_id=user_id,
            campaign_id=campaign_id,
            company=company,
            ddg_snips=ddg_snips_c,
            filings=filings,
            website=website,
            sources=sources_c
        )
    except Exception as e:
        if debug: print(f"[company save error] {e}")

    return {
        "Company": company,
        "kept": len(ddg_snips_c),
        "filings": len(filings),
        "website": len(website),
        "base_site_used": base_site or ""
    }

# -------------------- Batch orchestrator --------------------
def run_research_batch(
    user_id: str,
    campaign_id: str,
    rows: List[Dict],
    *,
    # toggles
    do_person: bool = True,
    do_company: bool = True,
    use_linkedin_scrape: bool = True,
    fetch_page_meta: bool = True,
    use_browser: bool = False,
    # limits
    max_person_hits: int = 6,
    max_company_hits: int = 12,
    max_company_meta: int = 10,
    timeout_sec: int = 10,
    polite_sleep_ms: int = 250,
    # infra
    driver = None,                 # Selenium driver (or None)
    progress_cb = None,            # callable(idx:int, total:int, msg:str)
    debug: bool = False
) -> List[Dict]:
    """
    Unified batch research. Safe to call from Streamlit pages or jobs.
    Returns per-row brief summaries (for logging/metrics).
    Also writes prospect_insights & company_insights rows to DB.
    """
    migrate_db_schema()

    total = len(rows)
    results: List[Dict] = []
    t0 = time.time()

    for i, r in enumerate(rows, start=1):
        if progress_cb:
            progress_cb(i, total, f"Researching {r.get('fullName','(unknown)')} @ {r.get('companyName') or r.get('Company','')}".strip())

        person_summary = {}
        company_summary = {}

        if do_person:
            try:
                person_summary = research_prospect_one(
                    user_id=user_id, campaign_id=campaign_id, row=r,
                    use_linkedin_scrape=use_linkedin_scrape,
                    driver=driver, max_person_hits=int(max_person_hits), debug=debug
                )
            except Exception as e:
                if debug: print(f"[batch person error] {e}")

        comp_name = r.get("companyName","") or r.get("Company","")
        if do_company and comp_name:
            try:
                company_summary = research_company_one(
                    user_id=user_id, campaign_id=campaign_id, company=comp_name,
                    do_company=True, fetch_page_meta=fetch_page_meta, use_browser=use_browser,
                    driver=driver, max_company_hits=int(max_company_hits),
                    max_company_meta=int(max_company_meta), timeout_sec=int(timeout_sec),
                    polite_sleep_ms=int(polite_sleep_ms), debug=debug
                )
            except Exception as e:
                if debug: print(f"[batch company error] {e}")

        results.append({
            "idx": i, "fullName": r.get("fullName",""),
            "Company": comp_name,
            "person": person_summary, "company": company_summary
        })

        if polite_sleep_ms:
            time.sleep(polite_sleep_ms/1000.0)

    if debug:
        print(f"[batch done] {total} rows in {time.time()-t0:.1f}s")
    return results
