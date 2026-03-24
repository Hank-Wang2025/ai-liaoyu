@echo off
cd /d D:\liaoyu\ai-liaoyu\backend
D:\liaoyu\ai-liaoyu\backend\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 1>D:\liaoyu\ai-liaoyu\backend\.runtime-logs\backend.out.log 2>D:\liaoyu\ai-liaoyu\backend\.runtime-logs\backend.err.log
