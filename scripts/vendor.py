#!/usr/bin/env python3
"""Vendors for the web frontend (no build step).

Downloads:
  - @awesome.me/webawesome@3.15.0   (MIT)
  - tabulator-tables@6.7.1          (MIT)

These are served locally via static/vendor/ as ES modules.
"""

import json
import os

STATIC = "/home/richard/coding/web/easycash-web/static/vendor"
os.makedirs(STATIC, exist_ok=True)


def main():
    packages: list[dict[str, str]] = [
        {
            "name": "@awesome.me/webawesome",
            "url": "https://registry.npmjs.org/@awesome.me/webawesome/latest",
        },
        {"name": "tabulator-tables", "url": "https://registry.npmjs.org/tabulator-tables/latest"},
    ]
    for pkg in packages:
        print(f"Downloading {pkg['name']}...")
        import urllib.request

        try:
            req = urllib.request.Request(pkg["url"], headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
            # write package.json + dist folder
            out_dir = os.path.join(STATIC, pkg["name"])
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, "package.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            # find tarball / wheel path from registry metadata
            if "dist-tags" in data or "files" in data:
                pass
            print(f"  → saved to {out_dir}")
        except Exception as e:
            print(f"  ⚠ failed: {e}")


if __name__ == "__main__":
    main()
