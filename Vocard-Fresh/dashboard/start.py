#!/usr/bin/env python3
"""Production startup script for Railway deployment"""
import os
import sys

print("Starting dashboard...", flush=True)
print(f"Python version: {sys.version}", flush=True)
print(f"PORT env: {os.getenv('PORT', 'not set')}", flush=True)

try:
    # Import app first to catch any import errors
    from main import app
    print("App imported successfully", flush=True)
    
    # Run with hypercorn
    import asyncio
    from hypercorn.config import Config
    from hypercorn.asyncio import serve
    print("Hypercorn imported successfully", flush=True)
    
    config = Config()
    port = os.getenv("PORT", "8080")
    config.bind = [f"0.0.0.0:{port}"]
    config.accesslog = "-"  # Log to stdout
    config.errorlog = "-"   # Log errors to stdout
    print(f"Starting server on 0.0.0.0:{port}", flush=True)
    
    asyncio.run(serve(app, config))
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)


