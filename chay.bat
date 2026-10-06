@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
title Treo may LMS VNU

rem ===== 1. Python: chua co thi tu cai =====
call :tim_python
if not defined PY (
    echo [*] Chua co Python, dang tu cai Python 3.12 ^(mat 1-3 phut^)...
    call :cai_python
    call :tim_python
)
if not defined PY (
    echo [LOI] Khong tu cai duoc Python.
    echo       Tai tay tai https://www.python.org/downloads/ va nho tick "Add Python to PATH".
    pause
    exit /b 1
)
echo [OK] Python: %PY%

rem ===== 2. Google Chrome: chua co thi tu cai =====
call :tim_chrome
if not defined CHROME (
    echo [*] Chua co Google Chrome, dang tu cai...
    call :cai_chrome
    call :tim_chrome
)
if not defined CHROME (
    echo [LOI] Khong tu cai duoc Google Chrome. Tai tay tai https://www.google.com/chrome/
    pause
    exit /b 1
)
echo [OK] Chrome: %CHROME%

rem ===== 3. Moi truong rieng .venv: khong dung toi Python/Conda cua may =====
set "VENV=%~dp0.venv"
set "VPY=%VENV%\Scripts\python.exe"
rem venv hong (vd Python goc da bi go) -> tao lai
if exist "%VPY%" (
    "%VPY%" -c "" >nul 2>nul
    if errorlevel 1 rmdir /s /q "%VENV%"
)
if not exist "%VPY%" (
    echo [*] Tao moi truong rieng .venv ^(chi lan dau^)...
    "%PY%" -m venv "%VENV%"
    if errorlevel 1 (
        echo [LOI] Khong tao duoc .venv.
        pause
        exit /b 1
    )
)
rem Chi cai thu vien khi .venv moi tao hoac requirements.txt thay doi
fc /b "requirements.txt" "%VENV%\.da_cai.txt" >nul 2>nul
if errorlevel 1 (
    echo [*] Dang cai thu vien vao .venv...
    "%VPY%" -m pip install --disable-pip-version-check -q --upgrade -r requirements.txt
    if errorlevel 1 (
        echo [LOI] Cai thu vien that bai. Kiem tra mang roi chay lai.
        pause
        exit /b 1
    )
    copy /y "requirements.txt" "%VENV%\.da_cai.txt" >nul
)
echo [OK] Moi truong .venv san sang.
echo.

rem ===== 4. Da co tai khoan: cho 5 giay de chon doi tai khoan =====
set "ARGS="
if exist "taikhoan.json" (
    choice /c CD /n /t 5 /d C /m "Da luu tai khoan. Bam D de DOI tai khoan, hoac doi 5 giay de chay luon... "
    if errorlevel 2 set "ARGS=--doi-tai-khoan"
)

"%VPY%" treo_lms.py %ARGS%

echo.
pause
exit /b 0


rem ================= CAC HAM =================

:tim_python
set "PY="
rem Uu tien python trong PATH (bo qua alias Microsoft Store: alias nay khong chay duoc -c)
python -c "import sys" >nul 2>nul && for /f "delims=" %%P in ('python -c "import sys;print(sys.executable)"') do set "PY=%%P"
if defined PY exit /b 0
py -3 -c "import sys" >nul 2>nul && for /f "delims=" %%P in ('py -3 -c "import sys;print(sys.executable)"') do set "PY=%%P"
if defined PY exit /b 0
rem Ban vua cai xong chua kip vao PATH cua cua so nay
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set "PY=%%D\python.exe"
exit /b 0

:cai_python
where winget >nul 2>nul
if not errorlevel 1 (
    winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
    if not errorlevel 1 exit /b 0
)
echo [*] Tai bo cai Python tu python.org...
set "PYINST=%TEMP%\python-3.12.10-amd64.exe"
curl -L --fail -o "%PYINST%" "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
if exist "%PYINST%" (
    "%PYINST%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    del "%PYINST%" >nul 2>nul
)
exit /b 0

:tim_chrome
set "CHROME="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set "CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
exit /b 0

:cai_chrome
where winget >nul 2>nul
if not errorlevel 1 (
    winget install -e --id Google.Chrome --silent --accept-package-agreements --accept-source-agreements
    if not errorlevel 1 exit /b 0
)
echo [*] Tai bo cai Chrome tu google.com...
set "CRINST=%TEMP%\chrome_installer.exe"
curl -L --fail -o "%CRINST%" "https://dl.google.com/chrome/install/latest/chrome_installer.exe"
if exist "%CRINST%" (
    "%CRINST%" /silent /install
    del "%CRINST%" >nul 2>nul
)
exit /b 0
