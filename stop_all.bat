@echo off
chcp 65001 >nul
title Vocard Stopper
color 0C

cls
echo.
echo     ════════════════════════════════════════════════════════
echo                    Stopping Vocard Services
echo     ════════════════════════════════════════════════════════
echo.

echo           Stopping all Python processes...
taskkill /F /IM python.exe >nul 2>&1

echo.
echo           [OK] All services stopped!
echo.
echo     ════════════════════════════════════════════════════════
echo.
echo           Press any key to close...
pause >nul
