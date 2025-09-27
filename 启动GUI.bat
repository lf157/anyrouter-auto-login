@echo off
chcp 65001 >nul
title AnyRouter GUI 登录工具

echo ========================================
echo   AnyRouter GUI 登录工具
echo ========================================
echo.

echo.
echo 🚀 启动GUI界面...
echo ========================================
echo.

REM 启动GUI程序并自动关闭bat窗口
start "" python auto_gui.py
exit