"""
Railway launcher — starts both backend (uvicorn) and Telegram bot in one process.
"""

import os
import sys
import asyncio
import threading
import uvicorn


def run_backend():
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)


def run_bot():
    from bot import main as bot_main
    bot_main()


if __name__ == "__main__":
    # Start backend in a thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()

    # Run bot in main thread (it uses asyncio event loop)
    run_bot()
