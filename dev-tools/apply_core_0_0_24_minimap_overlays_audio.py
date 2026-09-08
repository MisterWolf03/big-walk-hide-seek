from pathlib import Path
import re

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
s = s.replace('0.0.23', '0.0.24')
p = p.replace('<Version>0.0.23</Version>', '<Version>0.0.24</Version>')
p = p.replace('<AssemblyVersion>0.0.23.0</AssemblyVersion>', '<AssemblyVersion>0.0.24.0</AssemblyVersion>')
p = p.replace('<FileVersion>0.0.23.0</FileVersion>', '<FileVersion>0.0.24.0</FileVersion>')

# Square, larger minimap.
once('''    private const float MiniMapWidth = 210f;\n    private const float MiniMapHeight = 164f;''',
     '''    private const float MiniMapWidth = 260f;\n    private const float MiniMapHeight = 260f;''',
     'minimap size')

# Audio should be created after the world/player exists, not on Core's first frame.
once('''        initialized = true;\n        LoadSettings();\n        TryInitializeAudio();''',
     '''        initialized = true;\n        LoadSettings();''',
     'defer audio initialization')

# Initialize audio once the same post-spawn stabilization window used by the map has elapsed.
needle = '''        if (hasPlayerPosition\n            && playerFoundAt >= 0f\n            && Time.unscaledTime - playerFoundAt >= 3f\n            && (overlayOpen || settings.MiniMapEnabled))\n            EnsureMapTexture();\n\n        UpdateMissionProgress();'''
replacement = '''        if (hasPlayerPosition\n            && playerFoundAt >= 0f\n            && Time.unscaledTime - playerFoundAt >= 3f\n            && (overlayOpen || settings.MiniMapEnabled))\n            EnsureMapTexture();\n\n        if (hasPlayerPosition\n            && playerFoundAt >= 0f\n            && Time.unscaledTime - playerFoundAt >= 3f\n            && settings.SoundsEnabled\n            && uiAudioSource == null)\n            TryInitializeAudio();\n\n        UpdateMissionProgress();'''
once(needle, replacement, 'post-spawn audio initialization')

# Replace minimap method with a square clipped map that shares the full-map constraint mask
# and adds saved custom markers. The safe GUI.DrawTexture clipping path from 0.0.23 is retained.
pattern = re.compile(r'''    private void DrawMiniMap\(Rect rect\)\n    \{.*?\n    \}\n\n    private void DrawNavHud\(Rect rect\)''', re.S)
match = pattern.search(s)
if not match:
    raise SystemExit('DrawMiniMap method block not found')

new_method = '''    private void DrawMiniMap(Rect rect)\n    {\n        DrawPanelRect(rect, new Color(0.045f, 0.055f, 0.07f, 0.94f), BorderColor);\n        Rect map = new Rect(rect.x + 5f, rect.y + 5f, rect.width - 10f, rect.height - 10f);\n\n        if (!hasPlayerPosition)\n        {\n            GUI.Label(map, \"LOCATING PLAYER…\", statusStyle);\n            return;\n        }\n\n        Vector2 centerPixel = GameToMapPixel(gameX, gameY);\n        float sourceWidth = 620f;\n        float sourceHeight = sourceWidth;\n        sourceWidth = Mathf.Min(sourceWidth, mapTexture.width);\n        sourceHeight = Mathf.Min(sourceHeight, mapTexture.height);\n\n        float sourceX = Mathf.Clamp(centerPixel.x - sourceWidth * 0.5f, 0f, Mathf.Max(0f, mapTexture.width - sourceWidth));\n        float sourceY = Mathf.Clamp(centerPixel.y - sourceHeight * 0.5f, 0f, Mathf.Max(0f, mapTexture.height - sourceHeight));\n\n        float cropScaleX = map.width / sourceWidth;\n        float cropScaleY = map.height / sourceHeight;\n        Rect fullMapRect = new Rect(\n            -sourceX * cropScaleX,\n            -sourceY * cropScaleY,\n            mapTexture.width * cropScaleX,\n            mapTexture.height * cropScaleY);\n\n        if (constraints.Count > 0)\n            EnsureConstraintMaskTexture();\n\n        // Keep the safe 0.0.23 rendering path: crop by clipping a normal DrawTexture.\n        GUI.BeginGroup(map);\n        GUI.DrawTexture(fullMapRect, mapTexture, ScaleMode.StretchToFill, false);\n        if (constraintMaskTexture != null && constraints.Count > 0)\n            GUI.DrawTexture(fullMapRect, constraintMaskTexture, ScaleMode.StretchToFill, true);\n        GUI.EndGroup();\n\n        foreach (MapFeature tower in Towers)\n        {\n            Vector2 towerPixel = GameToMapPixel(tower.X, tower.Y);\n            if (towerPixel.x < sourceX || towerPixel.x > sourceX + sourceWidth\n                || towerPixel.y < sourceY || towerPixel.y > sourceY + sourceHeight)\n                continue;\n\n            float tx = map.x + ((towerPixel.x - sourceX) / sourceWidth) * map.width;\n            float ty = map.y + ((towerPixel.y - sourceY) / sourceHeight) * map.height;\n            DrawSolidRect(new Rect(tx - 4f, ty - 4f, 8f, 8f), new Color(0.03f, 0.035f, 0.045f, 0.96f));\n            DrawSolidRect(new Rect(tx - 3f, ty - 3f, 6f, 6f), tower.Color);\n        }\n\n        foreach (UserMarker marker in userMarkers)\n        {\n            Vector2 markerPixel = GameToMapPixel(marker.X, marker.Y);\n            if (markerPixel.x < sourceX || markerPixel.x > sourceX + sourceWidth\n                || markerPixel.y < sourceY || markerPixel.y > sourceY + sourceHeight)\n                continue;\n\n            float mx = map.x + ((markerPixel.x - sourceX) / sourceWidth) * map.width;\n            float my = map.y + ((markerPixel.y - sourceY) / sourceHeight) * map.height;\n            DrawSolidRect(new Rect(mx - 5f, my - 5f, 10f, 10f), new Color(0.03f, 0.035f, 0.045f, 0.98f));\n            DrawSolidRect(new Rect(mx - 3f, my - 3f, 6f, 6f), AccentYellow);\n            GUI.Label(new Rect(mx + 6f, my - 9f, 42f, 18f), $\"M{marker.Id}\", userMarkerLabelStyle);\n        }\n\n        float px = map.x + ((centerPixel.x - sourceX) / sourceWidth) * map.width;\n        float py = map.y + ((centerPixel.y - sourceY) / sourceHeight) * map.height;\n        DrawSolidRect(new Rect(px - 6f, py - 6f, 12f, 12f), new Color(0.03f, 0.035f, 0.045f, 0.98f));\n        DrawSolidRect(new Rect(px - 5f, py - 5f, 10f, 10f), Color.white);\n        DrawSolidRect(new Rect(px - 3f, py - 3f, 6f, 6f), AccentCyan);\n\n        Rect north = new Rect(map.x + map.width * 0.5f - 14f, map.y + 3f, 28f, 18f);\n        DrawPanelRect(north, new Color(0.03f, 0.04f, 0.055f, 0.82f), new Color(1f, 1f, 1f, 0.12f));\n        GUI.Label(north, \"N\", statusStyle);\n    }\n\n    private void DrawNavHud(Rect rect)'''

