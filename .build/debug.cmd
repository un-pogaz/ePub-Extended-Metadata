@echo off
call .build\build.cmd

echo Starting calibre in debug mode
calibre-debug.exe -g