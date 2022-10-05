@echo off
call .build\build.cmd

echo Starting calibre in debug mode
calibre-debug.exe --gui-debug C:\Users\un_pogaz\AppData\Local\Temp\calibre-debug.txt