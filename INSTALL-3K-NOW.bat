@echo off
title FunPod - Steam Desktop Install
echo ============================================
echo   Installing Steam GUI on FunPod
echo   Pod: tsbej1azdwvvde  
echo   You log in via VNC after this finishes.
echo ============================================
echo.

ssh -o StrictHostKeyChecking=no -p 30287 root@94.101.98.218 "dpkg --add-architecture i386 && apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq wget gnupg2 software-properties-common lib32gcc-s1 libgl1-mesa-dri:i386 libgl1:i386 libc6:i386 2>/dev/null && wget -qO /tmp/steam.deb https://cdn.cloudflare.steamstatic.com/client/installer/steam.deb && dpkg -i /tmp/steam.deb 2>/dev/null; apt-get install -f -y -qq 2>/dev/null && echo '=== STEAM INSTALLED ===' && echo 'Open VNC desktop, click terminal, type: steam' && echo 'Then log in with YOUR Steam account and download Three Kingdoms'"

echo.
echo ============================================
echo   DONE. Now go to VNC:
echo   https://tsbej1azdwvvde-80.proxy.runpod.net
echo   pw: gaming123
echo.
echo   Open terminal on desktop, type: steam
echo   Log into YOUR account. Download 3K.
echo ============================================
pause
