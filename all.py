#!/usr/bin/env python3
import os
import json
import time
import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import urllib.robotparser
from dotenv import load_dotenv

# Load .env variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/115.0 Safari/537.36")

# Selenium optional
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
except Exception:
    SELENIUM_AVAILABLE = False

# Request headers
HEADERS = {"User-Agent": USER_AGENT}
if GEMINI_API_KEY:
    HEADERS["Authorization"] = f"Bearer {GEMINI_API_KEY}"

# ---------- Utility Functions ----------

def can_fetch(url):
    parsed = urlparse(url)
    rp = urllib.robotparser.RobotFileParser()
    try:
        rp.set_url(parsed.scheme + "://" + parsed.netloc + "/robots.txt")
        rp.read()
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return True

def simple_get(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        return r
    except Exception as e:
        return e

def parse_html(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    meta_desc_tag = soup.find("meta", attrs={"name":"description"})
    meta_desc = meta_desc_tag.get("content").strip() if meta_desc_tag and meta_desc_tag.get("content") else ""
    h1_tag = soup.find("h1")
    h1 = h1_tag.get_text().strip() if h1_tag else ""

    structs = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            structs.append(json.loads(tag.string))
        except Exception:
            if tag.string:
                structs.append(tag.string.strip())

    links = []
    for a in soup.find_all("a", href=True):
        full = urljoin(base_url, a.get("href"))
        links.append(full)
        if len(links) >= 30:
            break

    scripts = [s.get("src") for s in soup.find_all("script") if s.get("src")]
    text = soup.get_text(separator=" ", strip=True)
    word_count = len(text.split())

    blocked = False
    lower_html = html.lower()
    if ("just a moment" in lower_html or "cloudflare" in lower_html or
        ("please enable javascript" in lower_html and "checking" in lower_html)):
        blocked = True

    return {
        "title": title,
        "meta_description": meta_desc,
        "h1": h1,
        "word_count": word_count,
        "links_count": len(links),
        "links_sample": links,
        "script_count": len(scripts),
        "script_src_sample": scripts[:10],
        "structured_data": structs,
        "blocked": blocked
    }

def selenium_fetch(url):
    if not SELENIUM_AVAILABLE:
        return {"error": "selenium not available"}
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=" + USER_AGENT)
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(3)
        html = driver.page_source
        return parse_html(html, url)
    except Exception as e:
        return {"error": str(e)}
    finally:
        if driver:
            driver.quit()

def handle_url(url):
    out = {"url": url}

    if not can_fetch(url):
        out["error"] = "Disallowed by robots.txt"
        return out

    # Gemini API
    if "gemini.com/v1" in url:
        if "some_endpoint" in url:
            url = "https://api.gemini.com/v1/pubticker/btcusd"
        resp = simple_get(url)
        if isinstance(resp, Exception):
            out["error"] = str(resp)
        elif getattr(resp, "status_code", None) != 200:
            out["http_status"] = getattr(resp, "status_code")
            out["error"] = "Non-200 HTTP status"
        else:
            out["type"] = "json"
            try:
                out["data"] = resp.json()
            except Exception:
                out["data"] = resp.text[:500]
        return out

    # Generic GET request
    resp = simple_get(url)
    if isinstance(resp, Exception):
        out["error"] = str(resp)
        return out
    if getattr(resp, "status_code", None) != 200:
        out["http_status"] = getattr(resp, "status_code")
        out["error"] = "Non-200 HTTP status"
        if SELENIUM_AVAILABLE:
            out["selenium_result"] = selenium_fetch(url)
        return out

    ct = resp.headers.get("Content-Type", "").lower()
    if "application/json" in ct or resp.text.strip().startswith("{"):
        out["type"] = "json"
        try:
            out["data"] = resp.json()
        except Exception:
            out["data"] = resp.text[:500]
        return out

    parsed = parse_html(resp.text, url)
    out.update(parsed)

    if parsed.get("blocked") and SELENIUM_AVAILABLE:
        out["note"] = "Blocked by anti-bot, using Selenium fallback"
        out["selenium_result"] = selenium_fetch(url)

    return out

# ---------- Main Script ----------

def main():
    parser = argparse.ArgumentParser(description="Dynamic scraper with summary")
    parser.add_argument("input_file", help="Text file with URLs")
    parser.add_argument("-o", "--output", default="output.json", help="Output JSON file")
    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print("Input file not found:", args.input_file)
        return

    with open(args.input_file, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    results = []
    print("="*80)
    for url in urls:
        print(f"Processing: {url}")
        data = handle_url(url)
        results.append(data)
        time.sleep(0.5)
    print("="*80)

    # Save full output
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # ---------- Summary ----------
    print("\nSUMMARY REPORT")
    print("="*80)
    for r in results:
        status = "Success"
        if "error" in r:
            status = "Error: " + r["error"]
        elif r.get("blocked"):
            status = "Blocked (Selenium fallback used)"
        print(f"URL: {r['url']}")
        print(f"Status: {status}")
        if r.get("type") == "json" and r.get("data"):
            if "bid" in r["data"]:
                print(f"Bid: {r['data']['bid']}, Ask: {r['data']['ask']}, Last: {r['data']['last']}")
        elif "title" in r:
            print(f"Title: {r['title']}, Words: {r.get('word_count',0)}")
            if r.get("links_sample"):
                print("Links sample:", ", ".join(r["links_sample"][:3]))
        print("-"*80)

    print(f"\nAll detailed results saved to {args.output}")

if __name__ == "__main__":
    main()
