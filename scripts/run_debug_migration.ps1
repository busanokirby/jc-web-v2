# powershell wrapper to run debug_migration.py with venv
& "${PWD}\webv2\Scripts\Activate.ps1"
python "${PWD}\scripts\debug_migration.py"