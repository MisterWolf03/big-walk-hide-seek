from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

def once(old,new,label):
    global s
    n=s.count(old)
    if n!=1:
        raise SystemExit(f'{label}: expected 1 match, found {n}')
    s=s.replace(old,new,1)

# Add a dedicated fallback action beneath the normal mission action.
once('''        <button class="primary" id="missionStartBtn" style="display:none;margin-top:8px">Start mission</button>\n''','''        <button class="primary" id="missionStartBtn" style="display:none;margin-top:8px">Start mission</button>\n        <button id="missionFallbackBtn" style="display:none;margin-top:8px">Impossible route</button>\n''','mission fallback button')

# Replace Cross the Zone target generation with a far-side sector that can produce one comparable alternate sector.
a=s.find('function buildCrossZoneMissionPlan')
b=s.find('\nfunction pointInMissionTarget',a)
if a==-1 or b==-1:
    raise SystemExit('Cross the Zone function anchors not found')
new_build=r'''function missionAngleDelta(a,b){
  let d=Math.abs(Number(a)-Number(b))%(Math.PI*2);
  return d>Math.PI?Math.PI*2-d:d;
}
function crossZoneCellsForAngle(cells,start,angle,minDistance,halfAngle){
  return cells.filter(c=>c.distance>=minDistance&&missionAngleDelta(Math.atan2(c.y-start.y,c.x-start.x),angle)<=halfAngle);
}
function buildCrossZoneMissionPlan(start,opts={}){
  const region=buildRelocationPlan(start);
  if(!region||region.invalid||!region.seen||!region.seen.size)return {index:Number(missionState.index||0),token:String(missionState.token||""),invalid:true};
  const cells=Array.from(region.seen,key=>{
    const [x,y]=key.split(",").map(Number);
    return {x,y,size:Number(region.step||25),key,distance:Math.hypot(x-start.x,y-start.y)};
  }).filter(c=>Number.isFinite(c.x)&&Number.isFinite(c.y));
  if(cells.length<4)return {index:Number(missionState.index||0),token:String(missionState.token||""),invalid:true};
  const maxDistance=Math.max(...cells.map(c=>c.distance));
  if(maxDistance<1)return {index:Number(missionState.index||0),token:String(missionState.token||""),invalid:true};

  const rerollFrom=opts.rerollFrom||null;
  let minDistance=rerollFrom?Number(rerollFrom.minTargetDistance||0):maxDistance*.70;
  if(!rerollFrom){
    let probe=cells.filter(c=>c.distance>=minDistance);
    if(probe.length<6){minDistance=maxDistance*.62;probe=cells.filter(c=>c.distance>=minDistance);}
    if(probe.length<3)minDistance=maxDistance*.55;
  }

  let centerAngle=null,targetCells=[];
  if(!rerollFrom){
    const farthest=cells.reduce((best,c)=>c.distance>best.distance?c:best,cells[0]);
    centerAngle=Math.atan2(farthest.y-start.y,farthest.x-start.x);
    targetCells=crossZoneCellsForAngle(cells,start,centerAngle,minDistance,Math.PI/3);
    if(targetCells.length<4)targetCells=crossZoneCellsForAngle(cells,start,centerAngle,minDistance,Math.PI/2);
  }else{
    const rejected=rerollFrom.targetKeys instanceof Set?rerollFrom.targetKeys:new Set();
    const rejectedAngle=Number(rerollFrom.centerAngle);
    const centerCandidates=cells.filter(c=>c.distance>=minDistance).sort((x,y)=>y.distance-x.distance);
    let best=null;
    for(const c of centerCandidates){
      const angle=Math.atan2(c.y-start.y,c.x-start.x);
      if(Number.isFinite(rejectedAngle)&&missionAngleDelta(angle,rejectedAngle)<Math.PI/2)continue;
      for(const halfAngle of [Math.PI/3,Math.PI/4,Math.PI/6]){
        const candidate=crossZoneCellsForAngle(cells,start,angle,minDistance,halfAngle);
        if(candidate.length<3)continue;
        const overlap=candidate.filter(cell=>rejected.has(cell.key)).length/candidate.length;
        if(overlap>.25)continue;
        const avg=candidate.reduce((sum,cell)=>sum+cell.distance,0)/candidate.length;
        const score=avg+(1-overlap)*maxDistance*.1;
        if(!best||score>best.score)best={angle,cells:candidate,score};
      }
    }
    if(best){centerAngle=best.angle;targetCells=best.cells;}
  }

  if(!targetCells.length)return {index:Number(missionState.index||0),token:String(missionState.token||""),invalid:true,noComparableAlternate:!!rerollFrom};
  const actualMinDistance=Math.min(...targetCells.map(c=>c.distance));
  return {
    index:Number(missionState.index||0),token:String(missionState.token||""),start:{x:Number(start.x),y:Number(start.y)},
    step:Number(region.step||25),targetCells,targetKeys:new Set(targetCells.map(c=>c.key)),
    constraintKey:missionConstraintKey(),signaled:false,pendingResult:"",invalid:false,
    centerAngle,minTargetDistance:actualMinDistance,maxDistance,rerollUsed:!!rerollFrom,noAlternate:false,returningHome:false
  };
}
function rerollCrossZoneMissionPlan(plan){
  if(!plan||plan.rerollUsed||!plan.start)return false;
  const alt=buildCrossZoneMissionPlan(plan.start,{rerollFrom:plan});
  if(!alt||alt.invalid){
    plan.rerollUsed=true;plan.noAlternate=true;
    localHiderMissionTargetCells=[];
    if(appInitialized)draw();
    return false;
  }
  alt.rerollUsed=true;
  localHiderMissionPlan=alt;
  localHiderMissionTargetCells=alt.targetCells.map(c=>({x:c.x,y:c.y,size:c.size}));
  if(appInitialized)draw();
  return true;
}
function missionHomeDistance(plan,p=liveMarker){
  if(!plan?.start||!p)return Number.NaN;
  return Math.hypot(Number(p.x)-Number(plan.start.x),Number(p.y)-Number(plan.start.y));
}
'''
s=s[:a]+new_build+s[b:]

