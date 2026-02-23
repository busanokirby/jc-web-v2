Version: 2.0.5
Release Date: 2026-02-23

Summary
-------
- Merge partial payments with credits so sales list shows a unified status: `PARTIAL/CREDIT` or `CREDIT` where applicable.
- Added `status_display` field in history exports to drive UI display (keeps original `status` intact).
- Updated `sales_list.html` to use the unified `status_display` and avoid duplicate "On credit" badges.
- Minor test adjustments and fixes for consistent behavior in daily sales reporting.

Files changed
-------------
- app/blueprints/sales/routes.py — add `status_display` when building history
- templates/sales/sales_list.html — show merged status badge
- tests/test_sales_daily_report.py — test fixes (local)

Notes
-----
- A local git commit and tag `v2.0.5` has been created (not pushed). To publish, run the push commands below.

Push to remote (example)
------------------------
Run these commands to push commits and tags to GitHub:

```bash
git add -A
git commit -m "Merge partial payments with credits; sales list unified status (v2.0.5)"
git tag -a v2.0.5 -m "Release v2.0.5: Partial/Credit merge"
git push origin main
git push origin v2.0.5
```

Adjust branch name if you're not using `main`.
