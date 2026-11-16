@echo off
rem ZestLoop website launcher (ChE 303 project).
rem Double-click this file. It starts the website and opens it in your browser.
rem Keep this window open while you present; close it (or press Ctrl+C) to stop the website.

cd /d "%~dp0"
title ZestLoop website - keep this window open
echo Starting the ZestLoop website at http://localhost:8501
echo Keep this window open during the demo. Close it to stop the website.
echo.

rem Open the browser after a short delay so the server is ready first.
start "" /b cmd /c "ping -n 7 127.0.0.1 >nul & start "" http://localhost:8501"

python -m streamlit run app\app.py --server.port 8501

echo.
echo The website has stopped. If an error is shown above, read it before closing this window.
pause
