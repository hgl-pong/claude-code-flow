#!/usr/bin/env python3
"""Generate images via 9Router cx/gpt-5.5-image.

Usage:
    python scripts/generate-image.py --prompt "watercolor mountains" --output out.png [--size 1024x1024] [--quality high] [--n 1]

Exit codes:
    0  success
    1  API error (details on stderr)
    2  missing env/args
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

MODEL = "cx/gpt-5.5-image"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate image via 9Router")
    parser.add_argument("--prompt", required=True, help="Image generation prompt")
    parser.add_argument("--output", required=True, help="Output file path (png/jpg)")
    parser.add_argument("--size", default="1024x1024", help="Image size (default: 1024x1024)")
    parser.add_argument("--quality", default="high", help="Quality: low, medium, high (default: high)")
    parser.add_argument("--n", type=int, default=1, help="Number of images (default: 1)")
    args = parser.parse_args()

    url = os.environ.get("NINEROUTER_URL", "").strip()
    key = os.environ.get("NINEROUTER_KEY", "").strip()
    if not url:
        print("Error: NINEROUTER_URL is required", file=sys.stderr)
        sys.exit(2)
    if not key:
        print("Error: NINEROUTER_KEY is required", file=sys.stderr)
        sys.exit(2)

    endpoint = f"{url.rstrip('/')}/v1/images/generations?response_format=binary"
    body = json.dumps({
        "model": MODEL,
        "prompt": args.prompt,
        "size": args.size,
        "quality": args.quality,
        "n": args.n,
    }).encode("utf-8")

    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"Error: API returned {e.code}: {err_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: request failed: {e.reason}", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)

    manifest = {
        "output": str(out_path),
        "model": MODEL,
        "size": args.size,
        "quality": args.quality,
        "prompt": args.prompt,
    }
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
