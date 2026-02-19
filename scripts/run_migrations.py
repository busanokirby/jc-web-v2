#!/usr/bin/env python3
"""
Run all migration scripts in the `scripts/` folder that match `migrate_*.py`.

This runner is intentionally simple and safe:
- Finds `scripts/migrate_*.py` files and runs them in sorted order.
- Passes through the environment (useful for DATABASE_URL, SECRET_KEY, etc.).
- Sets a temporary `SECRET_KEY` if missing (some migration scripts call `create_app()`).
- Is idempotent as underlying migration scripts should be idempotent.

Usage:
  python scripts/run_migrations.py         # run all migration scripts
  python scripts/run_migrations.py --dry-run
  python scripts/run_migrations.py --yes   # skip confirmation

Exit codes:
 - 0 : all migrations ran (or nothing to run)
 - 1 : one or more migrations failed
"""
from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
from typing import List

SCRIPT_DIR = os.path.dirname(__file__)
PATTERN = os.path.join(SCRIPT_DIR, 'migrate_*.py')


def discover_scripts(pattern: str = PATTERN) -> List[str]:
    files = sorted(glob.glob(pattern))
    # exclude this runner if misnamed
    files = [f for f in files if os.path.abspath(f) != os.path.abspath(__file__)]
    return files


def run_script(path: str, env: dict) -> int:
    print(f"\n--- Running: {os.path.basename(path)} ---")
    try:
        proc = subprocess.run([sys.executable, path], env=env)
        return proc.returncode
    except Exception as exc:
        print(f"Error running {path}: {exc}")
        return 1


def main(argv: List[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(description="Run idempotent migration scripts in scripts/")
    parser.add_argument('--dry-run', action='store_true', help='List scripts without running')
    parser.add_argument('--yes', '-y', action='store_true', help='Don\'t prompt for confirmation')
    parser.add_argument('--pattern', default=PATTERN, help='Glob pattern for migration scripts')

    args = parser.parse_args(argv)

    scripts = discover_scripts(args.pattern)
    if not scripts:
        print('No migration scripts found.')
        return 0

    print('Found migration scripts:')
    for s in scripts:
        print('  -', os.path.basename(s))

    if args.dry_run:
        return 0

    if not args.yes:
        resp = input('\nRun the above migration scripts now? [y/N]: ').strip().lower()
        if resp not in ('y', 'yes'):
            print('Aborted by user.')
            return 0

    # Prepare environment for child processes
    env = os.environ.copy()
    if not env.get('SECRET_KEY'):
        print('\nWarning: SECRET_KEY not set in environment. Setting a temporary SECRET_KEY for migration run.')
        env['SECRET_KEY'] = env.get('SECRET_KEY', 'migration-temp')

    exit_code = 0
    for script in scripts:
        code = run_script(script, env)
        if code != 0:
            print(f"\nMigration script failed: {os.path.basename(script)} (exit {code})")
            exit_code = code
            break

    if exit_code == 0:
        print('\nAll migration scripts completed successfully.')
    else:
        print('\nOne or more migration scripts failed. See output above.')

    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
