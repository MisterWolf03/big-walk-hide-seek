from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

def once(old,new,label):
    global s
    count=s.count(old)
    if count!=1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    s=s.replace(old,new,1)

once('const REQUIRED_ROOMS_BUILD_ID="v13-missions-20260827a";',
     'const REQUIRED_ROOMS_BUILD_ID="v13-missions-optional-20260827b";',
     'required rooms build id')
once('<script type="module" src="rooms.js?v=v13-missions-20260827a"></script>',
     '<script type="module" src="rooms.js?v=v13-missions-optional-20260827b"></script>',
     'rooms cache key')

once(
    'let localHiderMissionPlan=null,missionMutationBusy=false;\nlet missionSchedulerError="";',
    'let localHiderMissionPlan=null,missionMutationBusy=false;\nlet missionSchedulerError="";\nlet missionStartRequestPending=false;',
    'mission request state')

once(
    '        <div id="missionMessage" class="small" style="margin-top:8px">First mission becomes available at 10:00.</div>\n      </section>',
    '        <div id="missionMessage" class="small" style="margin-top:8px">First mission becomes available at 10:00.</div>\n        <button class="primary" id="missionStartBtn" style="display:none;margin-top:8px">Start mission</button>\n      </section>',
    'mission start button')

once(
    '          <li>Mission completion awards one Power Charge for the upcoming Hider power system.</li>\n          <li>Mission targets remain local to the Hider browser and are never uploaded to the room.</li>',
    '          <li>Mission completion awards one Power Charge for the upcoming Hider power system.</li>\n          <li>Missions are optional: the Hider chooses when to start an available mission, and Seekers do not see mission countdowns or availability.</li>\n          <li>Mission targets remain local to the Hider browser and are never uploaded to the room.</li>',
    'changelog optional mission note')

old_scheduler='''async function maybeHostAdvanceMission(){
  if(!roomModeConnected()||!roomCanDriveMission()||missionMutationBusy||!roomMatchRunning())return;
  const now=currentMatchSeconds();
  if(missionState.active){
    if(!window.BigWalkRooms?.hasHider?.()){
      missionMutationBusy=true;
      try{
        missionState={...missionState,active:false,nextAt:now+nextMissionDelay(),startedAt:null,lastResult:"cancelled",token:""};
        relocationState={...relocationState,active:false,nextAt:now+relocationSettings.interval,startedAt:null,deadline:null};
        resetLocalHiderMissionPlan();
        await window.BigWalkRooms.pushGameState();
      }finally{missionMutationBusy=false;}
      return;
    }
    const signal=window.BigWalkRooms?.getHiderMissionSignal?.();
    if(signal&&Number(signal.index)===Number(missionState.index)&&String(signal.token||"")===String(missionState.token||"")&&signal.result){
      missionMutationBusy=true;
      try{
        const result=String(signal.result);
        if(result==="completed")hiderPowerCharges=Math.max(0,Number(hiderPowerCharges||0))+1;
        missionState={...missionState,active:false,nextAt:now+nextMissionDelay(),startedAt:null,lastResult:result,token:""};
        relocationState={...relocationState,active:false,nextAt:now+relocationSettings.interval,startedAt:null,deadline:null};
        resetLocalHiderMissionPlan();
        await window.BigWalkRooms.pushGameState();
      }finally{missionMutationBusy=false;}
    }
    return;
  }
  if(relocationState.active||!window.BigWalkRooms?.hasHider?.())return;
  const nextAt=Number(missionState.nextAt??missionSettings.firstAt);
  if(!Number.isFinite(nextAt)||now+.01<nextAt)return;
  missionMutationBusy=true;
  try{
    missionState={active:true,index:Number(missionState.index||0)+1,nextAt:null,type:"crossZone",startedAt:now,lastResult:"",token:makeMissionToken()};
    relocationState={...relocationState,nextAt:null};
    resetLocalHiderMissionPlan();
    await window.BigWalkRooms.pushGameState();
  }finally{missionMutationBusy=false;}
}'''

