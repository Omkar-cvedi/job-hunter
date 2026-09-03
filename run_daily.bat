@echo off
cd /d "%~dp0"
python main.py >> run.log 2>&1
