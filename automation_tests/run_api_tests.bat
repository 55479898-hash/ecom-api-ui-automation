@echo off
chcp 65001 >nul
echo === Start ecom server ===
cd /d %~dp0..\ecom_app
start "EcomServer" cmd /c "python -m uvicorn main:app --host 127.0.0.1 --port 8000"
timeout /t 2 /nobreak >nul

echo === Run API tests ===
cd /d %~dp0
if not exist reports mkdir reports
pytest api/ -m api -q --html=reports/api-report.html --self-contained-html
echo Report: automation_tests\reports\api-report.html
pause
