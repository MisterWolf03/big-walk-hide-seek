from pathlib import Path

core_path = Path('in-game-mod/core/CoreEntry.cs')
proj_path = Path('in-game-mod/core/BigWalkHideSeek.Core.csproj')

s = core_path.read_text(encoding='utf-8')
p = proj_path.read_text(encoding='utf-8')

if '0.0.17' not in s:
    raise SystemExit('Core source is not at 0.0.17')
if '<Version>0.0.17</Version>' not in p:
    raise SystemExit('Core project is not at 0.0.17')

old = '''                int i = (y * width + x) * 4;
                // BGRA32 equivalent of rgba(5,7,10,.72).
'''
new = '''                // sourceY above uses the map/UI's top-origin pixel coordinates,
                // but Unity raw Texture2D data starts at the bottom row. The main
                // embedded map asset is packed the same way, so flip only the raw
                // destination row here. Do NOT alter the game/map coordinate math.
                int destinationY = height - 1 - y;
                int i = (destinationY * width + x) * 4;
                // BGRA32 equivalent of rgba(5,7,10,.72).
'''

count = s.count(old)
if count != 1:
    raise SystemExit(f'constraint mask pixel write: expected 1 match, found {count}')
s = s.replace(old, new, 1)

s = s.replace('0.0.17', '0.0.18')
p = p.replace('<Version>0.0.17</Version>', '<Version>0.0.18</Version>')
p = p.replace('<AssemblyVersion>0.0.17.0</AssemblyVersion>', '<AssemblyVersion>0.0.18.0</AssemblyVersion>')
p = p.replace('<FileVersion>0.0.17.0</FileVersion>', '<FileVersion>0.0.18.0</FileVersion>')

core_path.write_text(s, encoding='utf-8')
proj_path.write_text(p, encoding='utf-8')

print('Applied Core 0.0.18 constraint-mask vertical orientation fix.')
