import urllib.request
import urllib.parse
import re
import html
import time
import random
import json

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
]

class JobFetcher:
    def __init__(self, config):
        self.config = config
        self.queries = config.get("search_queries", ["Java Backend Developer", "Spring Boot Developer"])
        self.target_country = "India"

    def _get_headers(self):
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/"
        }

    def fetch_linkedin_feed(self, keyword, start=0, max_retries=2):
        """Fetches public LinkedIn job cards posted within the last 24h (f_TPR=r86400) for entry/internship."""
        encoded_kw = urllib.parse.quote(keyword)
        encoded_loc = urllib.parse.quote(self.target_country)
        url = (
            f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
            f"keywords={encoded_kw}&location={encoded_loc}&f_TPR=r86400&f_E=1,2&start={start}"
        )

        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers=self._get_headers())
                with urllib.request.urlopen(req, timeout=12) as response:
                    if response.status == 200:
                        content = response.read().decode("utf-8", errors="ignore")
                        return self._parse_job_cards(content)
            except Exception as e:
                time.sleep(1 + attempt)
        return []

    def _parse_job_cards(self, html_content):
        jobs = []
        # Extract individual job cards
        cards = re.findall(r'<div class="[^"]*base-card[^"]*".*?</li>', html_content, re.DOTALL)
        if not cards:
            # Fallback regex over entire block
            cards = [html_content]

        titles = re.findall(r'<h3 class="[^"]*base-search-card__title[^"]*">\s*([^<]+)\s*</h3>', html_content)
        companies = re.findall(r'<h4 class="[^"]*base-search-card__subtitle[^"]*">\s*(?:<a[^>]*>)?\s*([^<]+)\s*(?:</a>)?\s*</h4>', html_content)
        locations = re.findall(r'<span class="[^"]*job-search-card__location[^"]*">\s*([^<]+)\s*</span>', html_content)
        links = re.findall(r'<a class="[^"]*base-card__full-link[^"]*"\s+href="([^"]+)"', html_content)
        times = re.findall(r'<time[^>]*datetime="([^"]+)"[^>]*>\s*([^<]+)\s*</time>', html_content)

        count = min(len(titles), len(links))
        for i in range(count):
            clean_title = html.unescape(titles[i].strip())
            clean_company = html.unescape(companies[i].strip()) if i < len(companies) else "Company Undisclosed"
            clean_location = html.unescape(locations[i].strip()) if i < len(locations) else "India"
            raw_link = links[i]
            clean_url = raw_link.split("?")[0] if "?" in raw_link else raw_link
            time_val = times[i][1].strip() if i < len(times) else "Within last 24h"

            # Derive unique ID
            job_id_match = re.search(r'-(\d+)(?:\?|$)', clean_url)
            job_id = job_id_match.group(1) if job_id_match else f"li_{abs(hash(clean_url))}"

            jobs.append({
                "id": job_id,
                "title": clean_title,
                "company": clean_company,
                "location": clean_location,
                "url": clean_url,
                "posted_time": time_val,
                "source": "LinkedIn (Past 24h)"
            })
        return jobs

    def fetch_job_details(self, job_url):
        """Fetches full job description from the individual job posting page."""
        try:
            req = urllib.request.Request(job_url, headers=self._get_headers())
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode("utf-8", errors="ignore")
                
                # Match description section
                desc_match = re.search(r'<div class="[^"]*show-more-less-html__markup[^"]*">(.*?)</div>', content, re.DOTALL)
                if desc_match:
                    raw_desc = desc_match.group(1)
                    # Strip html tags and unescape
                    clean_desc = re.sub(r'<[^>]+>', ' ', raw_desc)
                    clean_desc = html.unescape(re.sub(r'\s+', ' ', clean_desc)).strip()
                    return clean_desc
                
                # Fallback: general body content
                clean_content = re.sub(r'<[^>]+>', ' ', content)
                return html.unescape(re.sub(r'\s+', ' ', clean_content))[:4000]
        except Exception:
            return ""

    def collect_all_recent_jobs(self, max_per_query=20):
        """Loops through all queries, aggregates jobs, and fetches descriptions."""
        all_jobs = {}
        print(f"[Fetcher] Starting job collection across {len(self.queries)} queries...")

        for query in self.queries:
            print(f"[Fetcher] Querying: '{query}'...")
            for start in [0, 10]:
                results = self.fetch_linkedin_feed(query, start=start)
                for job in results:
                    if job["id"] not in all_jobs:
                        all_jobs[job["id"]] = job
                time.sleep(0.4)  # polite spacing

        print(f"[Fetcher] Collected {len(all_jobs)} unique listings. Enriching job descriptions...")
        job_list = list(all_jobs.values())

        # Enrich description
        for idx, job in enumerate(job_list):
            desc = self.fetch_job_details(job["url"])
            job["description"] = desc
            time.sleep(0.2)
            if (idx + 1) % 10 == 0:
                print(f"[Fetcher] Processed {idx + 1}/{len(job_list)} job details...")

        return job_list
