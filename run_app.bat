@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
    if errorlevel 1 goto :python_error
)

".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :install_error

".venv\Scripts\python.exe" main.py
if errorlevel 1 goto :app_error
exit /b 0

:python_error
echo Failed to create the project virtual environment.
echo Install Python 3 and ensure the Python launcher or python command is available.
pause
exit /b 1

:install_error
echo Failed to install the packages listed in requirements.txt.
echo Check your internet connection and try again.
pause
exit /b 1

:app_error
echo The application stopped with an error. Review the message above.
pause
exit /b 1