# Big Walk Live Position Tracker

**Current version: v0.2.1**

[Download the current v0.2.1 source package](https://raw.githubusercontent.com/MisterWolf03/big-walk-hide-seek/main/live-position-tracker/releases/BigWalkLivePosition_v0.2.1_source.zip)

The live position tracker is the local BepInEx bridge used by the hosted Big Walk Hide + Seek map for live player positioning.

## v0.2.1

- Keeps the calibrated live Big Walk Y/X output from v0.2.0.
- Adds `OPTIONS` handling for browser preflight requests.
- Adds CORS and private-network response headers so the HTTPS-hosted map can request the loopback bridge at `127.0.0.1`.
- The server still listens on loopback only; it is not exposed to the internet or LAN.

## Install / update

1. Completely close Big Walk first so Windows releases the old plugin DLL.
2. Run `configure_profile.bat` only if your Thunderstore profile path needs changing.
3. Run `build_and_install.bat`.
4. Launch Big Walk with **Start modded** using that Thunderstore profile.
5. The diagnostic page remains available at `http://127.0.0.1:32145/`.

The hosted map may prompt the browser for permission to access a service on the local / loopback network. Allow it for live location to work.

## Release archive

Versioned tracker packages live under `live-position-tracker/releases/`. Future updates can be added there without replacing older versions, while this page always points to the current release.
