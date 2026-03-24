@echo off
set BRAINSTORM_DIR=D:\liaoyu\ai-liaoyu\.superpowers\brainstorm\therapy-controls-visual
set BRAINSTORM_PORT=52341
set BRAINSTORM_HOST=127.0.0.1
set BRAINSTORM_URL_HOST=localhost
cd /d C:\Users\DS-20220107-002\.codex\superpowers-codex\skills\brainstorming\scripts
node index.js > D:\liaoyu\ai-liaoyu\.superpowers\brainstorm\therapy-controls-visual\.server.log 2>&1
