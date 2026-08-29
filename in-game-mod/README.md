# Big Walk Hide + Seek — In-Game Mod Prototype

Experimental BepInEx/IL2CPP client for moving the Hide + Seek interface into Big Walk itself.

## Prototype 0.0.1 goal

This build proves only the UI foundation:

- plugin loads in Big Walk
- `F7` opens a full-screen Hide + Seek overlay
- `F7` or `Esc` closes it
- cursor is shown/unlocked while the overlay is open
- mouse GUI events are consumed by the overlay where possible

No Firebase, lobby integration, map rendering, mission logic, or updater is included yet.

## Build / install

1. Launch Big Walk modded through your Thunderstore profile at least once so BepInEx generates `BepInEx\interop`.
2. Run `configure_profile.bat` once and select the Thunderstore profile folder that directly contains `BepInEx`.
3. Run `build_and_install.bat`.
4. Launch Big Walk with **Start modded** using the same profile.
5. Press `F7` in-game.

The plugin installs to:

`BepInEx\plugins\BigWalkHideSeek\BigWalkHideSeek.dll`

## First test checklist

- Does Big Walk launch normally?
- Does `F7` open the overlay?
- Does the mouse cursor appear and move normally?
- Does `F7` close it again?
- Does `Esc` close it?
- After closing it, does normal camera/input behavior return?

If the overlay does not appear, send the BepInEx log from the active Thunderstore profile so we can inspect the exact error.

## Next milestone

Once this works reliably, replace the placeholder panel with the Big Walk map and implement pan + zoom, followed by the player's live map marker.
