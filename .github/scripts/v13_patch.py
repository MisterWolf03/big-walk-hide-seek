from pathlib import Path

def once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    return text.replace(old, new, 1)

p = Path("rooms.js")
r = p.read_text(encoding="utf-8")

overtime_funcs = '''function getHiderOvertimeSignal(){
  const entry=hiderMemberEntry();
  if(!entry)return null;
  const [uid,m]=entry;
  const x=Number(m?.relocationOvertimeX),y=Number(m?.relocationOvertimeY),revealedAt=Number(m?.relocationOvertimeAt||0);
  return {uid,index:Number(m?.relocationOvertimeIndex||0),x,y,revealedAt};
}
async function signalRelocationOvertime(index,x,y){
  if(!isConnected() || roomRole!=="hider" || !Number.isFinite(Number(x)) || !Number.isFinite(Number(y)))return false;
  const {dbMod}=firebase;
  await dbMod.update(dbMod.ref(db, `rooms/${roomCode}/members/${user.uid}`), {
    relocationOvertimeIndex:Number(index||0),
    relocationOvertimeX:Number(x),
    relocationOvertimeY:Number(y),
    relocationOvertimeAt:dbMod.serverTimestamp(),
    lastSeen:dbMod.serverTimestamp(),
  });
  return true;
}

'''
r = once(r, "function getMatchSeconds(){", overtime_funcs + "function getMatchSeconds(){", "overtime member functions")
r = once(
    r,
    "    await dbMod.set(memberRef, {name,role,joinedAt:dbMod.serverTimestamp(),lastSeen:dbMod.serverTimestamp()});",
    "    await dbMod.update(memberRef, {name,role,joinedAt:dbMod.serverTimestamp(),lastSeen:dbMod.serverTimestamp()});",
    "preserve member gameplay fields on reconnect",
)
r = once(
    r,
    "  getHiderRelocationSignal,\n  signalRelocationComplete,\n};",
    "  getHiderRelocationSignal,\n  signalRelocationComplete,\n  getHiderOvertimeSignal,\n  signalRelocationOvertime,\n  getServerNow:()=>serverNow(),\n};",
    "room exports",
)
p.write_text(r, encoding="utf-8")

p = Path("index.html")
s = p.read_text(encoding="utf-8")
s = once(s, "<title>Big Walk Hide + Seek — Prototype 1.2.0</title>", "<title>Big Walk Hide + Seek — Prototype 1.3.0 Preview</title>", "title")
s = once(s, 'const APP_VERSION="1.2.0";', 'const APP_VERSION="1.3.0-preview";', "app version")
if '<span class="small">v1.2.0</span>' in s:
    s = s.replace('<span class="small">v1.2.0</span>', '<span class="small">v1.3.0 preview</span>', 1)

state_anchor = '''let localRelocationPlan=null,relocationMutationBusy=false;
let relocationSchedulerError="";'''
state_new = '''let localRelocationPlan=null,relocationMutationBusy=false;
let relocationSchedulerError="";
const OVERTIME_REVEAL_RADIUS=200;
const OVERTIME_REVEAL_MS=120000;
const HIDER_MISSION_TARGET_FILL="rgba(147,86,255,.38)";
const HIDER_MISSION_TARGET_EDGE="rgba(201,177,255,.95)";
let localRelocationOvertimeSignalIndex=0;
let localHiderMissionTargetCells=null;
let overtimeRevealWasVisible=false;'''
s = once(s, state_anchor, state_new, "v1.3 state constants")

sound_anchor = '  else if(name==="relocationStart"){tone(220,.00,.16,.9,"square");tone(165,.19,.16,.85,"square");tone(220,.38,.22,.95,"square");}'
sound_new = sound_anchor + '\n  else if(name==="relocationOvertime"){tone(880,.00,.13,1,"square");tone(660,.16,.13,1,"square");tone(880,.32,.13,1,"square");tone(440,.50,.34,1,"sawtooth");}'
s = once(s, sound_anchor, sound_new, "overtime alarm sound")

capture_anchor = '''    relocationActive:roomModeConnected()&&!!relocationState.active,
    relocationIndex:Number(relocationState.index||0),'''
capture_new = '''    relocationActive:roomModeConnected()&&!!relocationState.active,
    relocationOvertime:roomModeConnected()&&!!relocationState.active&&Number.isFinite(Number(relocationState.deadline))&&sec>=Number(relocationState.deadline),
    relocationIndex:Number(relocationState.index||0),'''
s = once(s, capture_anchor, capture_new, "capture overtime event")

event_anchor = '''  if(!prev.relocationActive&&now.relocationActive)playGameSound("relocationStart");
  if(prev.relocationActive&&!now.relocationActive)playGameSound("relocationComplete");'''
event_new = '''  if(!prev.relocationActive&&now.relocationActive)playGameSound("relocationStart");
  if(!prev.relocationOvertime&&now.relocationOvertime)playGameSound("relocationOvertime");
  if(prev.relocationActive&&!now.relocationActive)playGameSound("relocationComplete");'''
s = once(s, event_anchor, event_new, "overtime sound transition")

