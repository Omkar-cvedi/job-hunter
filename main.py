import os
import sys
import json
import argparse
from datetime import datetime

# Ensure stdout and stderr support UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fetcher import JobFetcher
from matcher import ProfileMatcher
from reporter import JobReporter

def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def run_job_hunter(dry_run=False):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.json")
    config = load_config(config_path)

    print("==================================================")
    print(f"🚀 Job Hunter running for: {config['candidate']['name']}")
    print(f"⏰ Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔍 Searching for roles posted in the last 24 hours...")
    print("==================================================")

    fetcher = JobFetcher(config)
    matcher = ProfileMatcher(config)
    reporter = JobReporter(base_dir)

    # 1. Fetch raw jobs
    raw_jobs = fetcher.collect_all_recent_jobs()
    print(f"[Main] Total candidate jobs collected: {len(raw_jobs)}")

    # 2. Evaluate each job
    evaluated_jobs = []
    rejected_count = 0
    for job in raw_jobs:
        eval_result = matcher.evaluate(
            title=job.get("title", ""),
            company=job.get("company", ""),
            location=job.get("location", ""),
            description=job.get("description", "")
        )
        if eval_result["qualified"]:
            evaluated_jobs.append({
                "job": job,
                "eval": eval_result
            })
        else:
            rejected_count += 1

    print(f"[Main] Qualified: {len(evaluated_jobs)} | Filtered out by negative criteria: {rejected_count}")

    # 3. Deduplicate and save report
    final_jobs = reporter.filter_and_deduplicate(evaluated_jobs, dry_run=dry_run)
    report_file = reporter.generate_markdown_report(final_jobs, total_scanned=len(raw_jobs))

    print("==================================================")
    print(f"✅ Report generated successfully!")
    print(f"📄 Report File: {report_file}")
    print(f"⭐ High Match (>=80%): {len([j for j in final_jobs if j['eval']['match_percentage'] >= 80])}")
    print(f"⭐ Moderate Match (60-79%): {len([j for j in final_jobs if 60 <= j['eval']['match_percentage'] < 80])}")
    print(f"⭐ Total New Opportunities: {len(final_jobs)}")
    print("==================================================")

    return report_file, final_jobs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated 24h Job Hunter")
    parser.add_argument("--dry-run", action="store_true", help="Run without persisting to history")
    args = parser.parse_args()

    run_job_hunter(dry_run=args.dry_run)
