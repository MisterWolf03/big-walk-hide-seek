from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

old='''  const rerollFrom=opts.rerollFrom||null;\n  let minDistance=rerollFrom?Number(rerollFrom.minTargetDistance||0):maxDistance*.70;\n  if(!rerollFrom){\n'''
new='''  const rerollFrom=opts.rerollFrom||null;\n  let minDistance=maxDistance*.70;\n  if(!rerollFrom){\n'''
if s.count(old)!=1:
    raise SystemExit(f'minDistance anchor expected 1, found {s.count(old)}')
s=s.replace(old,new,1)

start='''  }else{\n    const rejected=rerollFrom.targetKeys instanceof Set?rerollFrom.targetKeys:new Set();\n'''
end='''      centerAngle=Math.atan2(seed.y-start.y,seed.x-start.x);\n    }\n  }\n'''
a=s.find(start)
b=s.find(end,a+len(start)) if a!=-1 else -1
if a==-1 or b==-1:
    raise SystemExit('reroll branch anchors not found')
b+=len(end)
replacement='''  }else{\n    const rejected=rerollFrom.targetKeys instanceof Set?rerollFrom.targetKeys:new Set();\n    const rejectedCells=Array.isArray(rerollFrom.targetCells)?rerollFrom.targetCells:[];\n    const outsideRejected=cells.filter(c=>!rejected.has(c.key));\n    let eligible=[];\n    for(const ratio of [.60,.52,.45]){\n      const pool=outsideRejected.filter(c=>c.distance>=maxDistance*ratio);\n      if(pool.length>=4){eligible=pool;break;}\n    }\n    if(!eligible.length){\n      const fallback=outsideRejected.filter(c=>c.distance>=maxDistance*.35);\n      if(fallback.length)eligible=fallback;\n    }\n    const separationFromRejected=c=>{\n      if(!rejectedCells.length)return c.distance;\n      let best=Infinity;\n      for(const r of rejectedCells)best=Math.min(best,Math.hypot(c.x-Number(r.x),c.y-Number(r.y)));\n      return best;\n    };\n    const seed=[...eligible].sort((a,b)=>{\n      const sa=separationFromRejected(a),sb=separationFromRejected(b);\n      return (sb+b.distance*.35)-(sa+a.distance*.35);\n    })[0]||null;\n    if(seed){\n      const separated=eligible.filter(c=>separationFromRejected(c)>=Number(region.step||25)*1.5);\n      const patchPool=separated.length>=4?separated:eligible;\n      targetCells=[...patchPool]\n        .sort((a,b)=>Math.hypot(a.x-seed.x,a.y-seed.y)-Math.hypot(b.x-seed.x,b.y-seed.y))\n        .slice(0,Math.min(14,patchPool.length));\n      centerAngle=Math.atan2(seed.y-start.y,seed.x-start.x);\n    }\n  }\n'''
s=s[:a]+replacement+s[b:]

old_confirm='''    if(!window.confirm("Reroll this Cross the Zone target? You can only use Impossible Route once this mission, and the replacement will not be closer than the current target."))return;'''
new_confirm='''    if(!window.confirm("Reroll this Cross the Zone target? You can only use Impossible Route once this mission. The replacement will prioritize a distinctly different legal area, even if terrain forces it somewhat closer."))return;'''
if s.count(old_confirm)!=1:
    raise SystemExit(f'confirm anchor expected 1, found {s.count(old_confirm)}')
s=s.replace(old_confirm,new_confirm,1)

needle='''    <div id="view-changelog" class="panelView">\n      <div class="panelHeader"><h2>Changelog</h2><button class="closePanel">Hide</button></div>\n\n'''
entry='''    <div id="view-changelog" class="panelView">\n      <div class="panelHeader"><h2>Changelog</h2><button class="closePanel">Hide</button></div>\n\n      <div class="changeEntry">\n        <h4>v1.3.0 preview — Impossible Route distance relaxation</h4>\n        <ul>\n          <li>Impossible Route no longer requires the replacement target to be at least as far away as the rejected target.</li>\n          <li>Replacement cells never reuse rejected target cells and prefer a clearly separated part of the legal zone.</li>\n          <li>The reroll tries 60%, 52%, then 45% of the connected-zone maximum distance before using a 35% emergency floor.</li>\n        </ul>\n      </div>\n'''
if s.count(needle)!=1:
    raise SystemExit(f'changelog anchor expected 1, found {s.count(needle)}')
s=s.replace(needle,entry,1)

p.write_text(s,encoding='utf-8')