helpers = '''function maybeSignalRelocationOvertime(){
  if(!isRoomHider()||!roomMatchRunning()||!relocationState.active||!liveMarker)return;
  const index=Number(relocationState.index||0),deadline=Number(relocationState.deadline);
  if(!index||!Number.isFinite(deadline)||currentMatchSeconds()+.01<deadline)return;
  const existing=window.BigWalkRooms?.getHiderOvertimeSignal?.();
  if(existing&&Number(existing.index)>=index){localRelocationOvertimeSignalIndex=index;return;}
  if(localRelocationOvertimeSignalIndex>=index)return;
  localRelocationOvertimeSignalIndex=index;
  Promise.resolve(window.BigWalkRooms?.signalRelocationOvertime?.(index,liveMarker.x,liveMarker.y)).catch(err=>{
    console.warn("Relocation overtime reveal signal failed",err);
    if(localRelocationOvertimeSignalIndex===index)localRelocationOvertimeSignalIndex=index-1;
  });
}
function activeOvertimeReveal(){
  if(!roomModeConnected()||roomRole()!=="seeker")return null;
  const signal=window.BigWalkRooms?.getHiderOvertimeSignal?.();
  if(!signal)return null;
  const x=Number(signal.x),y=Number(signal.y),revealedAt=Number(signal.revealedAt||0);
  if(!Number.isFinite(x)||!Number.isFinite(y)||!Number.isFinite(revealedAt)||revealedAt<=0)return null;
  const now=Number(window.BigWalkRooms?.getServerNow?.()||Date.now()),age=now-revealedAt;
  if(age<0||age>=OVERTIME_REVEAL_MS)return null;
  return {x,y,radius:OVERTIME_REVEAL_RADIUS,remainingMs:OVERTIME_REVEAL_MS-age,index:Number(signal.index||0)};
}
function refreshTransientMapOverlays(){
  const visible=!!activeOvertimeReveal();
  if(visible||overtimeRevealWasVisible)draw();
  overtimeRevealWasVisible=visible;
}

'''
s = once(s, "function updateLocalRelocation(){", helpers + "function updateLocalRelocation(){", "overtime helpers")
s = once(
    s,
    "  if(!liveMarker)return;\n  if(!localRelocationPlan||localRelocationPlan.index!==relocationState.index){",
    "  if(!liveMarker)return;\n  maybeSignalRelocationOvertime();\n  if(!localRelocationPlan||localRelocationPlan.index!==relocationState.index){",
    "signal overtime at deadline",
)

s = once(s, "  if(showTowerRegions)drawTowerRegions();", "  drawOvertimeReveal();\n  drawHiderMissionTarget();\n  if(showTowerRegions)drawTowerRegions();", "overlay draw calls")

draw_helpers = '''function drawOvertimeReveal(){
  const reveal=activeOvertimeReveal();
  if(!reveal)return;
  const c=mapToPixel(reveal.x,reveal.y),px=mapToPixel(reveal.x+reveal.radius,reveal.y),py=mapToPixel(reveal.x,reveal.y+reveal.radius);
  const rx=Math.max(1,Math.hypot(px.x-c.x,px.y-c.y)),ry=Math.max(1,Math.hypot(py.x-c.x,py.y-c.y));
  ctx.save();
  ctx.beginPath();ctx.ellipse(c.x,c.y,rx,ry,0,0,Math.PI*2);
  ctx.fillStyle="rgba(225,43,43,.50)";ctx.fill();
  ctx.lineWidth=4;ctx.strokeStyle="rgba(255,112,112,.95)";ctx.stroke();
  ctx.restore();
}
function drawHiderMissionTarget(){
  if(!isRoomHider()||!Array.isArray(localHiderMissionTargetCells)||!localHiderMissionTargetCells.length)return;
  ctx.save();
  for(const cell of localHiderMissionTargetCells){
    if(!cell||!Number.isFinite(Number(cell.x))||!Number.isFinite(Number(cell.y)))continue;
    const half=Number(cell.size||25)/2;
    const a=mapToPixel(Number(cell.x)-half,Number(cell.y)-half),b=mapToPixel(Number(cell.x)+half,Number(cell.y)+half);
    const x=Math.min(a.x,b.x),y=Math.min(a.y,b.y),w=Math.abs(b.x-a.x),h=Math.abs(b.y-a.y);
    ctx.fillStyle=HIDER_MISSION_TARGET_FILL;ctx.fillRect(x,y,w,h);
    ctx.lineWidth=1.5;ctx.strokeStyle=HIDER_MISSION_TARGET_EDGE;ctx.strokeRect(x,y,w,h);
  }
  ctx.restore();
}

'''
s = once(s, "function drawTowerRegions(){", draw_helpers + "function drawTowerRegions(){", "overlay render helpers")
s = once(s, "    renderMatchTimer();updateGameAudioEvents();return;", "    renderMatchTimer();updateGameAudioEvents();refreshTransientMapOverlays();return;", "refresh transient overlays")

old = '      message.textContent=remaining>0?"Questions are locked while the hider relocates.":"Relocation is overdue; questions remain locked until the hider completes the move.";'
new = "      message.textContent=remaining>0?\"Questions are locked while the hider relocates.\":\"Relocation overtime — the hider's last-known 200-unit area is revealed in red for 2 minutes.\";"
s = once(s, old, new, "seeker overtime copy")

p.write_text(s, encoding="utf-8")
Path("version.json").write_text('{\n  "version": "1.3.0-preview",\n  "released": "2026-08-26"\n}\n', encoding="utf-8")
