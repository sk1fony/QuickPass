@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
py -3 -c "import sys" >nul 2>&1
if errorlevel 1 goto try_python
py -3 bootstrap.py %*
goto finished
:try_python
python -c "import sys" >nul 2>&1
if errorlevel 1 goto missing
python bootstrap.py %*
:finished
set "QP_EXIT=%ERRORLEVEL%"
if not "%QP_EXIT%"=="0" pause
exit /b %QP_EXIT%
:missing
echo Install Python 3.10+ from https://www.python.org/downloads/
echo Enable Add Python to PATH during installation
pause
exit /b 1
