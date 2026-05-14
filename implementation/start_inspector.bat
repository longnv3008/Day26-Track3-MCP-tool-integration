@echo off
REM Run MCP Inspector against the SQLite Lab server
REM Usage: start_inspector.bat

set SCRIPT_DIR=%~dp0
set PYTHON=C:\Users\LONG NGO\AppData\Local\Programs\Python\Python312\python.exe

if not exist "%SCRIPT_DIR%.npm-cache" mkdir "%SCRIPT_DIR%.npm-cache"
set NPM_CONFIG_CACHE=%SCRIPT_DIR%.npm-cache
npx -y @modelcontextprotocol/inspector "%PYTHON%" "%SCRIPT_DIR%mcp_server.py"
