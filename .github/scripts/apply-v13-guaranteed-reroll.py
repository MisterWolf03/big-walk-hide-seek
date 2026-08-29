from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')
start='''  }else{\n    const rejected=rerollFrom.targetKeys instanceof Set?rerollFrom.targetKeys:new Set();\n'''
end='''    if(best){\n      centerAngle=Math.atan2(best.cy-start.y,best.cx-start.x);\n      targetCells=best.cells;\n    }\n  }\n'''
a=s.find(start)
b=s.find(end,a+len(start)) if a!=-1 else -1
if a==-1 or b==-1:
    raise SystemExit('reroll branch anchors not found')
b+=len(end)
replacement='''  }else{\n    const rejected=rerollFrom.targetKeys instanceof Set?rerollFrom.targetKeys:new Set();\n    const rejectedCells=Array.isArray(rerollFrom.targetCells)?rerollFrom.targetCells:[];\n    const rcx=rejectedCells.length?rejectedCells.reduce((sum,c)=>sum+Number(c.x),0)/rejectedCells.length:Number(start.x);\n    const rcy=rejectedCells.length?rejectedCells.reduce((sum,c)=>sum+Number(c.y),0)/rejectedCells.length:Number(start.y);\n    let farCells=cells.filter(c=>c.distance>=minDistance);\n    if(!farCells.length)farCells=[...cells].sort((a,b)=>b.distance-a.distance).slice(0,Math.min(12,cells.length));\n    const outsideRejected=farCells.filter(c=>!rejected.has(c.key));\n    const seedPool=outsideRejected.length?outsideRejected:farCells;\n    const seed=[...seedPool].sort((a,b)=>Math.hypot(b.x-rcx,b.y-rcy)-Math.hypot(a.x-rcx,a.y-rcy))[0]||null;\n    if(seed){\n      const preferred=outsideRejected.length?outsideRejected:farCells;\n      targetCells=[...preferred]\n        .sort((a,b)=>Math.hypot(a.x-seed.x,a.y-seed.y)-Math.hypot(b.x-seed.x,b.y-seed.y))\n        .slice(0,Math.min(14,Math.max(1,preferred.length)));\n      if(targetCells.length<4&&farCells.length>targetCells.length){\n        const picked=new Set(targetCells.map(c=>c.key));\n        for(const c of [...farCells].sort((a,b)=>Math.hypot(a.x-seed.x,a.y-seed.y)-Math.hypot(b.x-seed.x,b.y-seed.y))){\n          if(picked.has(c.key))continue;\n          targetCells.push(c);picked.add(c.key);\n          if(targetCells.length>=Math.min(4,farCells.length))break;\n        }\n      }\n      centerAngle=Math.atan2(seed.y-start.y,seed.x-start.x);\n    }\n  }\n'''
s=s[:a]+replacement+s[b:]

needle='''    <div id="view-changelog" class="panelView">\n      <div class="panelHeader"><h2>Changelog</h2><button class="closePanel">Hide</button></div>\n\n'''
entry='''    <div id="view-changelog" class="panelView">\n      <div class="panelHeader"><h2>Changelog</h2><button class="closePanel">Hide</button></div>\n\n      <div class="changeEntry">\n        <h4>v1.3.0 preview — Guaranteed Impossible Route target</h4>\n        <ul>\n          <li>Impossible Route no longer requires far-side cells to form a four-cell adjacency cluster before a replacement can appear.</li>\n          <li>The reroll now chooses the far legal point most separated from the rejected target and builds the replacement from the nearest equally-far legal cells.</li>\n          <li>If the legal far side is fragmented, the replacement can span nearby legal fragments instead of disappearing completely.</li>\n        </ul>\n      </div>\n'''
if s.count(needle)!=1:
    raise SystemExit(f'changelog anchor expected 1, found {s.count(needle)}')
s=s.replace(needle,entry,1)
p.write_text(s,encoding='utf-8')
