from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

def once(old,new,label):
    global s
    n=s.count(old)
    if n!=1:
        raise SystemExit(f'{label}: expected 1 match, found {n}')
    s=s.replace(old,new,1)

# Add a distinct mission-available sound before the existing mission-start cue.
once('''  else if(name==="relocationComplete"){tone(392,.00,.11,.55,"triangle");tone(523,.09,.13,.65,"triangle");tone(659,.19,.24,.8,"sine");}\n  else if(name==="missionStart"){tone(523,.00,.12,.65,"triangle");tone(659,.10,.13,.72,"triangle");tone(784,.21,.24,.85,"sine");}\n''', '''  else if(name==="relocationComplete"){tone(392,.00,.11,.55,"triangle");tone(523,.09,.13,.65,"triangle");tone(659,.19,.24,.8,"sine");}\n  else if(name==="missionAvailable"){tone(494,.00,.10,.55,"triangle");tone(659,.09,.11,.68,"triangle");tone(988,.19,.25,.85,"sine");}\n  else if(name==="missionStart"){tone(523,.00,.12,.65,"triangle");tone(659,.10,.13,.72,"triangle");tone(784,.21,.24,.85,"sine");}\n''','mission available tone')

once('''  relocationComplete:{kind:"relocation",title:"Relocation complete",detail:"A fresh relocation interval has started."},\n  missionStart:{kind:"mission",title:"Mission started",detail:"Cross the Zone is active."},\n''', '''  relocationComplete:{kind:"relocation",title:"Relocation complete",detail:"A fresh relocation interval has started."},\n  missionAvailable:{kind:"mission",title:"Mission available",detail:"Cross the Zone is ready if you want to accept it."},\n  missionStart:{kind:"mission",title:"Mission accepted",detail:"Cross the Zone is active."},\n''','mission cue metadata')

# Track availability in the audio/cue state.
once('''    relocationReady:localRelocationReadyNow(),\n    missionActive:roomModeConnected()&&!!missionState.active,\n    missionIndex:Number(missionState.index||0),\n''', '''    relocationReady:localRelocationReadyNow(),\n    missionAvailable:roomModeConnected()&&!!missionState.available,\n    missionActive:roomModeConnected()&&!!missionState.active,\n    missionIndex:Number(missionState.index||0),\n''','capture mission availability')

# Fire availability and accepted cues, but suppress reset-related completion/cancel cues.
once('''  if(prev.relocationActive&&!now.relocationActive)triggerGameCue("relocationComplete");\n  if(!prev.relocationReady&&now.relocationReady)triggerGameCue("relocationReady");\n  if(!prev.missionActive&&now.missionActive)triggerGameCue("missionStart");\n  if(prev.missionActive&&!now.missionActive)triggerGameCue(now.missionLastResult==="completed"?"missionComplete":"missionCancel");\n  audioEventSnapshot=now;\n''', '''  if(prev.relocationActive&&!now.relocationActive&&now.sec>.1)triggerGameCue("relocationComplete");\n  if(!prev.relocationReady&&now.relocationReady)triggerGameCue("relocationReady");\n  if(now.running&&!prev.missionAvailable&&now.missionAvailable)triggerGameCue("missionAvailable");\n  if(now.running&&!prev.missionActive&&now.missionActive)triggerGameCue("missionStart");\n  if(prev.missionActive&&!now.missionActive&&now.sec>.1)triggerGameCue(now.missionLastResult==="completed"?"missionComplete":"missionCancel");\n  audioEventSnapshot=now;\n''','mission event transitions')

# The exact mission-reset assignment appears in both standalone and room reset paths.
reset_old='''  missionState={active:false,index:0,nextAt:missionSettings.firstAt,type:"crossZone",startedAt:null,lastResult:"",token:""};hiderPowerCharges=0;resetLocalHiderMissionPlan();\n'''
reset_new='''  missionState={active:false,available:false,index:0,nextAt:missionSettings.firstAt,type:"crossZone",startedAt:null,lastResult:"",token:""};hiderPowerCharges=0;missionStartRequestPending=false;missionSchedulerError="";resetLocalHiderMissionPlan();\n'''
count=s.count(reset_old)
if count!=2:
    raise SystemExit(f'mission reset state: expected 2 matches, found {count}')
s=s.replace(reset_old,reset_new)

# Add a short preview changelog entry.
once('''    <div id="view-changelog" class="panelView">\n      <div class="panelHeader"><h2>Changelog</h2><button class="closePanel">Hide</button></div>\n\n''', '''    <div id="view-changelog" class="panelView">\n      <div class="panelHeader"><h2>Changelog</h2><button class="closePanel">Hide</button></div>\n\n      <div class="changeEntry">\n        <h4>v1.3.0 preview — Mission reset + cues</h4>\n        <ul>\n          <li>Match reset now explicitly clears available/active mission state and all local mission progress.</li>\n          <li>Added Hider-only visual/audio cues when a mission becomes available and when it is accepted.</li>\n          <li>Resetting an active mission no longer plays a misleading mission-cancelled cue.</li>\n        </ul>\n      </div>\n''','changelog')

p.write_text(s,encoding='utf-8')
