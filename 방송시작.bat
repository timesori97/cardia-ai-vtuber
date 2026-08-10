@echo off
title Cardia Stream - Twitch LIVE
echo.
echo   Starting Cardia stream (Twitch)...
echo   Close Chrome and other heavy apps first!
echo.
powershell -ExecutionPolicy Bypass -File "D:\ai-vtuber-kit\start_stream.ps1" -Live
echo.
pause
