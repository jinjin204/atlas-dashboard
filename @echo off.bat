@echo off
chcp 65001 >nul
title Atlas System - Master Launcher
color 0b

echo ==========================================
echo  Atlas System 統合起動プロセスを開始...
echo ==========================================

:: 1. CNCjs本体の起動 (デスクトップのショートカットを直接叩く)
echo [1/3] CNCjs本体 を起動しています...
:: ※ ↓ アイコンの名前が違う場合は「cncjs.lnk」の部分を実際の名前に書き換えてください。
start "" "C:\Users\yjing\AppData\Local\Programs\cncjs-app\CNCjs.exe"

:: 2. Hermes Monitor (CNCjs監視) を別ウィンドウで独立して起動
echo [2/3] Hermes Monitor (CNCjs監視) を起動しています...
start "Hermes Monitor" /D "C:\Users\yjing\.gemini\CNCjs 1.9.22監視" cmd /k "color 0a && python monitor.py"

:: 3. Atlas Hub (Streamlit) をこのウィンドウで起動
echo [3/3] Atlas Hub (生産管理画面) を起動しています...
cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else if exist "..\venv\Scripts\activate.bat" (
    cd ..
    call "venv\Scripts\activate.bat"
)

if exist "app.py" (
    streamlit run app.py --server.address 0.0.0.0 --browser.serverAddress localhost
) else if exist "atlas-hub\app.py" (
    cd atlas-hub
    streamlit run app.py --server.address 0.0.0.0 --browser.serverAddress localhost
) else (
    echo [ERROR] app.py が見つかりません。
    echo 現在の場所: %cd%
    pause
)