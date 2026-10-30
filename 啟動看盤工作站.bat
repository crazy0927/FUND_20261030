@echo off
chcp 65001 >nul
title 統一奔騰看盤工作站 - 本地伺服器
echo 正在啟動看盤工作站與資料庫更新服務...
start http://localhost:8000/
python app_server.py
pause
