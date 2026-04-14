@echo off
REM Sokudoku auto issue - daily run
cd /d "C:\Users\USER\sokudoku-automation"

set PYTHONIOENCODING=utf-8

if not exist logs mkdir logs
set LOGFILE=logs\run_%date:~0,4%-%date:~5,2%-%date:~8,2%.log

echo ==================================== >> "%LOGFILE%" 2>&1
echo Run: %date% %time% >> "%LOGFILE%" 2>&1
echo ==================================== >> "%LOGFILE%" 2>&1

"C:\Users\USER\AppData\Local\Programs\Python\Python312\python.exe" main.py --yes >> "%LOGFILE%" 2>&1

echo Exit code: %ERRORLEVEL% >> "%LOGFILE%" 2>&1
exit /b %ERRORLEVEL%
