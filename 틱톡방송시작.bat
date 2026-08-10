@echo off
title Cardia Stream - TikTok LIVE Studio
echo.
echo   Starting Cardia (TikTok mode)...
echo   Avatar + game + AI brain, then LIVE Studio opens.
echo   Press GO LIVE only after the READY banner appears.
echo.
powershell -ExecutionPolicy Bypass -File "D:\ai-vtuber-kit\start_stream.ps1" -TikTok
echo.
pause
