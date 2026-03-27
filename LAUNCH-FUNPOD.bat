@echo off
echo Installing dependencies...
C:\Python311\python.exe -m pip install paramiko requests PyQt6 -q --break-system-packages 2>nul
echo Launching FunPod...
cd /d C:\Users\Eru\Documents\GitHub\FunPod-RunpodGaming
C:\Python311\python.exe funpod.py
pause
