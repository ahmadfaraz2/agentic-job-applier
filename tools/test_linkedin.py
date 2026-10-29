"""
LinkedIn Public Jobs API & Scraping Tester.
"""

from __future__ import annotations

import re
import sys
import httpx

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def test_linkedin(query: str = "Python Developer", location: str = "Pakistan"):
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={query.replace(' ', '+')}&location={location.replace(' ', '+')}&start=0"
    print(f"Requesting LinkedIn: {url}...")

    with httpx.Client(headers=headers, follow_redirects=True, timeout=12.0) as client:
        r = client.get(url)
        print("HTTP Status:", r.status_code)
        if r.status_code != 200:
            print("Response body preview:", r.text[:300])
            return

        # Extract titles, companies, links, locations
        cards = re.findall(r'<div class="base-card[^>]*>.*?</div>\s*</div>', r.text, flags=re.DOTALL)
        print(f"Discovered {len(cards)} LinkedIn job cards!\n")

        for c in cards[:6]:
            title_m = re.search(r'<h3 class="base-search-card__title">([^<]+)</h3>', c)
            company_m = re.search(r'<h4 class="base-search-card__subtitle">[^<]*<a[^>]*>([^<]+)</a>', c) or re.search(r'<h4 class="base-search-card__subtitle">([^<]+)</h4>', c)
            loc_m = re.search(r'<span class="job-search-card__location">([^<]+)</span>', c)
            link_m = re.search(r'<a class="base-card__full-link[^"]*"\s+href="([^"?]+)', c)

            title = title_m.group(1).strip() if title_m else "N/A"
            company = company_m.group(1).strip() if company_m else "N/A"
            loc = loc_m.group(1).strip() if loc_m else "N/A"
            link = link_m.group(1).strip() if link_m else "N/A"

            print(f"• {title}")
            print(f"  Company:  {company}")
            print(f"  Location: {loc}")
            print(f"  Link:     {link}")
            print("-" * 50)

if __name__ == "__main__":
    test_linkedin()
