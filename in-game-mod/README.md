# Big Walk Hide + Seek — In-Game Mod Prototype

Experimental BepInEx 6 IL2CPP client for moving the Hide + Seek interface into Big Walk itself.

## Current milestone: first in-game map build

The Loader/Core architecture and automatic updater are proven in-game.

Current versions:

- `BigWalkHideSeek.Loader.dll` — **0.1.1**
- Published update-feed Core — **0.0.7**
- `mod-prototype` map-test Core source — **0.0.8**

`F7` opens the full-screen Hide + Seek overlay. While it is open, Big Walk camera/player input is gated with `ControlsManager.SetMenuMode(true)`, the mouse is freed, and the native Big Walk menu does not open underneath. Closing the overlay restores normal controls.

Core 0.0.8 is the first real in-game map build. It adds:

- the full `big-walk-map.png` embedded directly into Core;
- drag-to-pan;
- mouse-wheel zoom;
- Fit, Center Me, zoom-in, and zoom-out controls;
- a live local-player marker read directly from Big Walk;
- the same Unity -> Big Walk coordinate conversion used by the proven live-position tracker;
- the same Big Walk -> map-pixel calibration used by the web map.

The map and future gameplay/UI features live in Core so they can be delivered through the updater without replacing the permanent Loader.

## Installed layout

```text
BepInEx/
├── plugins/
│   └── BigWalkHideSeek/
│       └── BigWalkHideSeek.Loader.dll
└── BigWalkHideSeek/
    ├── BigWalkHideSeek.Core.dll
    ├── BigWalkHideSeek.Core.backup.dll
    └── updater-config.json
```

Core deliberately lives outside `BepInEx\plugins` so BepInEx does not inspect/load it before the Loader has a chance to replace it.

## Testing Core 0.0.8 locally

1. Download or update to the latest `mod-prototype` branch.
2. If needed, run `configure_profile.bat` and select the Thunderstore profile containing BepInEx 6 IL2CPP.
3. Run `build_and_install.bat`.
4. Launch Big Walk with **Start modded**.
5. Press `F7`.

Expected result:

- the Big Walk map fills the overlay viewport;
- dragging pans the map;
- the mouse wheel zooms around the cursor;
- `FIT` restores the full-map view;
- `CENTER ME` centers the live player marker;
- the top bar reports live Big Walk X/Y coordinates once the player is found;
- Big Walk movement/camera input remains disabled while the overlay is open;
- `F7`, `Esc`, or `CLOSE` returns to the game normally.

If the player is not immediately available, Core searches once per second for a `Rigidbody` whose GameObject name begins with `PlayerCharacter `, matching the proven tracker approach.

## Automatic Core updater

At game startup Loader 0.1.1:

1. reads `BepInEx\BigWalkHideSeek\updater-config.json`;
2. fetches the update manifest;
3. compares the installed Core version with the manifest version;
4. downloads a newer Core when available;
5. decodes the package when required;
6. verifies the decoded DLL's SHA-256 hash;
7. backs up the previous Core;
8. replaces Core before loading it;
9. loads the current Core and starts the Hide + Seek UI.

The current feed uses `"encoding": "gzip-base64"`. This packaging exists because publishing raw DLL bytes through the GitHub connector altered binary data during earlier tests. The gzip + base64 path has been proven successfully with the automatic Core 0.0.6 -> 0.0.7 update.

If the update server is unavailable, Loader uses the installed Core. If a newly installed Core cannot load, the previous backup is restored on disk for the next launch.

## Preparing a Core update

After changing the Core version/source, run:

```text
prepare_update.bat
```

That builds Core and creates a `publish` folder containing:

- `BigWalkHideSeek.Core.dll`
- `BigWalkHideSeek.Core.gz.b64`
- `latest.json`

`latest.json` contains the Core version, gzip/base64 package URL, SHA-256 hash of the decoded DLL, and the `gzip-base64` encoding declaration.

Do not publish a new Core to the update feed until that build has been tested locally in Big Walk.

## Branch policy

- In-game mod development: `mod-prototype`
- Core update feed: `bw-hs-feed-7c41e9`
- Stable web root is separate and should not be changed or promoted as part of in-game mod work.
