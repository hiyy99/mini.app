"""
Auto-restart Cloudflare tunnel + update bot WEBAPP_URL.
Run this instead of manually starting cloudflared.
"""
import subprocess
import re
import time
import signal
import sys

BOT_PY = "bot.py"
TUNNEL_CMD = ["cloudflared", "tunnel", "--url", "http://localhost:8000"]

def update_bot_url(new_url):
    """Replace WEBAPP_URL in bot.py with the new tunnel URL."""
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
    print(f"[tunnel] Updated bot.py WEBAPP_URL -> {webapp_url}")

def run_tunnel():
    """Start cloudflared and capture the tunnel URL."""
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
        print(line, end="")
        if not url_found and "Your quick Tunnel" not in line:
            match = re.search(r"(https://[a-z]+-[a-z]+-[a-z]+-[a-z]+\.trycloudflare\.com)", line)
            if match:
                new_url = match.group(1)
                print(f"\n[tunnel] Got URL: {new_url}")
                update_bot_url(new_url)
                url_found = True
    proc.wait()
    return proc.returncode

def main():
    print("[tunnel] Auto-restart tunnel manager started")
    print("[tunnel] Press Ctrl+C to stop\n")

    while True:
        print("[tunnel] Starting cloudflared...")
        code = run_tunnel()
        print(f"\n[tunnel] Tunnel exited with code {code}")
        print("[tunnel] Restarting in 3 seconds...\n")
        time.sleep(3)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[tunnel] Stopped.")
