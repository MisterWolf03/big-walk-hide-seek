from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

# 1) Replace the directional wedge with the entire far-distance band.
start='  let farthest=cells[0];'
end='  if(!targetCells.length)return '
a=s.find(start)
b=s.find(end,a+len(start)) if a!=-1 else -1
if a==-1 or b==-1:
    raise SystemExit('cross-zone target algorithm anchors not found')
replacement='''  const maxDistance=Math.max(...cells.map(c=>c.distance));\n  if(maxDistance<1)return {index:Number(missionState.index||0),token:String(missionState.token||""),invalid:true};\n  // Cross the Zone is intentionally a broad far-side band instead of one directional wedge.\n  // This reaches the true outer edge and gives the Hider multiple route choices around terrain.\n  let targetCells=cells.filter(c=>c.distance>=maxDistance*.75);\n  if(targetCells.length<6)targetCells=cells.filter(c=>c.distance>=maxDistance*.68);\n  if(targetCells.length<3)targetCells=cells.filter(c=>c.distance>=maxDistance*.60);\n'''
s=s[:a]+replacement+s[b:]

# 2) Draw the purple target with the exact same 10px raster origin/step as the eliminated-zone shading.
start='function drawHiderMissionTarget(){'
a=s.find(start)
b=s.find('\nfunction ',a+len(start)) if a!=-1 else -1
if a==-1 or b==-1:
    raise SystemExit('mission target drawing anchors not found')
replacement='''function drawHiderMissionTarget(){\n  if(!isRoomHider()||!localHiderMissionPlan||!Array.isArray(localHiderMissionTargetCells)||!localHiderMissionTargetCells.length)return;\n  // Match the eliminated-zone raster exactly so purple cells line up with the dark mask.\n  const step=10;\n  ctx.save();\n  ctx.fillStyle=HIDER_MISSION_TARGET_FILL;\n  for(let py=0;py<canvas.height;py+=step){\n    for(let px=0;px<canvas.width;px+=step){\n      const p=pixelToMap(px+step/2,py+step/2);\n      if(pointInMissionTarget(p,localHiderMissionPlan))ctx.fillRect(px,py,step+1,step+1);\n    }\n  }\n  ctx.restore();\n}\n'''
s=s[:a]+replacement+s[b:]

# 3) Update copy so the UI accurately describes the wider target band.
old='Reach the purple target area on the opposite side of the remaining legal search zone. The target is visible only to you.'
new='Reach any part of the purple far-side band in the remaining legal search zone. The target is visible only to you.'
if old not in s:
    raise SystemExit('mission instruction copy not found')
s=s.replace(old,new)
old='`${Math.max(0,Math.round(d))} units to the purple target area.`:"Reach the private purple target area."'
new='`${Math.max(0,Math.round(d))} units to the purple far-side band.`:"Reach the private purple far-side band."'
if old not in s:
    raise SystemExit('dashboard mission copy not found')
s=s.replace(old,new)

# 4) Changelog.
needle='''    <div id="view-changelog" class="panelView">\n      <div class="panelHeader"><h2>Changelog</h2><button class="closePanel">Hide</button></div>\n\n'''
entry='''    <div id="view-changelog" class="panelView">\n      <div class="panelHeader"><h2>Changelog</h2><button class="closePanel">Hide</button></div>\n\n      <div class="changeEntry">\n        <h4>v1.3.0 preview — Cross the Zone target polish</h4>\n        <ul>\n          <li>The purple mission overlay now uses the same raster alignment as eliminated zones.</li>\n          <li>Cross the Zone now includes the true far edge and highlights a broad far-side band, giving the Hider more route choices around difficult terrain.</li>\n        </ul>\n      </div>\n'''
if s.count(needle)!=1:
    raise SystemExit(f'changelog anchor: expected 1 match, got {s.count(needle)}')
s=s.replace(needle,entry,1)

p.write_text(s,encoding='utf-8')
