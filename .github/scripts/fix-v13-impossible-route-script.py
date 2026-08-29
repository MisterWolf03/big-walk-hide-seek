from pathlib import Path
p=Path('.github/scripts/apply-v13-impossible-route.py')
s=p.read_text(encoding='utf-8')
old="insert_at=s.find('soundEnabledEl.onchange=',pos)\nif insert_at==-1: raise SystemExit('mission handler insertion anchor not found')"
new="insert_at=s.find('document.getElementById(\\\"relocationReadyBtn\\\").onclick=',pos)\nif insert_at==-1: raise SystemExit('mission handler insertion anchor not found')"
if s.count(old)!=1:
    raise SystemExit(f'expected one insertion-anchor patch, found {s.count(old)}')
p.write_text(s.replace(old,new,1),encoding='utf-8')
