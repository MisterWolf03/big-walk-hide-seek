from pathlib import Path


def once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    return text.replace(old, new, 1)

# rooms.js: attach a per-relocation token to the Hider overtime signal.
p = Path("rooms.js")
r = p.read_text(encoding="utf-8")
r = once(
    r,
    '''  const x=Number(m?.relocationOvertimeX),y=Number(m?.relocationOvertimeY),revealedAt=Number(m?.relocationOvertimeAt||0);\n  return {uid,index:Number(m?.relocationOvertimeIndex||0),x,y,revealedAt};''',
    '''  const x=Number(m?.relocationOvertimeX),y=Number(m?.relocationOvertimeY),revealedAt=Number(m?.relocationOvertimeAt||0);\n  const token=String(m?.relocationOvertimeToken||"");\n  return {uid,index:Number(m?.relocationOvertimeIndex||0),x,y,revealedAt,token};''',
    "read overtime token",
)
r = once(
    r,
    '''async function signalRelocationOvertime(index,x,y){\n  if(!isConnected() || roomRole!=="hider" || !Number.isFinite(Number(x)) || !Number.isFinite(Number(y)))return false;''',
    '''async function signalRelocationOvertime(index,x,y,token=""){\n  if(!isConnected() || roomRole!=="hider" || !Number.isFinite(Number(x)) || !Number.isFinite(Number(y)))return false;''',
    "signal overtime signature",
)
r = once(
    r,
    '''    relocationOvertimeY:Number(y),\n    relocationOvertimeAt:dbMod.serverTimestamp(),''',
    '''    relocationOvertimeY:Number(y),\n    relocationOvertimeToken:String(token||"").slice(0,96),\n    relocationOvertimeAt:dbMod.serverTimestamp(),''',
    "write overtime token",
)
p.write_text(r, encoding="utf-8")

# index.html: unique relocation token + confirmed retry loop.
p = Path("index.html")
s = p.read_text(encoding="utf-8")
s = once(
    s,
    '''let localRelocationOvertimeSignalIndex=0;\nlet localHiderMissionTargetCells=null;''',
    '''let localRelocationOvertimeSignalIndex=0;\nlet localRelocationOvertimeSnapshot=null;\nlet localRelocationOvertimeLastAttempt=0;\nlet localHiderMissionTargetCells=null;''',
    "local overtime retry state",
)

old_func = '''function maybeSignalRelocationOvertime(){\n  if(!isRoomHider()||!roomMatchRunning()||!relocationState.active||!liveMarker)return;\n  const index=Number(relocationState.index||0),deadline=Number(relocationState.deadline);\n  if(!index||!Number.isFinite(deadline)||currentMatchSeconds()+.01<deadline)return;\n  const existing=window.BigWalkRooms?.getHiderOvertimeSignal?.();\n  if(existing&&Number(existing.index)>=index){localRelocationOvertimeSignalIndex=index;return;}\n  if(localRelocationOvertimeSignalIndex>=index)return;\n  localRelocationOvertimeSignalIndex=index;\n  Promise.resolve(window.BigWalkRooms?.signalRelocationOvertime?.(index,liveMarker.x,liveMarker.y)).catch(err=>{\n    console.warn("Relocation overtime reveal signal failed",err);\n    if(localRelocationOvertimeSignalIndex===index)localRelocationOvertimeSignalIndex=index-1;\n  });\n}\nfunction activeOvertimeReveal(){\n  if(!roomModeConnected()||roomRole()!=="seeker")return null;\n  const signal=window.BigWalkRooms?.getHiderOvertimeSignal?.();\n  if(!signal)return null;\n  const x=Number(signal.x),y=Number(signal.y),revealedAt=Number(signal.revealedAt||0);\n  if(!Number.isFinite(x)||!Number.isFinite(y)||!Number.isFinite(revealedAt)||revealedAt<=0)return null;\n  const now=Number(window.BigWalkRooms?.getServerNow?.()||Date.now()),age=now-revealedAt;\n  if(age<0||age>=OVERTIME_REVEAL_MS)return null;\n  return {x,y,radius:OVERTIME_REVEAL_RADIUS,remainingMs:OVERTIME_REVEAL_MS-age,index:Number(signal.index||0)};\n}'''
new_func = '''function currentRelocationOvertimeToken(){\n  return String(relocationState?.overtimeToken||"");\n}\nfunction makeRelocationOvertimeToken(){\n  if(globalThis.crypto?.randomUUID)return crypto.randomUUID();\n  const a=new Uint32Array(4);crypto.getRandomValues(a);\n  return `ot-${Date.now()}-${Array.from(a,n=>n.toString(36)).join("")}`;\n}\nfunction maybeSignalRelocationOvertime(){\n  if(!isRoomHider()||!roomMatchRunning()||!relocationState.active||!liveMarker)return;\n  const index=Number(relocationState.index||0),deadline=Number(relocationState.deadline),token=currentRelocationOvertimeToken();\n  if(!index||!token||!Number.isFinite(deadline)||currentMatchSeconds()+.01<deadline)return;\n  const existing=window.BigWalkRooms?.getHiderOvertimeSignal?.();\n  if(existing&&Number(existing.index)===index&&String(existing.token||"")===token&&Number.isFinite(Number(existing.revealedAt))&&Number(existing.revealedAt)>0){\n    localRelocationOvertimeSignalIndex=index;\n    localRelocationOvertimeSnapshot=null;\n    return;\n  }\n  if(!localRelocationOvertimeSnapshot||localRelocationOvertimeSnapshot.token!==token){\n    localRelocationOvertimeSnapshot={index,token,x:Number(liveMarker.x),y:Number(liveMarker.y)};\n    localRelocationOvertimeLastAttempt=0;\n  }\n  const now=Date.now();\n  if(now-localRelocationOvertimeLastAttempt<1000)return;\n  localRelocationOvertimeLastAttempt=now;\n  const snap=localRelocationOvertimeSnapshot;\n  Promise.resolve(window.BigWalkRooms?.signalRelocationOvertime?.(snap.index,snap.x,snap.y,snap.token)).catch(err=>{\n    console.warn("Relocation overtime reveal signal failed",err);\n    localRelocationOvertimeLastAttempt=0;\n  });\n}\nfunction activeOvertimeReveal(){\n  if(!roomModeConnected()||roomRole()!=="seeker")return null;\n  const token=currentRelocationOvertimeToken();\n  if(!token)return null;\n  const signal=window.BigWalkRooms?.getHiderOvertimeSignal?.();\n  if(!signal||Number(signal.index)!==Number(relocationState.index||0)||String(signal.token||"")!==token)return null;\n  const x=Number(signal.x),y=Number(signal.y),revealedAt=Number(signal.revealedAt||0);\n  if(!Number.isFinite(x)||!Number.isFinite(y)||!Number.isFinite(revealedAt)||revealedAt<=0)return null;\n  const now=Number(window.BigWalkRooms?.getServerNow?.()||Date.now()),age=now-revealedAt;\n  if(age<0||age>=OVERTIME_REVEAL_MS)return null;\n  return {x,y,radius:OVERTIME_REVEAL_RADIUS,remainingMs:OVERTIME_REVEAL_MS-age,index:Number(signal.index||0),token};\n}'''
s = once(s, old_func, new_func, "replace overtime signal pipeline")

