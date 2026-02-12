"""
Shadow Empire — запуск всего: бэкенд + тоннель + бот.
Тоннель и бот автоматически перезапускаются при падении.
При смене URL тоннеля бот перезапускается автоматически.

Запуск: python -u run_all.py
"""
import subprocess
import re
import time
import threading
import os
import signal
import sys

BOT_PY = "bot.py"
TUNNEL_CMD = ["cloudflared", "tunnel", "--url", "http://localhost:8000"]
BACKEND_CMD = [sys.executable, "run.py"]
BOT_CMD = [sys.executable, "bot.py"]

bot_proc = None
bot_lock = threading.Lock()


def log(tag, msg):
    print(f"[{tag}] {msg}", flush=True)


def update_bot_url(new_url):
    webapp_url = new_url + "/static/index.html"
    with open(BOT_PY, "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(
        r'(WEBAPP_URL\s*=\s*os\.getenv\("WEBAPP_URL",\s*")([^"]+)(")',
        lambda m: m.group(1) + webapp_url + m.group(3),
        content
    )
    with open(BOT_PY, "w", encoding="utf-8") as f:
        f.write(content)
    log("tunnel", f"WEBAPP_URL -> {webapp_url}")


def start_bot():
    global bot_proc
    with bot_lock:
        # Kill old bot if running
        if bot_proc and bot_proc.poll() is None:
            log("bot", "Stopping old bot...")
            bot_proc.terminate()
            try:
                bot_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                bot_proc.kill()
        log("bot", "Starting bot...")
        bot_proc = subprocess.Popen(BOT_CMD)
        log("bot", f"Bot started (PID {bot_proc.pid})")


def bot_watchdog():
    """Restart bot if it crashes."""
    global bot_proc
    while True:
        time.sleep(5)
        with bot_lock:
            if bot_proc and bot_proc.poll() is not None:
                log("bot", f"Bot crashed (code {bot_proc.returncode}), restarting...")
                bot_proc = subprocess.Popen(BOT_CMD)
                log("bot", f"Bot restarted (PID {bot_proc.pid})")


def run_backend():
    """Run backend server in a thread, restart on crash."""
    while True:
        log("backend", "Starting backend server...")
        proc = subprocess.Popen(BACKEND_CMD)
        log("backend", f"Backend started (PID {proc.pid})")
        proc.wait()
        log("backend", f"Backend exited (code {proc.returncode}), restarting in 3s...")
        time.sleep(3)


def run_tunnel():
    """Run cloudflared tunnel, capture URL, restart bot on new URL."""
    while True:
        log("tunnel", "Starting cloudflared...")
        proc = subprocess.Popen(
            TUNNEL_CMD,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        url_found = False
        for line in proc.stdout:
            line = line.strip()
            if line:
                log("tunnel", line)
            if not url_found and "Your quick Tunnel" not in line:
                match = re.search(r"(https://[a-z]+-[a-z]+-[a-z]+-[a-z]+\.trycloudflare\.com)", line)
                if match:
                    new_url = match.group(1)
                    update_bot_url(new_url)
                    url_found = True
                    # Restart bot with new URL
                    start_bot()

        proc.wait()
        log("tunnel", f"Tunnel exited (code {proc.returncode}), restarting in 3s...")
        time.sleep(3)


def cleanup():
    global bot_proc
    log("main", "Shutting down...")
    with bot_lock:
        if bot_proc and bot_proc.poll() is None:
            bot_proc.terminate()


def main():
    log("main", "=== Shadow Empire — Full Stack Launcher ===")
    log("main", "Backend + Tunnel + Bot")
    log("main", "Press Ctrl+C to stop everything\n")

    # Start backend in thread
    t_backend = threading.Thread(target=run_backend, daemon=True)
    t_backend.start()

    # Wait for backend to start
    time.sleep(2)

    # Start bot watchdog in thread
    t_watchdog = threading.Thread(target=bot_watchdog, daemon=True)
    t_watchdog.start()

    # Run tunnel in main thread (blocks)
    try:
        run_tunnel()
    except KeyboardInterrupt:
        cleanup()
        log("main", "Stopped.")


if __name__ == "__main__":
    main()
