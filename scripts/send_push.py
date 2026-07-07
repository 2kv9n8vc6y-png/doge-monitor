"""
Send push notifications via Expo Push API.
Reads push tokens from environment variable or push_tokens.json.
Sends the latest DOGE report as a push notification.
"""

import json
import os
import sys

import requests

EXPO_PUSH_API = "https://exp.host/--/api/v2/push/send"
REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
LATEST_REPORT = os.path.join(REPO_ROOT, "public", "latest.json")
TOKENS_FILE = os.path.join(REPO_ROOT, "push_tokens.json")


def get_tokens():
    """Get push tokens from JSON file or env var."""
    # First check env var (GitHub Secret) — highest priority
    env_token = os.environ.get("EXPO_PUSH_TOKEN")
    env_tokens = os.environ.get("EXPO_PUSH_TOKENS")  # comma-separated

    tokens = []
    if env_token:
        tokens.append(env_token)
    if env_tokens:
        tokens.extend([t.strip() for t in env_tokens.split(",") if t.strip()])

    # Also check tokens file (for tokens registered via the app)
    if os.path.exists(TOKENS_FILE):
        try:
            with open(TOKENS_FILE, "r", encoding="utf-8") as f:
                file_tokens = json.load(f)
                if isinstance(file_tokens, list):
                    tokens.extend(file_tokens)
        except (json.JSONDecodeError, IOError):
            pass

    # Deduplicate
    return list(set(tokens))


def load_report():
    """Load the latest report JSON."""
    if not os.path.exists(LATEST_REPORT):
        print(f"Report not found: {LATEST_REPORT}", file=sys.stderr)
        return None
    with open(LATEST_REPORT, "r", encoding="utf-8") as f:
        return json.load(f)


def build_message(report):
    """Build push notification title and body from report."""
    price = report["price"]
    analysis = report["analysis"]
    rtype = report["type"]

    emoji = "☀️" if rtype == "morning" else "🌙"
    label = "DOGE 早报" if rtype == "morning" else "DOGE 晚报"

    change = price.get("change_24h_pct") or 0
    sign = "+" if change >= 0 else ""
    arrow = "📈" if change >= 0 else "📉"

    title = f"{emoji} {label}"
    body = (
        f"${price['price_usd']:.4f} {arrow} {sign}{change:.1f}% | "
        f"支撑 ${analysis['support']:.4f} / 阻力 ${analysis['resistance']:.4f}\n"
        f"{analysis['phase']}"
    )

    return title, body


def send_push(token, title, body):
    """Send a push notification to a single Expo push token."""
    payload = {
        "to": token,
        "title": title,
        "body": body,
        "sound": "default",
        "priority": "high",
        "channelId": "doge-reports",
        "data": {
            "type": "doge_report",
            "url": "https://raw.githubusercontent.com/",
        },
    }
    try:
        resp = requests.post(EXPO_PUSH_API, json=payload, timeout=15)
        result = resp.json()
        status = result.get("data", {}).get("status", "unknown")
        print(f"  {token[:30]}... → {status}")
        return status == "ok"
    except Exception as e:
        print(f"  {token[:30]}... → error: {e}")
        return False


def main():
    tokens = get_tokens()
    if not tokens:
        print("No push tokens configured. Skipping push notifications.")
        print("To enable: add EXPO_PUSH_TOKEN as a GitHub Secret, or")
        print("register via the mobile app (pushes to push_tokens.json).")
        return

    print(f"Found {len(tokens)} push token(s)")

    report = load_report()
    if not report:
        print("No report to send. Run fetch_data.py first.", file=sys.stderr)
        sys.exit(1)

    title, body = build_message(report)
    print(f"Title: {title}")
    print(f"Body: {body}")

    success = 0
    for token in tokens:
        if send_push(token, title, body):
            success += 1

    print(f"Sent: {success}/{len(tokens)} succeeded")


if __name__ == "__main__":
    main()
