from __future__ import annotations

import json
from urllib.request import Request, urlopen


def notify(webhook_url: str | None, message: str) -> None:
    print(message)
    if not webhook_url:
        return
    request = Request(
        webhook_url,
        data=json.dumps({"content": message, "text": message}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10):
            pass
    except OSError as error:
        print(f"ALERT DELIVERY FAILED: {error}")
