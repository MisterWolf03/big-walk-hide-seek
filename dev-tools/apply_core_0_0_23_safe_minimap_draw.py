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
s = s.replace('0.0.22', '0.0.23')
p = p.replace('<Version>0.0.22</Version>', '<Version>0.0.23</Version>')
p = p.replace('<AssemblyVersion>0.0.22.0</AssemblyVersion>', '<AssemblyVersion>0.0.23.0</AssemblyVersion>')
p = p.replace('<FileVersion>0.0.22.0</FileVersion>', '<FileVersion>0.0.23.0</FileVersion>')

# Unity 6000 + IL2CPP crashes natively inside GUI.DrawTextureWithTexCoords when
# the passive minimap supplies the runtime-created Texture2D. The fullscreen map
# has always used ordinary GUI.DrawTexture successfully, so crop the minimap by
# clipping an enlarged/offset full texture instead of using UV texcoords.
once(
'''        Rect uv = new Rect(
            sourceX / mapTexture.width,
            1f - ((sourceY + sourceHeight) / mapTexture.height),
            sourceWidth / mapTexture.width,
            sourceHeight / mapTexture.height);

        GUI.DrawTextureWithTexCoords(map, mapTexture, uv, false);
''',
'''        float cropScaleX = map.width / sourceWidth;
        float cropScaleY = map.height / sourceHeight;
        Rect fullMapRect = new Rect(
            -sourceX * cropScaleX,
            -sourceY * cropScaleY,
            mapTexture.width * cropScaleX,
            mapTexture.height * cropScaleY);

        // DrawTextureWithTexCoords causes a native IL2CPP AccessViolation on
        // Big Walk's Unity 6000 build. Clip the proven DrawTexture path instead.
        GUI.BeginGroup(map);
        GUI.DrawTexture(fullMapRect, mapTexture, ScaleMode.StretchToFill, false);
        GUI.EndGroup();
''',
'safe minimap crop rendering')

core_path.write_text(s, encoding='utf-8')
proj_path.write_text(p, encoding='utf-8')
print('Applied Core 0.0.23 safe minimap rendering without DrawTextureWithTexCoords.')
