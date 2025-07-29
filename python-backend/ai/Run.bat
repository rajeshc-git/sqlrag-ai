@echo off
cd /d "C:\Users\ABI-AI\Desktop\rajesh\ai"

start uvicorn blueshift:app --host 0.0.0.0 --port 8002

start uvicorn rag:app --host 0.0.0.0 --port 8001

pause