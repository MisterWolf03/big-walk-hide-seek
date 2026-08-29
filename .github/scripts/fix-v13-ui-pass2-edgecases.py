from pathlib import Path
p=Path('index.html')
s=p.read_text(encoding='utf-8')

def once(old,new,label):
    global s
    c=s.count(old)
    if c!=1: raise SystemExit(f'{label}: expected 1, found {c}')
    s=s.replace(old,new,1)

once('#topLeaveRoomBtn{background:#3b2226;border-color:#6d3438}', '#leaveRoomBtn{background:#3b2226;border-color:#6d3438}', 'leave css')
once('#topLeaveRoomBtn{font-size:11px;padding:6px 7px}', '#leaveRoomBtn{font-size:11px;padding:6px 7px}', 'leave mobile css')
once('''async function maybeHostAdvanceMission(){\n  if(!roomModeConnected()||!roomCanDriveMission()||missionMutationBusy||!roomMatchRunning())return;''','''async function maybeHostAdvanceMission(){\n  if(!roomModeConnected()||!roomCanDriveMission()||missionMutationBusy||!roomMatchRunning()||hidingTimeRemaining()>.01)return;''','mission hide gate')
once('''async function maybeHostAdvanceRelocation(){\n  if(!roomModeConnected()||!roomCanDriveRelocation()||relocationMutationBusy||!roomMatchRunning())return;''','''async function maybeHostAdvanceRelocation(){\n  if(!roomModeConnected()||!roomCanDriveRelocation()||relocationMutationBusy||!roomMatchRunning()||hidingTimeRemaining()>.01)return;''','relocation hide gate')
p.write_text(s,encoding='utf-8')
