#!/usr/bin/env python
"""
Startup script for FinOps - runs both app.py and server.py
"""
import subprocess
import time
import sys
import os

os.chdir("/app/server")

# Start FastAPI backend server on port 7861
print("Starting FastAPI backend server...")
server_process = subprocess.Popen([sys.executable, "server.py"], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE)

# Give server time to start
time.sleep(3)

# Start frontend HTTP server on port 7860
print("Starting frontend HTTP server...")
try:
    subprocess.run([sys.executable, "app.py"])
except KeyboardInterrupt:
    print("Shutting down...")
    server_process.terminate()
    server_process.wait()
    sys.exit(0)
