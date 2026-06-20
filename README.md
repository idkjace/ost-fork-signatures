# OST Fork Signatures

Distribution endpoint for the **OpenSteamTool fork-only** `steamclient64.dll`
signatures — the functions powering the in-client build/version switch that
aren't tracked by the upstream `steam-monitor` project.

This repo is a **pure receiver**. It does not generate anything itself. The
private `ost-steam-monitor` repo reverse-engineers and extracts the signatures,
then pushes the fork-only subset here (to the `pattern` branch) on every Steam
client update. OpenSteamTool's `PatternLoader` downloads from that branch at
runtime — a public URL, so end users need no authentication.

## Data flow

```
Valve SteamCMD ─► ost-steam-monitor CI (private, producer)
                        │  extract full patterns
                        │  export fork-only subset (renamed)
                        ▼  push via deploy key
                  ost-fork-signatures @ pattern  (this repo, public)
                        │
                        ▼  raw.githubusercontent / jsDelivr
                  OpenSteamTool PatternLoader::LoadFork
```

## Layout

```
steamclient/<sha256>.toml   # fork patterns, keyed by steamclient64.dll SHA-256
```

The `pattern` branch is what the tool reads; `main` is just this README.

## TOML format

Consumed verbatim by OpenSteamTool's `PatternLoader`. Each entry is keyed by
the FNV-1a (32-bit) hash of the OpenSteamTool hook name:

```toml
[0x3E4D0FE7]
name = "GetAppBuildID"
rva  = "0x4B0090"
sig  = "89 54 24 ?? 48 89 4C 24 ?? 55 56 57 ..."
```

## Editing signatures

Do **not** edit signatures here — they are overwritten on the next publish.
The source of truth is `ost-steam-monitor` (`steamclient_ida_sigs.json` +
`STEAMCLIENT_FUNCTIONS`, exported via `export_fork_patterns.py`).
