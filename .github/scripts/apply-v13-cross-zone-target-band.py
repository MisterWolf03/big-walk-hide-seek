from pathlib import Path
import re

p=Path('index.html')
s=p.read_text(encoding='utf-8')

# 1) Replace the directional 72-90% wedge with the entire far-distance band.
pattern=r'''  let farthest=cells\[0\];\n  for\(const c of cells\)if\(c\.distance>farthest\.distance\)farthest=c;\n  const vx=farthest\.x-start\.x,vy=farthest\.y-start\.y,len=Math\.hypot\(vx,vy\);\n  if\(len<1\)return \{index:Number\(missionState\.index\|\|0\),token:String\(missionState\.token\|\|""\),invalid:true\};\n  const ux=vx/len,uy=vy/len;\n  for\(const c of cells\)c\.projection=\(c\.x-start\.x\)\*ux\+\(c\.y-start\.y\)\*uy;\n  const maxProjection=Math\.max\(\.\.\.cells\.map\(c=>c\.projection\)\);\n  let targetCells=cells\.filter\(c=>c\.projection>=maxProjection\*\.72&&c\.projection<=maxProjection\*\.90&&c\.distance>=farthest\.distance\*\.55\);\n  if\(targetCells\.length<4\)targetCells=cells\.filter\(c=>c\.projection>=maxProjection\*\.70&&c\.projection<=maxProjection\*\.97&&c\.distance>=farthest\.distance\*\.50\);\n  if\(targetCells\.length<3\)targetCells=cells\.filter\(c=>c\.projection>=maxProjection\*\.70\);\n'''
replacement='''  const maxDistance=Math.max(...cells.map(c=>c.distance));\n  if(maxDistance<1)return {index:Number(missionState.index||0),token:String(missionState.token||""),invalid:true};\n  // Cross the Zone is intentionally a broad far-side band instead of one directional wedge.\n  // This reaches the true outer edge and gives the Hider multiple route choices around terrain.\n  let targetCells=cells.filter(c=>c.distance>=maxDistance*.75);\n  if(targetCells.length<6)targetCells=cells.filter(c=>c.distance>=maxDistance*.68);\n  if(targetCells.length<3)targetCells=cells.filter(c=>c.distance>=maxDistance*.60);\n'''
s,n=re.subn(pattern,replacement,s,count=1)
if n!=1:
    raise SystemExit(f'cross-zone target algorithm: expected 1 replacement, got {n}')

# 2) Draw the purple target with the exact same 10px raster origin/step as the eliminated-zone shading.
pattern=r'''function drawHiderMissionTarget\(\)\{\n  if\(!isRoomHider\(\)\|\|!Array\.isArray\(localHiderMissionTargetCells\)\|\|!localHiderMissionTargetCells\.length\)return;\n  ctx\.save\(\);\n  for\(const cell of localHiderMissionTargetCells\)\{.*?\n  \}\n  ctx\.restore\(\);\n\}\n'''
replacement='''function drawHiderMissionTarget(){\n  if(!isRoomHider()||!localHiderMissionPlan||!Array.isArray(localHiderMissionTargetCells)||!localHiderMissionTargetCells.length)return;\n  // Match the eliminated-zone raster exactly so purple cells line up with the dark mask.\n  const step=10;\n  ctx.save();\n  ctx.fillStyle=HIDER_MISSION_TARGET_FILL;\n  for(let py=0;py<canvas.height;py+=step){\n    for(let px=0;px<canvas.width;px+=step){\n      const p=pixelToMap(px+step/2,py+step/2);\n      if(pointInMissionTarget(p,localHiderMissionPlan))ctx.fillRect(px,py,step+1,step+1);\n    }\n  }\n  ctx.restore();\n}\n'''
s,n=re.subn(pattern,replacement,s,count=1,flags=re.S)
if n!=1:
    raise SystemExit(f'mission target drawing: expected 1 replacement, got {n}')

# 3) Update copy so the UI accurately describes the wider target band.
s=s.replace('Reach the purple target area on the opposite side of the remaining legal search zone. The target is visible only to you.',
            'Reach any part of the purple far-side band in the remaining legal search zone. The target is visible only to you.')
s=s.replace('`${Math.max(0,Math.round(d))} units to the purple target area.`:"Reach the private purple target area."',
            '`${Math.max(0,Math.round(d))} units to the purple far-side band.`:"Reach the private purple far-side band."')

# 4) Changelog.
needle='''    <div id="view-changelog" class="panelView">\n      <div class="panelHeader"><h2>Changelog</h2><button class="closePanel">Hide</button></div>\n\n'''
entry='''    <div id="view-changelog" class="panelView">\n      <div class="panelHeader"><h2>Changelog</h2><button class="closePanel">Hide</button></div>\n\n      <div class="changeEntry">\n        <h4>v1.3.0 preview — Cross the Zone target polish</h4>\n        <ul>\n          <li>The purple mission overlay now uses the same raster alignment as eliminated zones.</li>\n          <li>Cross the Zone now includes the true far edge and highlights a broad far-side band, giving the Hider more route choices around difficult terrain.</li>\n        </ul>\n      </div>\n'''
if s.count(needle)!=1:
    raise SystemExit(f'changelog anchor: expected 1 match, got {s.count(needle)}')
s=s.replace(needle,entry,1)

p.write_text(s,encoding='utf-8')