# Never treat or draw eliminated coordinates as part of the mission target.
once('''function pointInMissionTarget(p,plan){\n  if(!p||!plan?.targetKeys||!plan.step)return false;\n''','''function pointInMissionTarget(p,plan){\n  if(!p||!plan?.targetKeys||!plan.step||!allowedAt(Number(p.x),Number(p.y)))return false;\n''','target legality check')

# Ensure the raster intersection also explicitly respects the eliminated-zone mask.
once('''      if(pointInMissionTarget(p,localHiderMissionPlan))ctx.fillRect(px,py,step+1,step+1);\n''','''      if(allowedAt(p.x,p.y)&&pointInMissionTarget(p,localHiderMissionPlan))ctx.fillRect(px,py,step+1,step+1);\n''','purple raster legality')

# Wire the fallback button into mission rendering.
once('''  const section=document.getElementById("missionGameSection"),headline=document.getElementById("missionHeadline"),status=document.getElementById("missionStatus"),type=document.getElementById("missionType"),progress=document.getElementById("missionProgress"),charges=document.getElementById("hiderPowerCharges"),message=document.getElementById("missionMessage"),startBtn=document.getElementById("missionStartBtn");\n''','''  const section=document.getElementById("missionGameSection"),headline=document.getElementById("missionHeadline"),status=document.getElementById("missionStatus"),type=document.getElementById("missionType"),progress=document.getElementById("missionProgress"),charges=document.getElementById("hiderPowerCharges"),message=document.getElementById("missionMessage"),startBtn=document.getElementById("missionStartBtn"),fallbackBtn=document.getElementById("missionFallbackBtn");\n''','mission UI button lookup')
once('''  startBtn.style.display="none";startBtn.disabled=true;startBtn.textContent="Start mission";\n''','''  startBtn.style.display="none";startBtn.disabled=true;startBtn.textContent="Start mission";\n  fallbackBtn.style.display="none";fallbackBtn.disabled=false;fallbackBtn.textContent="Impossible route";fallbackBtn.classList.remove("danger");\n''','mission UI button reset')

old=r'''      else{
        const inTarget=pointInMissionTarget(liveMarker,localHiderMissionPlan);
        const d=missionDistanceToTarget(liveMarker,localHiderMissionPlan);
        if(inTarget){
          progress.textContent="Target reached";
          message.textContent="You are inside the purple target area. Find your new hiding spot, then press Complete mission while you remain inside the zone.";
          startBtn.style.display="block";startBtn.disabled=false;startBtn.textContent="Complete mission";
        }else{
          progress.textContent=Number.isFinite(d)?`${Math.max(0,Math.round(d))} units to target`:"Target active";
          message.textContent="Reach any part of the purple far-side band in the remaining legal search zone. The target is visible only to you.";
        }
      }
'''
new=r'''      else{
        const plan=localHiderMissionPlan,homeD=missionHomeDistance(plan),elapsed=Math.max(0,currentMatchSeconds()-Number(missionState.startedAt||currentMatchSeconds()));
        if(plan.returningHome){
          progress.textContent=Number.isFinite(homeD)?`${Math.max(0,Math.round(homeD))} units to hiding spot`:"Return home";
          message.textContent="Mission aborted. Return within 5 units of the hiding spot where you started the mission. No Power Charge will be awarded.";
        }else if(plan.noAlternate){
          progress.textContent="No alternate target";
          message.textContent="No equally distant alternate target could be generated. Abort the mission and return to your original hiding spot for no reward.";
          fallbackBtn.style.display="block";fallbackBtn.textContent="Abort mission";fallbackBtn.classList.add("danger");
        }else{
          const inTarget=pointInMissionTarget(liveMarker,plan);
          const d=missionDistanceToTarget(liveMarker,plan);
          if(inTarget){
            progress.textContent="Target reached";
            message.textContent="You are inside the purple target area. Find your new hiding spot, then press Complete mission while you remain inside the zone.";
            startBtn.style.display="block";startBtn.disabled=false;startBtn.textContent="Complete mission";
          }else{
            progress.textContent=Number.isFinite(d)?`${Math.max(0,Math.round(d))} units to target`:"Target active";
            message.textContent=plan.rerollUsed?"Reach the replacement purple target. Impossible Route has already been used for this mission.":"Reach the purple far-side target. If terrain makes it genuinely unreachable, you can use Impossible Route once while you are still near your starting hiding spot.";
          }
          if(plan.rerollUsed){
            fallbackBtn.style.display="block";fallbackBtn.textContent="Abort mission";fallbackBtn.classList.add("danger");
          }else if(elapsed<=90&&Number.isFinite(homeD)&&homeD<=20){
            fallbackBtn.style.display="block";fallbackBtn.textContent="Impossible route";
            fallbackBtn.title=`One reroll available · ${Math.max(0,90-Math.floor(elapsed))}s remaining · stay within 20 units of your start`;
          }
        }
      }
'''
once(old,new,'active mission fallback UI')

