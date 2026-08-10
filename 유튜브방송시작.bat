@echo off
title Cardia Stream - YouTube LIVE
echo.
echo   Starting Cardia stream (YouTube)...
echo   Close Chrome and other heavy apps first!
echo.
powershell -ExecutionPolicy Bypass -File "D:\ai-vtuber-kit\start_stream.ps1" -YouTube
echo.
pause
