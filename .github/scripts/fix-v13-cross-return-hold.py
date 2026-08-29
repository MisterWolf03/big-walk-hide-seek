from pathlib import Path
p=Path('index.html')
s=p.read_text(encoding='utf-8')
repls=[
('if(!Number.isFinite(Number(plan.holdStartedAt)))plan.holdStartedAt=currentMatchSeconds();','if(plan.holdStartedAt===null||!Number.isFinite(Number(plan.holdStartedAt)))plan.holdStartedAt=currentMatchSeconds();'),
('const held=Math.max(0,currentMatchSeconds()-Number(plan.holdStartedAt||currentMatchSeconds()));','const held=Math.max(0,currentMatchSeconds()-Number(plan.holdStartedAt));'),
('const held=Number.isFinite(Number(plan.holdStartedAt))?Math.max(0,currentMatchSeconds()-Number(plan.holdStartedAt)):0;','const held=plan.holdStartedAt!==null&&Number.isFinite(Number(plan.holdStartedAt))?Math.max(0,currentMatchSeconds()-Number(plan.holdStartedAt)):0;'),
('const held=Number.isFinite(Number(plan.holdStartedAt))?Math.max(0,currentMatchSeconds()-Number(plan.holdStartedAt)):0,remaining=','const held=plan.holdStartedAt!==null&&Number.isFinite(Number(plan.holdStartedAt))?Math.max(0,currentMatchSeconds()-Number(plan.holdStartedAt)):0,remaining=')
]
for old,new in repls:
    c=s.count(old)
    if c!=1: raise SystemExit(f'expected 1 match for {old[:50]!r}, got {c}')
    s=s.replace(old,new,1)
for needle in ['plan.holdStartedAt===null||!Number.isFinite','currentMatchSeconds()-Number(plan.holdStartedAt)','plan.holdStartedAt!==null&&Number.isFinite']:
    if needle not in s: raise SystemExit(f'missing {needle}')
p.write_text(s,encoding='utf-8')
