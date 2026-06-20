"""update_readme.py — refresh the build-version table in README.md.

Usage: python update_readme.py <steam_build_version> <steamclient_sha256>
Inserts/updates a row between the <!--TABLE--> ... <!--/TABLE--> markers.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

START = "<!--TABLE-->"
END = "<!--/TABLE-->"


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: update_readme.py <version> <sha256>", file=sys.stderr)
        return 2
    version, sha = sys.argv[1], sys.argv[2].lower()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    readme = Path("README.md")
    text = readme.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print("markers not found in README.md; skipping", file=sys.stderr)
        return 0

    pre, rest = text.split(START, 1)
    _, post = rest.split(END, 1)

    header = (
        "\n\n| Steam build | steamclient64.dll SHA-256 | Updated (UTC) |\n"
        "| --- | --- | --- |\n"
    )
    row = f"| `{version}` | `{sha}` | {now} |\n"

    # Keep prior rows (everything that looks like a table row) and prepend new.
    prior_rows = [
        ln for ln in rest.split(END, 1)[0].splitlines()
        if ln.startswith("| `") and sha not in ln
    ]
    body = header + row + ("\n".join(prior_rows) + "\n" if prior_rows else "")

    readme.write_text(pre + START + body + END + post, encoding="utf-8")
    print(f"README updated: build {version} ({sha})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