new_scheduler='''async function maybeHostAdvanceMission(){
  if(!roomModeConnected()||!roomCanDriveMission()||missionMutationBusy||!roomMatchRunning())return;
  const now=currentMatchSeconds();
  if(missionState.active){
    if(!window.BigWalkRooms?.hasHider?.()){
      missionMutationBusy=true;
      try{
        missionState={...missionState,active:false,available:false,nextAt:now+nextMissionDelay(),startedAt:null,lastResult:"cancelled",token:""};
        relocationState={...relocationState,active:false,nextAt:now+relocationSettings.interval,startedAt:null,deadline:null};
        resetLocalHiderMissionPlan();
        await window.BigWalkRooms.pushGameState();
      }finally{missionMutationBusy=false;}
      return;
    }
    const signal=window.BigWalkRooms?.getHiderMissionSignal?.();
    if(signal&&Number(signal.index)===Number(missionState.index)&&String(signal.token||"")===String(missionState.token||"")&&signal.result){
      missionMutationBusy=true;
      try{
        const result=String(signal.result);
        if(result==="completed")hiderPowerCharges=Math.max(0,Number(hiderPowerCharges||0))+1;
        missionState={...missionState,active:false,available:false,nextAt:now+nextMissionDelay(),startedAt:null,lastResult:result,token:""};
        relocationState={...relocationState,active:false,nextAt:now+relocationSettings.interval,startedAt:null,deadline:null};
        resetLocalHiderMissionPlan();
        await window.BigWalkRooms.pushGameState();
      }finally{missionMutationBusy=false;}
    }
    return;
  }
  if(missionState.available){
    if(!window.BigWalkRooms?.hasHider?.()||relocationState.active)return;
    const startSignal=window.BigWalkRooms?.getHiderMissionStartSignal?.();
    if(!startSignal||Number(startSignal.index)!==Number(missionState.index)||String(startSignal.token||"")!==String(missionState.token||""))return;
    missionMutationBusy=true;
    try{
      missionState={...missionState,active:true,available:false,nextAt:null,startedAt:now,lastResult:""};
      relocationState={...relocationState,nextAt:null};
      resetLocalHiderMissionPlan();
      await window.BigWalkRooms.pushGameState();
    }finally{missionMutationBusy=false;}
    return;
  }
  if(relocationState.active||!window.BigWalkRooms?.hasHider?.())return;
  const nextAt=Number(missionState.nextAt??missionSettings.firstAt);
  if(!Number.isFinite(nextAt)||now+.01<nextAt)return;
  missionMutationBusy=true;
  try{
    missionState={active:false,available:true,index:Number(missionState.index||0)+1,nextAt:null,type:"crossZone",startedAt:null,lastResult:"",token:makeMissionToken()};
    resetLocalHiderMissionPlan();
    await window.BigWalkRooms.pushGameState();
  }finally{missionMutationBusy=false;}
}'''
once(old_scheduler,new_scheduler,'optional mission scheduler')

start=s.index('function updateMissionUi(){')
end=s.index('\n\nfunction updateLocalRelocation(){',start)
new_ui='''function updateMissionUi(){
  const section=document.getElementById("missionGameSection"),headline=document.getElementById("missionHeadline"),status=document.getElementById("missionStatus"),type=document.getElementById("missionType"),progress=document.getElementById("missionProgress"),charges=document.getElementById("hiderPowerCharges"),message=document.getElementById("missionMessage"),startBtn=document.getElementById("missionStartBtn");
  if(!section)return;
  if(!missionState.available)missionStartRequestPending=false;
  startBtn.style.display="none";startBtn.disabled=true;startBtn.textContent="Start mission";
  section.classList.toggle("missionActive",!!missionState.active);
  type.textContent="Cross the Zone";
  charges.textContent=isRoomHider()||!roomModeConnected()?String(Math.max(0,Number(hiderPowerCharges||0))):"Hidden";
  const now=currentMatchSeconds();
  if(!roomModeConnected()){
    section.style.display="block";
    headline.textContent=formatTime(Math.max(0,Number(missionState.nextAt??missionSettings.firstAt)-now));status.textContent="Rooms required";progress.textContent="—";message.textContent="Hider missions activate during shared room matches.";return;
  }
  if(!isRoomHider()&&!missionState.active){
    section.style.display="none";
    return;
  }
  section.style.display="block";
  if(missionState.active){
    headline.textContent="ACTIVE";
    if(isRoomHider()){
      status.textContent="Cross the Zone";
      if(window.BigWalkRooms?.getBuildId?.()!==REQUIRED_ROOMS_BUILD_ID){progress.textContent="Refresh required";message.textContent="Room sync module is out of date — hard refresh this browser.";}
      else if(!liveMarker){progress.textContent="Waiting for live tracker";message.textContent="Connect live location to generate your private purple target area.";}
      else if(!localHiderMissionPlan){progress.textContent="Calculating…";message.textContent="Finding the opposite side of the connected legal search area.";}
      else if(localHiderMissionPlan.invalid){progress.textContent="Cancelling…";message.textContent="No safe opposite-side target is available. The relocation timer will restart fresh.";}
      else if(localHiderMissionPlan.signaled){progress.textContent=localHiderMissionPlan.pendingResult==="completed"?"Target reached":"Cancelling";message.textContent=localHiderMissionPlan.pendingResult==="completed"?"Mission complete — confirming your Power Charge and restarting the relocation timer.":"Mission target became invalid — restarting the relocation timer.";}
      else{
        const d=missionDistanceToTarget(liveMarker,localHiderMissionPlan);
        progress.textContent=Number.isFinite(d)?`${Math.max(0,Math.round(d))} units to target`:"Target active";
        message.textContent="Reach the purple target area on the opposite side of the remaining legal search zone. The target is visible only to you.";
      }
    }else{
      status.textContent="Hider mission in progress";progress.textContent="Target hidden";message.textContent="Cross the Zone is active. The Hider's purple target and live position remain private; forced relocation will restart fresh when the mission ends.";
    }
    return;
  }
  if(isRoomHider()&&missionState.available){
    headline.textContent="AVAILABLE";status.textContent="Optional";progress.textContent="Not started";
    startBtn.style.display="block";
    const buildOk=window.BigWalkRooms?.getBuildId?.()===REQUIRED_ROOMS_BUILD_ID;
    const canStart=buildOk&&roomMatchRunning()&&!relocationState.active&&!!liveMarker&&!missionStartRequestPending;
    startBtn.disabled=!canStart;
    startBtn.textContent=missionStartRequestPending?"Starting…":"Start mission";
    if(!buildOk)message.textContent="Room sync module is out of date — hard refresh this browser.";
    else if(!roomMatchRunning())message.textContent="Mission is available. Resume the match before starting it.";
    else if(relocationState.active)message.textContent="Mission is available, but it cannot start during forced relocation. You can accept it after relocation finishes.";
    else if(!liveMarker)message.textContent="Mission is available. Connect live location before starting so your private target can be generated.";
    else if(missionStartRequestPending)message.textContent="Starting Cross the Zone…";
    else message.textContent="Optional mission. Start it whenever you want; until then, the forced-relocation countdown continues normally.";
    return;
  }
  const nextAt=Number(missionState.nextAt??missionSettings.firstAt),remaining=Math.max(0,nextAt-now);
  headline.textContent=formatTime(remaining);progress.textContent="—";
  status.textContent=missionState.lastResult?`Last: ${missionState.lastResult}`:"Waiting";
  if(missionSchedulerError)message.textContent=`Mission scheduler error: ${missionSchedulerError}`;
  else if(relocationState.active&&remaining<=.01)message.textContent="The next mission offer will wait until the current forced relocation is completed.";
  else if(!window.BigWalkRooms?.hasHider?.())message.textContent="Waiting for a Hider before the next mission can become available.";
  else message.textContent=`Next optional mission becomes available in ${formatTime(remaining)}. After a mission ends, the next offer is scheduled randomly 10–15 minutes later.`;
}'''
s=s[:start]+new_ui+s[end:]