s = s[:match.start()] + new_method + s[match.end():]

# Harden audio source setup and use direct clip playback instead of PlayOneShot.
once('''            uiAudioSource = gameObject.AddComponent<AudioSource>();\n            uiAudioSource.playOnAwake = false;\n            uiAudioSource.loop = false;\n            uiAudioSource.spatialBlend = 0f;\n\n            softToneClip = CreateToneClip(\"BWHS Soft\", 620f, 0.08f);\n            normalToneClip = CreateToneClip(\"BWHS Normal\", 740f, 0.14f);\n            importantToneClip = CreateToneClip(\"BWHS Important\", 880f, 0.22f);''',
     '''            uiAudioSource = gameObject.AddComponent<AudioSource>();\n            uiAudioSource.playOnAwake = false;\n            uiAudioSource.loop = false;\n            uiAudioSource.spatialBlend = 0f;\n            uiAudioSource.volume = 1f;\n            uiAudioSource.mute = false;\n            uiAudioSource.priority = 0;\n            uiAudioSource.ignoreListenerPause = true;\n\n            softToneClip = CreateToneClip(\"BWHS Soft\", 620f, 0.10f);\n            normalToneClip = CreateToneClip(\"BWHS Normal\", 740f, 0.16f);\n            importantToneClip = CreateToneClip(\"BWHS Important\", 880f, 0.24f);\n            CoreEntry.Logger?.LogInfo(\"Hide + Seek notification audio initialized after world spawn.\");''',
     'audio source setup')

# Preserve generated clips across scene cleanup just like the runtime map texture.
once('''        AudioClip clip = AudioClip.Create(name, sampleCount, 1, sampleRate, false);\n        var data = new Il2CppStructArray<float>(sampleCount);''',
     '''        AudioClip clip = AudioClip.Create(name, sampleCount, 1, sampleRate, false);\n        clip.hideFlags = HideFlags.HideAndDontSave;\n        var data = new Il2CppStructArray<float>(sampleCount);''',
     'audio clip persistence')

play_pattern = re.compile(r'''    private void PlayNotificationTone\(NotificationTone tone\)\n    \{.*?\n    \}\n\n    private void DrawNotifications\(\)''', re.S)
play_match = play_pattern.search(s)
if not play_match:
    raise SystemExit('PlayNotificationTone method block not found')

new_play = '''    private void PlayNotificationTone(NotificationTone tone)\n    {\n        if (uiAudioSource == null)\n        {\n            if (hasPlayerPosition && playerFoundAt >= 0f && Time.unscaledTime - playerFoundAt >= 3f)\n                TryInitializeAudio();\n            if (uiAudioSource == null)\n                return;\n        }\n\n        AudioClip clip = tone == NotificationTone.Important\n            ? importantToneClip\n            : tone == NotificationTone.Normal ? normalToneClip : softToneClip;\n\n        if (clip == null)\n            return;\n\n        try\n        {\n            uiAudioSource.Stop();\n            uiAudioSource.clip = clip;\n            uiAudioSource.volume = Mathf.Clamp01(settings.SoundVolume);\n            uiAudioSource.mute = false;\n            uiAudioSource.Play();\n        }\n        catch (Exception ex)\n        {\n            CoreEntry.Logger?.LogWarning($\"Hide + Seek notification sound playback failed: {ex.Message}\");\n        }\n    }\n\n    private void DrawNotifications()'''

s = s[:play_match.start()] + new_play + s[play_match.end():]

core_path.write_text(s, encoding='utf-8')
proj_path.write_text(p, encoding='utf-8')
print('Applied Core 0.0.24 minimap overlays and post-spawn audio fix.')
