from pathlib import Path
import re

path = Path('index.html')
s = path.read_text(encoding='utf-8')


def replace_once(old, new, label):
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly 1 match, found {count}')
    s = s.replace(old, new, 1)


def sub_once(pattern, repl, label, flags=0):
    global s
    s2, count = re.subn(pattern, repl, s, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly 1 match, found {count}')
    s = s2

replace_once(
'''let missionSettings={firstAt:600,minInterval:600,maxInterval:900};
let missionState={active:false,index:0,nextAt:600,type:"crossZone",startedAt:null,lastResult:"",token:""};''',
'''let missionSettings={firstAt:600,minInterval:600,maxInterval:900};
const HIDER_MISSION_TYPES=["crossZone","crossReturn"];
const CROSS_RETURN_HOLD_SECONDS=60;
function missionDisplayName(type=missionState?.type){return String(type||"")==="crossReturn"?"Cross & Return":"Cross the Zone";}
function missionRewardForType(type=missionState?.type){return String(type||"")==="crossReturn"?2:1;}
function chooseNextMissionType(){
  const previous=String(missionState?.type||"");
  const choices=HIDER_MISSION_TYPES.filter(t=>t!==previous);
  const pool=choices.length?choices:HIDER_MISSION_TYPES;
  return pool[Math.floor(Math.random()*pool.length)]||"crossZone";
}
let missionState={active:false,index:0,nextAt:600,type:"crossZone",startedAt:null,lastResult:"",token:""};''',
'mission helpers')

replace_once(
'''    centerAngle,minTargetDistance:actualMinDistance,maxDistance,rerollUsed:!!rerollFrom,noAlternate:false,returningHome:false
  };''',
'''    centerAngle,minTargetDistance:actualMinDistance,maxDistance,rerollUsed:!!rerollFrom,noAlternate:false,returningHome:false,
    missionType:String(missionState.type||"crossZone"),holdStartedAt:null,holdSeconds:CROSS_RETURN_HOLD_SECONDS
  };''',
'cross return plan fields')

replace_once(
'''  if(!roomMatchRunning()||!liveMarker)return;
  const index=Number(missionState.index||0),token=String(missionState.token||"");''',
'''  if(!roomMatchRunning())return;
  if(!liveMarker){
    if(localHiderMissionPlan?.missionType==="crossReturn"&&!localHiderMissionPlan.returningHome)localHiderMissionPlan.holdStartedAt=null;
    return;
  }
  const index=Number(missionState.index||0),token=String(missionState.token||"");''',
'live tracker hold reset')

replace_once(
'''    localHiderMissionTargetCells=valid.map(c=>({x:c.x,y:c.y,size:c.size}));
    if(appInitialized)draw();
  }
}
async function maybeHostAdvanceMission(){''',
'''    localHiderMissionTargetCells=valid.map(c=>({x:c.x,y:c.y,size:c.size}));
    if(appInitialized)draw();
  }
  if(plan.missionType==="crossReturn"){
    const inTarget=pointInMissionTarget(liveMarker,plan);
    if(inTarget){
      if(!Number.isFinite(Number(plan.holdStartedAt)))plan.holdStartedAt=currentMatchSeconds();
      const held=Math.max(0,currentMatchSeconds()-Number(plan.holdStartedAt||currentMatchSeconds()));
      if(held>=Number(plan.holdSeconds||CROSS_RETURN_HOLD_SECONDS)){
        beginMissionReturnHome(plan,"completed","Hold complete. Return within 5 units of the hiding spot where you started the mission to earn 2 Power Charges.");
        renderMatchTimer();
        return;
      }
    }else if(plan.holdStartedAt!==null){
      plan.holdStartedAt=null;
    }
  }
}
async function maybeHostAdvanceMission(){''',
'cross return hold logic')

replace_once(
'''        if(result==="completed")hiderPowerCharges=Math.max(0,Number(hiderPowerCharges||0))+1;''',
'''        if(result==="completed")hiderPowerCharges=Math.max(0,Number(hiderPowerCharges||0))+missionRewardForType(missionState.type);''',
'mission reward amount')

replace_once(
'''    missionState={active:false,available:true,index:Number(missionState.index||0)+1,nextAt:null,type:"crossZone",startedAt:null,lastResult:"",token:makeMissionToken()};''',
'''    missionState={active:false,available:true,index:Number(missionState.index||0)+1,nextAt:null,type:chooseNextMissionType(),startedAt:null,lastResult:"",token:makeMissionToken()};''',
'next mission type')

replace_once(
'''  section.classList.toggle("missionActive",!!missionState.active);
  type.textContent="Cross the Zone";
  charges.textContent=isRoomHider()||!roomModeConnected()?String(Math.max(0,Number(hiderPowerCharges||0))):"Hidden";''',
'''  section.classList.toggle("missionActive",!!missionState.active);
  const missionName=missionDisplayName(missionState.type),rewardAmount=missionRewardForType(missionState.type);
  type.textContent=(missionState.active||missionState.available)?missionName:"Random mission";
  charges.textContent=isRoomHider()||!roomModeConnected()?String(Math.max(0,Number(hiderPowerCharges||0))):"Hidden";''',
'mission UI name')

replace_once(
'''      status.textContent="Cross the Zone";''',
'''      status.textContent=missionName;''',
'active mission status')

replace_once(
'''          if(inTarget){
            progress.textContent="Target reached";
            message.textContent="You are inside the purple target area. Find your new hiding spot, then press Complete mission while you remain inside the zone.";
            startBtn.style.display="block";startBtn.disabled=false;startBtn.textContent="Complete mission";
          }else{
            progress.textContent=Number.isFinite(d)?`${Math.max(0,Math.round(d))} units to target`:"Target active";
            message.textContent=plan.rerollUsed?"Reach the replacement purple target. Impossible Route has already been used for this mission.":"Reach the purple far-side target. If terrain makes it genuinely unreachable, you can use Impossible Route once while you are still near your starting hiding spot.";
          }''',
'''          if(inTarget){
            if(plan.missionType==="crossReturn"){
              const held=Number.isFinite(Number(plan.holdStartedAt))?Math.max(0,currentMatchSeconds()-Number(plan.holdStartedAt)):0;
              const holdRemaining=Math.max(0,Number(plan.holdSeconds||CROSS_RETURN_HOLD_SECONDS)-held);
              progress.textContent=`Hold · ${formatTime(Math.ceil(holdRemaining))}`;
              message.textContent="Stay continuously inside the purple target for 1 minute. Leaving the target resets the hold timer. When it reaches zero, your hiding spot guide will appear and you must return home.";
            }else{
              progress.textContent="Target reached";
              message.textContent="You are inside the purple target area. Find your new hiding spot, then press Complete mission while you remain inside the zone.";
              startBtn.style.display="block";startBtn.disabled=false;startBtn.textContent="Complete mission";
            }
          }else{
            progress.textContent=Number.isFinite(d)?`${Math.max(0,Math.round(d))} units to target`:"Target active";
            message.textContent=plan.rerollUsed?"Reach the replacement purple target. Impossible Route has already been used for this mission.":(plan.missionType==="crossReturn"?"Reach the purple far-side target, then stay inside it continuously for 1 minute before returning to your original hiding spot. Impossible Route is available once while you remain near your start.":"Reach the purple far-side target. If terrain makes it genuinely unreachable, you can use Impossible Route once while you are still near your starting hiding spot.");
          }''',
'cross return mission UI')

replace_once(
'''    else if(missionStartRequestPending)message.textContent="Starting Cross the Zone…";
    else message.textContent="Optional mission. Start it whenever you want; until then, the forced-relocation countdown continues normally.";''',
'''    else if(missionStartRequestPending)message.textContent=`Starting ${missionName}…`;
    else message.textContent=`Optional mission · Reward: ${rewardAmount} Power Charge${rewardAmount===1?"":"s"}. Start it whenever you want; until then, the forced-relocation countdown continues normally.`;''',
'available mission reward copy')

replace_once(
'''  else message.textContent=`Cross the Zone is optional. Repeat offers are scheduled randomly ${formatApproxDuration(missionSettings.minInterval)}–${formatApproxDuration(missionSettings.maxInterval)} apart.`;''',
'''  else message.textContent=`The next mission type stays hidden until its offer appears. Repeat offers are scheduled randomly ${formatApproxDuration(missionSettings.minInterval)}–${formatApproxDuration(missionSettings.maxInterval)} apart.`;''',
'waiting mission copy')

replace_once(
'''  if(isRoomHider()&&missionState.active){
    const plan=localHiderMissionPlan;
    if(!roomMatchRunning()||!liveMarker||!plan||plan.invalid||plan.signaled||!pointInMissionTarget(liveMarker,plan))return;
    signalMissionResult("completed");renderMatchTimer();return;
  }''',
'''  if(isRoomHider()&&missionState.active){
    const plan=localHiderMissionPlan;
    if(plan?.missionType==="crossReturn")return;
    if(!roomMatchRunning()||!liveMarker||!plan||plan.invalid||plan.signaled||!pointInMissionTarget(liveMarker,plan))return;
    signalMissionResult("completed");renderMatchTimer();return;
  }''',
'cross return no manual completion')

replace_once(
'''    if(!window.confirm("Reroll this Cross the Zone target? You can only use Impossible Route once this mission. The replacement will prioritize a distinctly different legal area, even if terrain forces it somewhat closer."))return;''',
'''    if(!window.confirm(`Reroll this ${missionDisplayName(missionState.type)} target? You can only use Impossible Route once this mission. The replacement will prioritize a distinctly different legal area, even if terrain forces it somewhat closer.`))return;''',
'dynamic reroll confirmation')

replace_once(
'''  missionAvailable:{kind:"mission",title:"Mission available",detail:"Cross the Zone is ready if you want to accept it."},
  missionStart:{kind:"mission",title:"Mission accepted",detail:"Cross the Zone is active."},''',
'''  missionAvailable:{kind:"mission",title:"Mission available",detail:"A Hider mission is ready if you want to accept it."},
  missionStart:{kind:"mission",title:"Mission accepted",detail:"Your Hider mission is active."},''',
'generic mission audio copy')

old_dashboard='''  if(missionState.active&&isHider){
    eyebrow.textContent="CURRENT OBJECTIVE";title.textContent="Cross the Zone";
    if(liveMarker&&localHiderMissionPlan&&!localHiderMissionPlan.invalid){const inTarget=pointInMissionTarget(liveMarker,localHiderMissionPlan),d=missionDistanceToTarget(liveMarker,localHiderMissionPlan);detail.textContent=inTarget?"Target reached — choose your new hiding spot, then complete the mission.":Number.isFinite(d)?`${Math.max(0,Math.round(d))} units to the purple far-side band.`:"Reach the private purple far-side band.";}
    else detail.textContent="Reach the private purple target area.";
    next.textContent="Forced relocation · paused";return;
  }
  if(isHider&&missionState.available){eyebrow.textContent="OPTIONAL OBJECTIVE";title.textContent="Mission available";detail.textContent="Cross the Zone is ready whenever you want to take it.";return;}'''
new_dashboard='''  if(missionState.active&&isHider){
    eyebrow.textContent="CURRENT OBJECTIVE";title.textContent=missionDisplayName(missionState.type);
    if(liveMarker&&localHiderMissionPlan&&!localHiderMissionPlan.invalid){
      const plan=localHiderMissionPlan,homeD=missionHomeDistance(plan),inTarget=pointInMissionTarget(liveMarker,plan),d=missionDistanceToTarget(liveMarker,plan);
      if(plan.returningHome)detail.textContent=Number.isFinite(homeD)?`${Math.max(0,Math.round(homeD))} units back to your hiding spot.`:"Return to your original hiding spot.";
      else if(plan.missionType==="crossReturn"&&inTarget){
        const held=Number.isFinite(Number(plan.holdStartedAt))?Math.max(0,currentMatchSeconds()-Number(plan.holdStartedAt)):0,remaining=Math.max(0,Number(plan.holdSeconds||CROSS_RETURN_HOLD_SECONDS)-held);
        detail.textContent=`Hold the purple zone continuously · ${formatTime(Math.ceil(remaining))} remaining.`;
      }else if(inTarget)detail.textContent="Target reached — choose your new hiding spot, then complete the mission.";
      else detail.textContent=Number.isFinite(d)?`${Math.max(0,Math.round(d))} units to the purple far-side band.`:"Reach the private purple far-side band.";
    }
    else detail.textContent="Reach the private purple target area.";
    next.textContent="Forced relocation · paused";return;
  }
  if(isHider&&missionState.available){eyebrow.textContent="OPTIONAL OBJECTIVE";title.textContent="Mission available";detail.textContent=`${missionDisplayName(missionState.type)} is ready · Reward ${missionRewardForType(missionState.type)} Power Charge${missionRewardForType(missionState.type)===1?"":"s"}.`;return;}'''
replace_once(old_dashboard,new_dashboard,'dashboard mission copy')

replace_once(
'''          <p class="small">Cross the Zone remains optional and completely private to the Hider UI. Repeat timing is randomized inside the configured range.</p>''',
'''          <p class="small">Hider missions remain optional and private to the Hider UI. Mission type is revealed only when an offer appears; repeat timing is randomized inside the configured range.</p>''',
'mission settings copy')

changelog_anchor='''      <div class="changeEntry">
        <h4>v1.3.0 preview — Impossible Route fallback</h4>'''
changelog_entry='''      <div class="changeEntry">
        <h4>v1.3.0 preview — Cross &amp; Return</h4>
        <ul>
          <li>Added Cross &amp; Return as the second Hider mission, using the same private far-side target and Impossible Route fallback as Cross the Zone.</li>
          <li>The Hider must remain continuously inside the purple target for 60 seconds; leaving resets the hold timer.</li>
          <li>After the hold, the universal Hiding Spot marker and dashed return line appear. Returning within 5 units completes the mission for 2 Power Charges.</li>
          <li>Mission offers now choose from the available mission pool while avoiding an immediate repeat when another mission type is available.</li>
        </ul>
      </div>
''' + changelog_anchor
replace_once(changelog_anchor,changelog_entry,'cross return changelog')

# Basic guards
for needle in [
    'const HIDER_MISSION_TYPES=["crossZone","crossReturn"]',
    'const CROSS_RETURN_HOLD_SECONDS=60',
    'missionType:String(missionState.type||"crossZone")',
    'beginMissionReturnHome(plan,"completed","Hold complete.',
    'missionRewardForType(missionState.type)',
    'type:chooseNextMissionType()',
    'Hold · ${formatTime(Math.ceil(holdRemaining))}',
    'v1.3.0 preview — Cross &amp; Return'
]:
    if needle not in s:
        raise SystemExit(f'missing validation needle: {needle}')

path.write_text(s, encoding='utf-8')
