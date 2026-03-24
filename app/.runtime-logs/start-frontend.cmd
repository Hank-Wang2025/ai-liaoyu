@echo off
cd /d D:\liaoyu\ai-liaoyu\app
npm run dev -- --host 127.0.0.1 --port 5173 > .runtime-logs\frontend.log 2>&1
