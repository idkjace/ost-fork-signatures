# OST Fork Signatures

Auto-maintained byte signatures + RVAs for the **OpenSteamTool fork-only**
`steamclient64.dll` functions — the ones powering the in-client build/version
switch feature that aren't tracked by the upstream `steam-monitor` project.

A GitHub Action runs daily: it pulls the latest `steamclient64.dll` via
SteamCMD, resolves each fork function with [`fork_pattern_dumper.py`](fork_pattern_dumper.py),
and commits a new TOML keyed by the DLL's SHA-256. OpenSteamTool's
`PatternLoader` fetches these at runtime, so a Steam client update no longer
requires re-shipping the tool.

## Layout

```
steamclient/<sha256>.toml      # per-build patterns (immutable, keyed by DLL hash)
steamclient_ida_sigs.json      # gold-standard IDA signatures (resolver input)
fork_pattern_dumper.py         # resolver: sig -> unique .text match -> RVA -> TOML
```

## TOML format

Consumed verbatim by OpenSteamTool's `PatternLoader`. Each entry is keyed by
the FNV-1a (32-bit) hash of the function name:

```toml
[0x82428E37]
name = "GetAppBuildID"
rva  = "0x4B0090"
sig  = "89 54 24 ?? 48 89 4C 24 ?? 55 56 57 ..."
```

## Tracked functions

| Function | Purpose |
| --- | --- |
| `BIsAppUpToDate` | Play-vs-Update button decision |
| `GetActiveBeta` / `SetActiveBeta` | active branch dot + selection marshaller |
| `GetNumBetas` / `GetBetaInfo` | build-history rows in the panel |
| `GetAppConfigBranchesKV` | injects the branch list the panel renders |
| `GetAppBuildID` | target-build resolver (planner reads this) |
| `GetAppInfoNode` / `GetAppInfoSection` / `KeyValues_FindKeyPath` | appinfo-cache injection |
| `ModifyStateFlags` | forces `UpdateRequired` so the rollback download plans |

## Regenerating signatures

When Valve reshapes a function and the daily run reports `MISS`, re-mint that
function's signature in IDA Pro (`make_signature_for_function`, wildcard
operands) and update `steamclient_ida_sigs.json`.

## Latest builds

<!--TABLE-->

| Steam build | steamclient64.dll SHA-256 | Updated (UTC) |
| --- | --- | --- |
| `1781219792` | `4e20ea4d442d1ac1cacb95bdf3ea7e2b12212dea99f970e66d71018b5c2ffa4c` | 2026-06-20 10:46:38 UTC |
| `1780352834` | `38b75e0d99ce8a42165bf34c6dbb6efbe17071b17be2416d11c80538c50bd3ce` | 2026-06-20 05:48:13 UTC |
<!--/TABLE-->
