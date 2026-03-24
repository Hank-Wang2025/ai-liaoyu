@echo off
cd /d D:\liaoyu\ai-liaoyu\app
call "C:\Program Files\nodejs\npm.cmd" run electron:dev 1>D:\liaoyu\ai-liaoyu\app\.runtime-logs\electron-dev.out.log 2>D:\liaoyu\ai-liaoyu\app\.runtime-logs\electron-dev.err.log
