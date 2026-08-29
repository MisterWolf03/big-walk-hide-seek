from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

start='''  }else{\n    const rejected=rerollFrom.targetKeys instanceof Set?rerollFrom.targetKeys:new Set();\n'''
end='''    if(best){centerAngle=best.angle;targetCells=best.cells;}\n  }\n'''
a=s.find(start)
b=s.find(end,a+len(start)) if a!=-1 else -1
if a==-1 or b==-1:
    raise SystemExit('reroll branch anchors not found')
b+=len(end)
replacement='''  }else{\n    const rejected=rerollFrom.targetKeys instanceof Set?rerollFrom.targetKeys:new Set();\n    const rejectedCells=Array.isArray(rerollFrom.targetCells)?rerollFrom.targetCells:[];\n    const rcx=rejectedCells.length?rejectedCells.reduce((sum,c)=>sum+Number(c.x),0)/rejectedCells.length:Number(start.x);\n    const rcy=rejectedCells.length?rejectedCells.reduce((sum,c)=>sum+Number(c.y),0)/rejectedCells.length:Number(start.y);\n    const farCells=cells.filter(c=>c.distance>=minDistance);\n    const outsideRejected=farCells.filter(c=>!rejected.has(c.key));\n    const pools=[];\n    if(outsideRejected.length>=4)pools.push(outsideRejected);\n    pools.push(farCells);\n    let best=null;\n    for(const pool of pools){\n      if(!pool.length)continue;\n      const byKey=new Map(pool.map(c=>[c.key,c]));\n      const seeds=[...pool].sort((a,b)=>Math.hypot(b.x-rcx,b.y-rcy)-Math.hypot(a.x-rcx,a.y-rcy));\n      for(const seed of seeds){\n        const queue=[seed],seen=new Set([seed.key]),patch=[];\n        while(queue.length&&patch.length<14){\n          const cur=queue.shift();patch.push(cur);\n          const neighbors=[\n            relocationCellKey(cur.x+Number(region.step||25),cur.y),\n            relocationCellKey(cur.x-Number(region.step||25),cur.y),\n            relocationCellKey(cur.x,cur.y+Number(region.step||25)),\n            relocationCellKey(cur.x,cur.y-Number(region.step||25))\n          ].map(key=>byKey.get(key)).filter(Boolean)\n           .sort((a,b)=>Math.hypot(b.x-rcx,b.y-rcy)-Math.hypot(a.x-rcx,a.y-rcy));\n          for(const n of neighbors){if(!seen.has(n.key)){seen.add(n.key);queue.push(n);}}\n        }\n        if(patch.length<4)continue;\n        const pcx=patch.reduce((sum,c)=>sum+c.x,0)/patch.length,pcy=patch.reduce((sum,c)=>sum+c.y,0)/patch.length;\n        const shift=Math.hypot(pcx-rcx,pcy-rcy);\n        if(shift<Number(region.step||25)*1.25&&farCells.length>6)continue;\n        const avgDistance=patch.reduce((sum,c)=>sum+c.distance,0)/patch.length;\n        const score=shift+avgDistance*.15+(pool===outsideRejected?maxDistance*.25:0);\n        if(!best||score>best.score)best={cells:patch,cx:pcx,cy:pcy,score};\n      }\n      if(best)break;\n    }\n    if(best){\n      centerAngle=Math.atan2(best.cy-start.y,best.cx-start.x);\n      targetCells=best.cells;\n    }\n  }\n'''
s=s[:a]+replacement+s[b:]

needle='''    <div id="view-changelog" class="panelView">\n      <div class="panelHeader"><h2>Changelog</h2><button class="closePanel">Hide</button></div>\n\n'''
entry='''    <div id="view-changelog" class="panelView">\n      <div class="panelHeader"><h2>Changelog</h2><button class="closePanel">Hide</button></div>\n\n      <div class="changeEntry">\n        <h4>v1.3.0 preview — Impossible Route reroll fix</h4>\n        <ul>\n          <li>Impossible Route now generates a compact connected replacement patch instead of requiring a second sector roughly 90 degrees away.</li>\n          <li>The replacement still cannot be closer than the original target and prefers legal cells outside the rejected purple zone.</li>\n          <li>If the original target already covers nearly the whole far side, the reroll can use a smaller shifted far-side patch rather than producing no target.</li>\n        </ul>\n      </div>\n'''
if s.count(needle)!=1:
    raise SystemExit(f'changelog anchor expected 1, found {s.count(needle)}')
s=s.replace(needle,entry,1)

p.write_text(s,encoding='utf-8')
