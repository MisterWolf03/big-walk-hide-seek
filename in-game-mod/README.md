# Big Walk Hide + Seek — In-Game Mod Prototype

Experimental BepInEx/IL2CPP client for moving the Hide + Seek interface into Big Walk itself.

## Current milestone: Loader + updateable Core

The overlay/input foundation has been proven in-game. `F7` opens the Hide + Seek overlay, Big Walk's camera/player input is gated with `ControlsManager.SetMenuMode`, the cursor is freed, and closing the overlay restores normal controls.

The project is now split into two assemblies:

- `BigWalkHideSeek.Loader.dll` — tiny permanent BepInEx plugin; checks for Core updates and then loads Core.
- `BigWalkHideSeek.Core.dll` — updateable game/UI logic; future map, missions, questions, Firebase, sabotages, etc. live here.

Installed layout:

```text
BepInEx/
├── plugins/
│   └── BigWalkHideSeek/
│       └── BigWalkHideSeek.Loader.dll
└── BigWalkHideSeek/
    ├── BigWalkHideSeek.Core.dll
    ├── BigWalkHideSeek.Core.backup.dll   (created after the first successful update)
    └── updater-config.json
```

Core deliberately lives outside `BepInEx\plugins` so BepInEx does not inspect/load it before the Loader has a chance to replace it.

## One-time migration test

1. Download the latest `mod-prototype` branch.
2. Run `configure_profile.bat` and select the Thunderstore profile containing `BepInEx`.
3. Run `build_and_install.bat`.
4. The script removes the old all-in-one `BigWalkHideSeek.dll`, builds Loader + Core, and installs both.
5. Launch Big Walk with **Start modded**.
6. Press `F7`.

The test overlay should say:

`AUTO-UPDATE CORE TEST · v0.0.6`

It should behave exactly like the proven v0.0.5 overlay: no native Big Walk menu behind it, no camera/player input while open, free mouse cursor, and normal controls after closing.

## How the updater works

At game startup the Loader:

1. finds `BepInEx\BigWalkHideSeek\updater-config.json`;
2. reads the private manifest URL;
3. compares the installed Core version with the manifest version;
4. downloads a newer Core when available;
5. verifies its SHA-256 hash;
6. backs up the previous Core;
7. replaces Core before Core is loaded;
8. loads the current Core and starts the Hide + Seek UI.

If the update server is unavailable, the Loader simply uses the installed Core. If a newly installed Core cannot load, the previous backup is restored on disk for the next launch.

## Private host still to choose

`updater-config.json` is intentionally created with a blank `manifestUrl` for now. The updater code is in place, but we still need to choose the friends-only HTTPS host/authentication method before turning remote updates on.

The config supports:

```json
{
  "enabled": true,
  "manifestUrl": "https://private-host.example/latest.json",
  "bearerToken": "optional-read-token",
  "timeoutSeconds": 4
}
```

No public mod binary needs to be hosted just to test Loader -> Core locally.

## Preparing a future Core update

After changing the Core version/source, run:

```text
prepare_update.bat "https://PRIVATE_HOST/BigWalkHideSeek.Core.dll"
```

That creates a `publish` folder containing:

- `BigWalkHideSeek.Core.dll`
- `latest.json`

The manifest contains the Core version, download URL, and SHA-256 hash. Once private hosting is selected, publishing those two files is enough for installed Loaders to update automatically.

## Next step

First verify that the Loader successfully starts Core v0.0.6 in-game. Then connect the updater to a private host and prove one real automatic update (for example Core v0.0.6 -> v0.0.7) before beginning the full map port.
