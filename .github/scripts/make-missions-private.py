from pathlib import Path
p=Path('index.html')
s=p.read_text(encoding='utf-8')

def once(old,new,label):
    global s
    n=s.count(old)
    if n!=1:
        raise SystemExit(f'{label}: expected 1 match, found {n}')
    s=s.replace(old,new,1)

once('''  if(!roomModeConnected()){section.style.display="none";return;}\n  if(isRoomHider()&&!missionState.active&&!missionState.available){section.style.display="none";return;}\n  if(!isRoomHider()&&!missionState.active){section.style.display="none";return;}\n  section.style.display="block";\n''','''  if(!roomModeConnected()||!isRoomHider()){section.style.display="none";return;}\n  if(!missionState.active&&!missionState.available){section.style.display="none";return;}\n  section.style.display="block";\n''','mission card hider-only')

once('''  if(missionState.active){\n    eyebrow.textContent="CURRENT OBJECTIVE";title.textContent=isHider?"Cross the Zone":"Hider mission active";\n    if(isHider&&liveMarker&&localHiderMissionPlan&&!localHiderMissionPlan.invalid){const d=missionDistanceToTarget(liveMarker,localHiderMissionPlan);detail.textContent=Number.isFinite(d)?`${Math.max(0,Math.round(d))} units to the purple target area.`:"Reach the private purple target area.";}\n    else detail.textContent=isHider?"Reach the private purple target area.":"The mission target and Hider progress remain private.";\n    next.textContent=isHider?"Forced relocation · paused":"Mission in progress";return;\n  }\n''','''  if(missionState.active&&isHider){\n    eyebrow.textContent="CURRENT OBJECTIVE";title.textContent="Cross the Zone";\n    if(liveMarker&&localHiderMissionPlan&&!localHiderMissionPlan.invalid){const d=missionDistanceToTarget(liveMarker,localHiderMissionPlan);detail.textContent=Number.isFinite(d)?`${Math.max(0,Math.round(d))} units to the purple target area.`:"Reach the private purple target area.";}\n    else detail.textContent="Reach the private purple target area.";\n    next.textContent="Forced relocation · paused";return;\n  }\n''','dashboard mission privacy')

once('''  else if(roomModeConnected()&&missionState.active)topSub.textContent=roomRole()==="hider"?"Hider mission active":"Match running";\n''','''  else if(roomModeConnected()&&missionState.active&&isRoomHider())topSub.textContent="Hider mission active";\n''','top timer mission privacy')

once('''          <li>Missions are optional: the Hider chooses when to start an available mission, and Seekers do not see mission countdowns or availability.</li>\n''','''          <li>Missions are optional and completely private to the Hider UI: Seekers receive no mission countdown, availability, active-state, progress, or completion indication.</li>\n''','mission changelog privacy')

# Guard against known seeker-facing mission wording returning in this build.
for forbidden in ('Mission in progress','Hider mission active</','The mission target and Hider progress remain private.'):
    if forbidden in s:
        raise SystemExit(f'seeker mission wording still present: {forbidden}')

p.write_text(s,encoding='utf-8')
