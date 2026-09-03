import os
import json
from datetime import datetime

class JobReporter:
    def __init__(self, storage_dir):
        self.storage_dir = storage_dir
        self.reports_dir = os.path.join(storage_dir, "reports")
        os.makedirs(self.reports_dir, exist_ok=True)
        self.history_file = os.path.join(storage_dir, "seen_jobs.json")
        self.history = self._load_history()

    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_history(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"[Reporter] Warning: Could not save history: {e}")

    def filter_and_deduplicate(self, jobs_with_eval, dry_run=False):
        """Removes previously seen jobs and jobs rejected by hard filters."""
        new_qualified_jobs = []
        for item in jobs_with_eval:
            job = item["job"]
            eval_res = item["eval"]
            job_id = str(job["id"])

            # Check if seen previously
            if job_id in self.history:
                continue

            if not eval_res.get("qualified", False):
                continue

            # Minimum threshold: include down to 25%
            if eval_res.get("match_percentage", 0) < 25:
                continue

            new_qualified_jobs.append(item)

            if not dry_run:
                self.history[job_id] = {
                    "seen_date": datetime.now().strftime("%Y-%m-%d"),
                    "title": job["title"],
                    "company": job["company"]
                }

        if not dry_run:
            self._save_history()

        # Sort by match percentage descending
        new_qualified_jobs.sort(key=lambda x: x["eval"]["match_percentage"], reverse=True)
        return new_qualified_jobs

    def generate_markdown_report(self, qualified_jobs, total_scanned=0):
        """Generates a rich, structured markdown report with quick links and badges."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        report_filename = f"jobs_{today_str}.md"
        report_path = os.path.join(self.reports_dir, report_filename)
        latest_path = os.path.join(self.reports_dir, "latest_jobs.md")

        high_match = [j for j in qualified_jobs if j["eval"]["match_percentage"] >= 80]
        medium_match = [j for j in qualified_jobs if 60 <= j["eval"]["match_percentage"] < 80]
        entry_match = [j for j in qualified_jobs if 50 <= j["eval"]["match_percentage"] < 60]
        lesser_match = [j for j in qualified_jobs if j["eval"]["match_percentage"] < 50]

        md = []
        md.append(f"# 🎯 Daily Job Discovery & Profile Match Report — {today_str}\n")
        md.append(f"> **Candidate Profile:** Omkar Chaturvedi | Java Backend / SDE-1 (Spring Boot, MySQL, AWS)")
        md.append(f"> **Run Time:** {datetime.now().strftime('%d %b %Y, %I:%M %p IST')} | **Scan Window:** Last 24 Hours\n")

        md.append("## 📊 Summary Overview\n")
        md.append(f"| Metric | Count |")
        md.append(f"| :--- | :--- |")
        md.append(f"| **Total 24h Postings Scanned** | `{total_scanned}` |")
        md.append(f"| **Qualified Listings Found** | `{len(qualified_jobs)}` |")
        md.append(f"| **High Match (≥ 80%)** | `{len(high_match)}` 🟢 |")
        md.append(f"| **Moderate Match (60% - 79%)** | `{len(medium_match)}` 🟡 |")
        md.append(f"| **Relevant Associate / Intern (50% - 59%)** | `{len(entry_match)}` 🔵 |")
        md.append(f"| **Lesser Matched / Adjacent (< 50%)** | `{len(lesser_match)}` ⚪ |\n")

        if not qualified_jobs:
            md.append("### ℹ️ No new listings matched your criteria in this run.\n")
            md.append("All discovered jobs were either previously surfaced or filtered out by negative criteria (e.g. Python/FastAPI or >3 YoE). Next scan will check again at 10:00 AM IST.\n")
        else:
            md.append("## ⚡ Quick Application Table\n")
            md.append("| Match % | Role Title | Company | Location | Link |")
            md.append("| :---: | :--- | :--- | :--- | :---: |")
            for item in qualified_jobs:
                j = item["job"]
                ev = item["eval"]
                pct = ev["match_percentage"]
                badge = "🟢" if pct >= 80 else ("🟡" if pct >= 60 else ("🔵" if pct >= 50 else "⚪"))
                md.append(f"| **{badge} {pct}%** | {j['title']} | **{j['company']}** | {j['location']} | [Apply Now ↗]({j['url']}) |")
            md.append("\n---\n")

            if high_match:
                md.append("## 🟢 High Match Opportunities (≥ 80%)\n")
                for item in high_match:
                    md.extend(self._format_job_card(item))

            if medium_match:
                md.append("## 🟡 Moderate Match Roles (60% - 79%)\n")
                for item in medium_match:
                    md.extend(self._format_job_card(item))

            if entry_match:
                md.append("## 🔵 Associate & Intern Roles (50% - 59%)\n")
                for item in entry_match:
                    md.extend(self._format_job_card(item))

            if lesser_match:
                md.append("## ⚪ Lesser Matched / Adjacent Roles (< 50%)\n")
                md.append("> *Compact view for quick reference (Title, Company, Location & Direct Link):*\n")
                for item in lesser_match:
                    j = item["job"]
                    ev = item["eval"]
                    pct = ev["match_percentage"]
                    md.append(f"* **{pct}%** — [{j['title']}]({j['url']}) at **{j['company']}** ({j['location']})")
                md.append("\n")

        md.append("\n---\n")
        md.append("*Generated automatically by Omkar's Job Hunter Agent.*")

        content = "\n".join(md)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)

        with open(latest_path, "w", encoding="utf-8") as f:
            f.write(content)

        return report_path

    def _format_job_card(self, item):
        j = item["job"]
        ev = item["eval"]
        lines = []
        lines.append(f"### [{j['title']}]({j['url']}) — **{j['company']}**")
        lines.append(f"- **Profile Match:** `{ev['match_percentage']}%`")
        lines.append(f"- **Location:** {j['location']}")
        lines.append(f"- **Posted:** {j['posted_time']}")
        
        matched_str = ", ".join([f"`{s}`" for s in ev.get("matched_skills", [])]) or "General Java Backend"
        lines.append(f"- **Key Skills Matched:** {matched_str}")
        
        missing = ev.get("missing_skills", [])
        if missing:
            missing_str = ", ".join([f"`{s}`" for s in missing])
            lines.append(f"- **Good-to-Have Skills:** {missing_str}")

        lines.append(f"- **Direct Link:** [Open Application Link]({j['url']})\n")
        return lines
