from pathlib import Path

core_path = Path('in-game-mod/core/CoreEntry.cs')
proj_path = Path('in-game-mod/core/BigWalkHideSeek.Core.csproj')
s = core_path.read_text(encoding='utf-8')
p = proj_path.read_text(encoding='utf-8')


def once(old, new, label):
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly 1 match, found {count}')
    s = s.replace(old, new, 1)

# Version bump.
s = s.replace('0.0.20', '0.0.21')
p = p.replace('<Version>0.0.20</Version>', '<Version>0.0.21</Version>')
p = p.replace('<AssemblyVersion>0.0.20.0</AssemblyVersion>', '<AssemblyVersion>0.0.21.0</AssemblyVersion>')
p = p.replace('<FileVersion>0.0.20.0</FileVersion>', '<FileVersion>0.0.21.0</FileVersion>')

once(
'''        EnsureInitialized();
        UpdateMatchTimer();

        // Texture creation/loading belongs in the normal Unity update loop.
        // 0.0.19 attempted this from OnGUI for the passive mini-map, which can
        // leave the one-shot loader stuck before the texture becomes usable.
        if (overlayOpen || settings.MiniMapEnabled)
            EnsureMapTexture();

        bool needsPosition = overlayOpen
            || missionActive
            || settings.MiniMapEnabled
            || settings.NavHudEnabled
            || settings.MissionHudEnabled;
        if (needsPosition)
            UpdatePlayerPosition();

        UpdateMissionProgress();
''',
'''        EnsureInitialized();
        UpdateMatchTimer();

        bool needsPosition = overlayOpen
            || missionActive
            || settings.MiniMapEnabled
            || settings.NavHudEnabled
            || settings.MissionHudEnabled;
        if (needsPosition)
            UpdatePlayerPosition();

        // Do not construct the large Unity Texture2D during the bootstrap/title
        // scene. 0.0.20's log proved the resource itself loaded correctly, but
        // it was created roughly 20 seconds before WorldScene and PlayerCharacter
        // existed. Wait for the real local player, matching the proven 0.0.18
        // timing, then load once the game world is actually alive.
        if (hasPlayerPosition && (overlayOpen || settings.MiniMapEnabled))
            EnsureMapTexture();

        UpdateMissionProgress();
''',
'update load timing')

once(
'''        Cursor.visible = true;
        Cursor.lockState = CursorLockMode.None;
        EnsureMapTexture();
''',
'''        Cursor.visible = true;
        Cursor.lockState = CursorLockMode.None;
        if (hasPlayerPosition)
            EnsureMapTexture();
''',
'overlay update load guard')

once(
'''            EnterOverlayInputMode();
            Cursor.visible = true;
            Cursor.lockState = CursorLockMode.None;
            EnsureMapTexture();
            UpdatePlayerPosition();
            CoreEntry.Logger?.LogInfo("Hide + Seek overlay opened; ControlsManager menu mode enabled.");
''',
'''            EnterOverlayInputMode();
            Cursor.visible = true;
            Cursor.lockState = CursorLockMode.None;
            UpdatePlayerPosition();
            if (hasPlayerPosition)
                EnsureMapTexture();
            CoreEntry.Logger?.LogInfo("Hide + Seek overlay opened; ControlsManager menu mode enabled.");
''',
'overlay open load ordering')

once(
'''        string title = mapLoadAttempted ? "MAP RETRYING…" : "MAP LOADING…";
''',
'''        string title = !hasPlayerPosition
            ? "WAITING FOR WORLD…"
            : (mapLoadAttempted ? "MAP RETRYING…" : "MAP LOADING…");
''',
'minimap waiting status')

core_path.write_text(s, encoding='utf-8')
proj_path.write_text(p, encoding='utf-8')
print('Applied Core 0.0.21 deferred map loading until PlayerCharacter exists.')
