# 🚀 Automated 24h Job Hunter & Profile Matcher

Automated daily job discovery engine for **Omkar Chaturvedi** (Java Backend Engineer / SDE-1).

Every day at **10:00 AM IST**, this repository automatically runs via GitHub Actions to:
1. Search across public job feeds for roles posted in the **last 24 hours**.
2. Filter out non-Java / Senior (>3 YoE) / pure frontend roles.
3. Compute an objective **Profile Match Percentage (%)** against Omkar's resume skills.
4. Deduplicate against previously seen jobs so every day brings fresh listings.
5. Generate a daily Markdown dashboard in `reports/`.

---

### 📄 Latest Job Report
👉 [Click here to view the Latest Jobs Dashboard](reports/latest_jobs.md)

---

### 🛠️ Manual Execution
To run locally:
```bash
python main.py
```
