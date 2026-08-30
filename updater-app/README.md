# Big Walk Hide + Seek Updater

Standalone Windows installer/updater for the in-game Big Walk Hide + Seek mod.

## Intended user flow

First install:

1. Run `BigWalkHideSeek.Updater.exe`.
2. Select the Thunderstore **Big Walk profile root** (the folder containing `BepInEx`).
3. Click **INSTALL MOD**.
4. Close the updater.
5. Open Thunderstore and use **Start modded** like normal.

Later updates:

1. Run the updater.
2. Click **CHECK FOR UPDATES**.
3. If a newer Loader or Core exists, the updater downloads, SHA-256 verifies, backs up, and replaces it automatically.
4. Close the updater and launch modded through Thunderstore.

The updater deliberately does **not** launch Big Walk. Thunderstore remains the game/mod launcher.

## Install paths

Loader:

`<profile>\BepInEx\plugins\BigWalkHideSeek\BigWalkHideSeek.Loader.dll`

Core:

`<profile>\BepInEx\BigWalkHideSeek\BigWalkHideSeek.Core.dll`

The app also creates the Loader's `updater-config.json` on fresh installs, so the existing in-game Core updater remains available as a fallback.

## Feed

Updater v0.1 expects:

`https://raw.githubusercontent.com/MisterWolf03/big-walk-hide-seek/bw-hs-feed-7c41e9/feed/9f6d2a/updater.json`

Schema:

```json
{
  "schemaVersion": 1,
  "loader": {
    "version": "0.1.1.0",
    "url": "https://...",
    "sha256": "...",
    "encoding": "gzip-base64"
  },
  "core": {
    "version": "0.0.10.0",
    "url": "https://...",
    "sha256": "...",
    "encoding": "gzip-base64"
  },
  "releaseNotes": "..."
}
```

Supported package encodings are `raw`, `base64`, and `gzip-base64`.

Targets are hard-coded in the updater rather than supplied by the remote manifest, so a feed edit cannot redirect installation outside the expected Big Walk Hide + Seek folders.

## Build

Run `publish_updater.bat`, or:

```bat
dotnet publish BigWalkHideSeek.Updater.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:EnableCompressionInSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true
```

The self-contained build does not require friends to install the .NET runtime separately.
