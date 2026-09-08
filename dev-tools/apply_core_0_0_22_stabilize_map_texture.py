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
s = s.replace('0.0.21', '0.0.22')
p = p.replace('<Version>0.0.21</Version>', '<Version>0.0.22</Version>')
p = p.replace('<AssemblyVersion>0.0.21.0</AssemblyVersion>', '<AssemblyVersion>0.0.22.0</AssemblyVersion>')
p = p.replace('<FileVersion>0.0.21.0</FileVersion>', '<FileVersion>0.0.22.0</FileVersion>')

once(
'''    private Rigidbody playerRb;\n    private float nextPlayerSearchAt;\n    private bool hasPlayerPosition;\n''',
'''    private Rigidbody playerRb;\n    private float nextPlayerSearchAt;\n    private float playerFoundAt = -1f;\n    private bool hasPlayerPosition;\n''',
'player stabilization timestamp field')

once(
'''        if (hasPlayerPosition && (overlayOpen || settings.MiniMapEnabled))\n            EnsureMapTexture();\n''',
'''        if (hasPlayerPosition\n            && playerFoundAt >= 0f\n            && Time.unscaledTime - playerFoundAt >= 3f\n            && (overlayOpen || settings.MiniMapEnabled))\n            EnsureMapTexture();\n''',
'passive map stabilization delay')

once(
'''        if (hasPlayerPosition)\n            EnsureMapTexture();\n    }\n\n    private void UpdateMatchTimer()\n''',
'''        if (hasPlayerPosition\n            && playerFoundAt >= 0f\n            && Time.unscaledTime - playerFoundAt >= 3f)\n            EnsureMapTexture();\n    }\n\n    private void UpdateMatchTimer()\n''',
'overlay update stabilization delay')

once(
'''            UpdatePlayerPosition();\n            if (hasPlayerPosition)\n                EnsureMapTexture();\n            CoreEntry.Logger?.LogInfo("Hide + Seek overlay opened; ControlsManager menu mode enabled.");\n''',
'''            UpdatePlayerPosition();\n            if (hasPlayerPosition\n                && playerFoundAt >= 0f\n                && Time.unscaledTime - playerFoundAt >= 3f)\n                EnsureMapTexture();\n            CoreEntry.Logger?.LogInfo("Hide + Seek overlay opened; ControlsManager menu mode enabled.");\n''',
'overlay open stabilization delay')

# Record when the real PlayerCharacter first appears. This is intentionally tied
# to the existing proven player-search path instead of scene-name guesses.
old_log = '                CoreEntry.Logger?.LogInfo($"Map player found: \'{rb.gameObject.name}\'.");\n'
new_log = '                playerFoundAt = Time.unscaledTime;\n                CoreEntry.Logger?.LogInfo($"Map player found: \'{rb.gameObject.name}\'. Waiting 3 seconds before creating map texture.");\n'
once(old_log, new_log, 'player-found timestamp')

# Keep the runtime-created texture out of Unity unload/scene cleanup paths.
once(
'''                mapTexture = new Texture2D(width, height, TextureFormat.BGRA32, false);\n                Il2CppStructArray<byte> il2cppBytes = ToIl2CppByteArray(pixelBytes);\n''',
'''                mapTexture = new Texture2D(width, height, TextureFormat.BGRA32, false);\n                mapTexture.hideFlags = HideFlags.HideAndDontSave;\n                Il2CppStructArray<byte> il2cppBytes = ToIl2CppByteArray(pixelBytes);\n''',
'persistent map texture')

# While the three-second safety window is active, make the HUD status truthful.
once(
'''        string title = !hasPlayerPosition\n            ? "WAITING FOR WORLD…"\n            : (mapLoadAttempted ? "MAP RETRYING…" : "MAP LOADING…");\n''',
'''        bool stabilizing = hasPlayerPosition\n            && playerFoundAt >= 0f\n            && Time.unscaledTime - playerFoundAt < 3f;\n        string title = !hasPlayerPosition\n            ? "WAITING FOR WORLD…"\n            : (stabilizing ? "MAP STARTING…" : (mapLoadAttempted ? "MAP RETRYING…" : "MAP LOADING…"));\n''',
'minimap stabilization status')

core_path.write_text(s, encoding='utf-8')
proj_path.write_text(p, encoding='utf-8')
print('Applied Core 0.0.22 map texture stabilization fix.')