once(
    'document.addEventListener("keydown",()=>ensureGameAudioContext(),{once:true,capture:true});\ndocument.getElementById("relocationReadyBtn").onclick=()=>{',
    '''document.addEventListener("keydown",()=>ensureGameAudioContext(),{once:true,capture:true});
document.getElementById("missionStartBtn").onclick=async()=>{
  if(!isRoomHider()||!missionState.available||missionState.active||relocationState.active||!roomMatchRunning()||!liveMarker||missionStartRequestPending)return;
  const fn=window.BigWalkRooms?.signalMissionStart;
  if(typeof fn!=="function"||window.BigWalkRooms?.getBuildId?.()!==REQUIRED_ROOMS_BUILD_ID)return;
  missionStartRequestPending=true;renderMatchTimer();
  try{
    await fn(missionState.index,missionState.token);
    setTimeout(()=>{
      if(missionState.available&&!missionState.active){missionStartRequestPending=false;renderMatchTimer();}
    },2000);
  }catch(err){
    console.warn("Mission start request failed",err);missionStartRequestPending=false;renderMatchTimer();
  }
};
document.getElementById("relocationReadyBtn").onclick=()=>{''',
    'mission start button handler')

p.write_text(s,encoding='utf-8')

rp=Path('rooms.js')
r=rp.read_text(encoding='utf-8')

def ronce(old,new,label):
    global r
    count=r.count(old)
    if count!=1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    r=r.replace(old,new,1)

ronce('const ROOMS_BUILD_ID = "v13-missions-20260827a";',
      'const ROOMS_BUILD_ID = "v13-missions-optional-20260827b";',
      'rooms build id')

ronce(
    'function getHiderMissionSignal(){',
    '''function getHiderMissionStartSignal(){
  const entry=hiderMemberEntry();
  if(!entry)return null;
  const [uid,m]=entry;
  return {uid,index:Number(m?.missionStartIndex||0),token:String(m?.missionStartToken||""),requestedAt:Number(m?.missionStartAt||0)};
}
async function signalMissionStart(index,token=""){
  if(!isConnected() || roomRole!=="hider")return false;
  const {dbMod}=firebase;
  await dbMod.update(dbMod.ref(db, `rooms/${roomCode}/members/${user.uid}`), {
    missionStartIndex:Number(index||0),
    missionStartToken:String(token||"").slice(0,128),
    missionStartAt:dbMod.serverTimestamp(),
    lastSeen:dbMod.serverTimestamp(),
  });
  return true;
}

function getHiderMissionSignal(){''',
    'mission start signal functions')

ronce(
    '  getHiderMissionSignal,\n  signalMissionResult,',
    '  getHiderMissionStartSignal,\n  signalMissionStart,\n  getHiderMissionSignal,\n  signalMissionResult,',
    'mission start exports')

rp.write_text(r,encoding='utf-8')
