from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

def once(old,new,label):
    global s
    n=s.count(old)
    if n!=1:
        raise SystemExit(f'{label}: expected 1 match, found {n}')
    s=s.replace(old,new,1)

# Stop auto-completing the instant the Hider touches the target zone.
once('''  if(pointInMissionTarget(liveMarker,plan))signalMissionResult("completed");\n}\nasync function maybeHostAdvanceMission(){\n''','''}\nasync function maybeHostAdvanceMission(){\n''','remove cross-zone auto completion')

# When inside the target, let the Hider settle on a hiding spot and explicitly finish.
once('''      else{\n        const d=missionDistanceToTarget(liveMarker,localHiderMissionPlan);\n        progress.textContent=Number.isFinite(d)?`${Math.max(0,Math.round(d))} units to target`:"Target active";\n        message.textContent="Reach the purple target area on the opposite side of the remaining legal search zone. The target is visible only to you.";\n      }\n''','''      else{\n        const inTarget=pointInMissionTarget(liveMarker,localHiderMissionPlan);\n        const d=missionDistanceToTarget(liveMarker,localHiderMissionPlan);\n        if(inTarget){\n          progress.textContent="Target reached";\n          message.textContent="You are inside the purple target area. Find your new hiding spot, then press Complete mission while you remain inside the zone.";\n          startBtn.style.display="block";startBtn.disabled=false;startBtn.textContent="Complete mission";\n        }else{\n          progress.textContent=Number.isFinite(d)?`${Math.max(0,Math.round(d))} units to target`:"Target active";\n          message.textContent="Reach the purple target area on the opposite side of the remaining legal search zone. The target is visible only to you.";\n        }\n      }\n''','active mission complete button')

# The mission action button now handles both accepting an offer and explicitly completing Cross the Zone.
once('''document.getElementById("missionStartBtn").onclick=async()=>{\n  if(!isRoomHider()||!missionState.available||missionState.active||relocationState.active||!roomMatchRunning()||!liveMarker||missionStartRequestPending)return;\n''','''document.getElementById("missionStartBtn").onclick=async()=>{\n  if(isRoomHider()&&missionState.active){\n    const plan=localHiderMissionPlan;\n    if(!roomMatchRunning()||!liveMarker||!plan||plan.invalid||plan.signaled||!pointInMissionTarget(liveMarker,plan))return;\n    signalMissionResult("completed");renderMatchTimer();return;\n  }\n  if(!isRoomHider()||!missionState.available||missionState.active||relocationState.active||!roomMatchRunning()||!liveMarker||missionStartRequestPending)return;\n''','mission action click handler')

# Make the large dashboard reflect that reaching the zone is not yet completion.
once('''    if(liveMarker&&localHiderMissionPlan&&!localHiderMissionPlan.invalid){const d=missionDistanceToTarget(liveMarker,localHiderMissionPlan);detail.textContent=Number.isFinite(d)?`${Math.max(0,Math.round(d))} units to the purple target area.`:"Reach the private purple target area.";}\n''','''    if(liveMarker&&localHiderMissionPlan&&!localHiderMissionPlan.invalid){const inTarget=pointInMissionTarget(liveMarker,localHiderMissionPlan),d=missionDistanceToTarget(liveMarker,localHiderMissionPlan);detail.textContent=inTarget?"Target reached — choose your new hiding spot, then complete the mission.":Number.isFinite(d)?`${Math.max(0,Math.round(d))} units to the purple target area.`:"Reach the private purple target area.";}\n''','dashboard target reached state')

# Add a short changelog note.
once('''    <div id="view-changelog" class="panelView">\n      <div class="panelHeader"><h2>Changelog</h2><button class="closePanel">Hide</button></div>\n\n''','''    <div id="view-changelog" class="panelView">\n      <div class="panelHeader"><h2>Changelog</h2><button class="closePanel">Hide</button></div>\n\n      <div class="changeEntry">\n        <h4>v1.3.0 preview — Cross the Zone completion</h4>\n        <ul>\n          <li>Cross the Zone no longer auto-completes when the Hider first enters the purple target.</li>\n          <li>While inside the target, the Hider can settle on a new hiding spot and press Complete mission to finish.</li>\n        </ul>\n      </div>\n''','changelog')

p.write_text(s,encoding='utf-8')
