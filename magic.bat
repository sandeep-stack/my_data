@echo off
title Shutdown Input

set /p mins=Enter number of minutes to wait until shutdown:
set /a mins=%mins%*60

shutdown.exe -s -t %mins%


//
shutdown.exe /s /f/ t/ 120 /c "GO TO BED RIGHT NOW!!!"