# During the return-home phase, finish the failed mission only once the Hider is back within 5 units.
once('''  const plan=localHiderMissionPlan;\n  if(!plan||plan.invalid||plan.signaled)return;\n  const currentConstraintKey=missionConstraintKey();\n''','''  const plan=localHiderMissionPlan;\n  if(!plan||plan.invalid||plan.signaled)return;\n  if(plan.returningHome){\n    const homeD=missionHomeDistance(plan);\n    if(Number.isFinite(homeD)&&homeD<=5)signalMissionResult("cancelled");\n    return;\n  }\n  if(plan.noAlternate)return;\n  const currentConstraintKey=missionConstraintKey();\n''','mission return-home monitor')

# Add the fallback click behavior after the existing mission action handler.
anchor='''document.getElementById("missionStartBtn").onclick=async()=>{\n'''
pos=s.find(anchor)
if pos==-1: raise SystemExit('mission start handler not found')
# Find the next top-level sound/settings handler after the mission handler and insert before it.
insert_at=s.find('soundEnabledEl.onchange=',pos)
if insert_at==-1: raise SystemExit('mission handler insertion anchor not found')
fallback_handler=r'''document.getElementById("missionFallbackBtn").onclick=()=>{
  if(!isRoomHider()||!missionState.active||!roomMatchRunning()||!liveMarker)return;
  const plan=localHiderMissionPlan;
  if(!plan||plan.invalid||plan.signaled||plan.returningHome)return;
  const homeD=missionHomeDistance(plan),elapsed=Math.max(0,currentMatchSeconds()-Number(missionState.startedAt||currentMatchSeconds()));
  if(!plan.rerollUsed){
    if(elapsed>90||!Number.isFinite(homeD)||homeD>20)return;
    if(!window.confirm("Reroll this Cross the Zone target? You can only use Impossible Route once this mission, and the replacement will not be closer than the current target."))return;
    rerollCrossZoneMissionPlan(plan);
    renderMatchTimer();draw();return;
  }
  if(!window.confirm("Abort this mission? You will earn no Power Charge and must return within 5 units of your original hiding spot."))return;
  plan.returningHome=true;plan.noAlternate=false;localHiderMissionTargetCells=[];
  if(Number.isFinite(homeD)&&homeD<=5)signalMissionResult("cancelled");
  renderMatchTimer();draw();
};

'''
s=s[:insert_at]+fallback_handler+s[insert_at:]

# Changelog.
needle='''    <div id="view-changelog" class="panelView">\n      <div class="panelHeader"><h2>Changelog</h2><button class="closePanel">Hide</button></div>\n\n'''
entry='''    <div id="view-changelog" class="panelView">\n      <div class="panelHeader"><h2>Changelog</h2><button class="closePanel">Hide</button></div>\n\n      <div class="changeEntry">\n        <h4>v1.3.0 preview — Impossible Route fallback</h4>\n        <ul>\n          <li>Cross the Zone now offers one guarded Impossible Route reroll during the first 90 seconds and only within 20 units of the mission start.</li>\n          <li>The replacement target must be at least as far away and substantially different from the rejected target.</li>\n          <li>After the reroll, Abort mission is the only fallback and requires returning within 5 units of the original hiding spot for no reward.</li>\n          <li>Purple target raster cells no longer count or draw over eliminated coordinates.</li>\n        </ul>\n      </div>\n'''
if s.count(needle)!=1: raise SystemExit(f'changelog anchor expected 1, found {s.count(needle)}')
s=s.replace(needle,entry,1)

p.write_text(s,encoding='utf-8')
