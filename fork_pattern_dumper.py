"""
fork_pattern_dumper.py
======================
Self-contained pattern dumper for the OpenSteamTool *fork-only* functions —
the handful of steamclient64.dll routines the build-version-switch feature
hooks that are NOT tracked by the upstream steam-monitor project.

For each function it:
  1. Scans steamclient64.dll's .text for the gold-standard IDA byte signature
     (from `steamclient_ida_sigs.json`).
  2. Derives the function-start RVA from the unique match.
  3. Emits `steamclient/<sha256>.toml`, keyed by FNV-1a(name), in the exact
     format OpenSteamTool's PatternLoader consumes:

        [0xFNV1A]
        name = "<FunctionName>"
        rva  = "0x...."
        sig  = "<bytes with ?? wildcards>"

Usage:
    python fork_pattern_dumper.py <steamclient64.dll> [--out-dir DIR]
                                  [--sigs steamclient_ida_sigs.json]

Exit code is non-zero if any function fails to resolve uniquely, so CI fails
loudly when Valve reshapes a function and a signature needs re-minting.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pefile


# ── FNV-1a (32-bit) — must match OpenSteamTool's Fnv1aHash ─────────────────
def fnv1a_32(name: str) -> int:
    h = 0x811C9DC5
    for c in name.encode("ascii"):
        h = ((h ^ c) * 0x01000193) & 0xFFFFFFFF
    return h


# ── signature parsing / scanning ──────────────────────────────────────────
def parse_sig(sig: str) -> tuple[bytes, bytes]:
    """Return (bytes, mask) where mask byte 0 == wildcard."""
    out_b = bytearray()
    out_m = bytearray()
    for tok in sig.split():
        if tok in ("?", "??"):
            out_b.append(0)
            out_m.append(0)
        else:
            out_b.append(int(tok, 16))
            out_m.append(1)
    return bytes(out_b), bytes(out_m)


def find_unique(text: bytes, pat: bytes, mask: bytes) -> list[int]:
    """All offsets in `text` where the masked pattern matches."""
    hits: list[int] = []
    n, m = len(text), len(pat)
    if m == 0 or n < m:
        return hits
    first = pat[0]
    has_fixed_first = mask[0] == 1
    i = 0
    while i <= n - m:
        if has_fixed_first:
            i = text.find(first, i, n - m + 1)
            if i < 0:
                break
        ok = True
        for j in range(m):
            if mask[j] and text[i + j] != pat[j]:
                ok = False
                break
        if ok:
            hits.append(i)
        i += 1
    return hits


def get_text_section(pe: pefile.PE) -> tuple[bytes, int]:
    """Return (.text bytes, .text RVA)."""
    for sec in pe.sections:
        if sec.Name.rstrip(b"\x00") == b".text":
            return sec.get_data(), sec.VirtualAddress
    raise RuntimeError(".text section not found")


# ── main resolve ───────────────────────────────────────────────────────────
def resolve(dll_path: Path, sigs: dict[str, str]) -> tuple[dict[str, dict], int]:
    pe = pefile.PE(str(dll_path), fast_load=True)
    text, text_rva = get_text_section(pe)

    results: dict[str, dict] = {}
    failures = 0
    for name, sig in sigs.items():
        if name.startswith("_"):
            continue  # metadata keys in the JSON
        pat, mask = parse_sig(sig)
        hits = find_unique(text, pat, mask)
        if len(hits) == 1:
            rva = text_rva + hits[0]
            results[name] = {"rva": rva, "sig": sig}
            print(f"[HIGH] {name:<26} rva=0x{rva:X}")
        elif len(hits) == 0:
            print(f"[MISS] {name:<26} signature not found")
            failures += 1
        else:
            print(f"[MISS] {name:<26} {len(hits)} matches (ambiguous)")
            failures += 1
    return results, failures


def write_toml(results: dict[str, dict], sha256: str, out_dir: Path) -> Path:
    sc_dir = out_dir / "steamclient"
    sc_dir.mkdir(parents=True, exist_ok=True)
    path = sc_dir / f"{sha256}.toml"
    lines: list[str] = []
    for name in sorted(results):
        entry = results[name]
        lines.append(f"[0x{fnv1a_32(name):08X}]")
        lines.append(f'name = "{name}"')
        lines.append(f'rva = "0x{entry["rva"]:X}"')
        lines.append(f'sig = "{entry["sig"]}"')
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description="OST fork-only pattern dumper")
    ap.add_argument("dll", help="path to steamclient64.dll")
    ap.add_argument("--out-dir", default=".", help="output root (default: cwd)")
    ap.add_argument("--sigs", default=None,
                    help="ida sigs json (default: <script dir>/steamclient_ida_sigs.json)")
    args = ap.parse_args()

    dll_path = Path(args.dll)
    if not dll_path.is_file():
        print(f"error: DLL not found: {dll_path}", file=sys.stderr)
        return 2

    sigs_path = Path(args.sigs) if args.sigs else \
        Path(__file__).parent / "steamclient_ida_sigs.json"
    sigs = json.loads(sigs_path.read_text(encoding="utf-8"))

    sha256 = hashlib.sha256(dll_path.read_bytes()).hexdigest()
    print(f"steamclient64.dll SHA-256 = {sha256}")

    results, failures = resolve(dll_path, sigs)
    out_path = write_toml(results, sha256, Path(args.out_dir))
    print(f"wrote {out_path} ({len(results)} functions)")

    if failures:
        print(f"::error::{failures} fork function(s) failed to resolve", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
