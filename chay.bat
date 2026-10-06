@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Treo may LMS VNU

rem ===== Tim Python =====
set "PY="
python --version >nul 2>nul && set "PY=python"
if not defined PY py --version >nul 2>nul && set "PY=py"
if not defined PY (
    echo [LOI] Chua cai Python. Tai tai https://www.python.org/downloads/
    echo       Nho tick "Add Python to PATH" khi cai.
    pause
    exit /b 1
)

rem ===== Cai thu vien neu chua co =====
%PY% -c "import selenium, webdriver_manager" >nul 2>nul
if errorlevel 1 (
    echo Dang cai thu vien selenium, webdriver-manager...
    %PY% -m pip install --upgrade selenium webdriver-manager
    if errorlevel 1 (
        echo [LOI] Cai thu vien that bai.
        pause
        exit /b 1
    )
)

rem ===== Da co tai khoan: cho 5 giay de chon doi tai khoan =====
set "ARGS="
if exist "taikhoan.json" (
    choice /c CD /n /t 5 /d C /m "Da luu tai khoan. Bam D de DOI tai khoan, hoac doi 5 giay de chay luon... "
    if errorlevel 2 set "ARGS=--doi-tai-khoan"
)

%PY% abc.py %ARGS%

echo.
pause