old_active = '''  if(relocationState.active){\n    const signal=window.BigWalkRooms?.getHiderRelocationSignal?.();'''
new_active = '''  if(relocationState.active){\n    if(!currentRelocationOvertimeToken()){\n      relocationMutationBusy=true;\n      try{\n        relocationState={...relocationState,overtimeToken:makeRelocationOvertimeToken()};\n        await window.BigWalkRooms.pushGameState();\n      }finally{relocationMutationBusy=false;}\n      return;\n    }\n    const signal=window.BigWalkRooms?.getHiderRelocationSignal?.();'''
s = once(s, old_active, new_active, "seed token for active legacy relocation")

old_start = '''    relocationState={active:true,index:Number(relocationState.index||0)+1,nextAt:Number(relocationState.nextAt||relocationSettings.firstAt),startedAt:now,deadline:now+relocationSettings.window,lastResult:""};'''
new_start = '''    relocationState={active:true,index:Number(relocationState.index||0)+1,nextAt:Number(relocationState.nextAt||relocationSettings.firstAt),startedAt:now,deadline:now+relocationSettings.window,lastResult:"",overtimeToken:makeRelocationOvertimeToken()};'''
s = once(s, old_start, new_start, "new relocation token")

# Reset local retry state at both reset sites.
reset_old='''relocationState={active:false,index:0,nextAt:relocationSettings.firstAt,startedAt:null,deadline:null,lastResult:""};resetLocalRelocationPlan();'''
reset_new='''relocationState={active:false,index:0,nextAt:relocationSettings.firstAt,startedAt:null,deadline:null,lastResult:""};resetLocalRelocationPlan();localRelocationOvertimeSnapshot=null;localRelocationOvertimeSignalIndex=0;'''
count=s.count(reset_old)
if count != 2:
    raise SystemExit(f"reset overtime state: expected 2 matches, found {count}")
s=s.replace(reset_old,reset_new)

old_msg='''      message.textContent=remaining>0?"Questions are locked while the hider relocates.":"Relocation overtime — the hider's last-known 200-unit area is revealed in red for 2 minutes.";'''
new_msg='''      if(remaining>0)message.textContent="Questions are locked while the hider relocates.";\n      else message.textContent=activeOvertimeReveal()?"Relocation overtime — the hider's last-known 200-unit area is revealed in red for 2 minutes.":"Relocation overtime — waiting for the Hider snapshot…";'''
s = once(s, old_msg, new_msg, "seeker overtime diagnostic copy")

p.write_text(s, encoding="utf-8")
