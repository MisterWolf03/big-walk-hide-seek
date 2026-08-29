from pathlib import Path

idx=Path('index.html')
rooms=Path('rooms.js')
s=idx.read_text(encoding='utf-8')
r=rooms.read_text(encoding='utf-8')

def once(text, old, new, label):
    n=text.count(old)
    if n!=1:
        raise SystemExit(f'{label}: expected 1 match, found {n}')
    return text.replace(old,new,1)

# Build id / module cache bust.
s=once(s,'const REQUIRED_ROOMS_BUILD_ID="v13-private-relocation-20260829a";','const REQUIRED_ROOMS_BUILD_ID="v13-mission-role-ui-20260829a";','html build id')
s=once(s,'<script type="module" src="rooms.js?v=v13-private-relocation-20260829a"></script>','<script type="module" src="rooms.js?v=v13-mission-role-ui-20260829a"></script>','module cache id')
r=once(r,'const ROOMS_BUILD_ID = "v13-private-relocation-20260829a";','const ROOMS_BUILD_ID = "v13-mission-role-ui-20260829a";','rooms build id')

# Castle/tower icon without a door.
s=once(s,'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v18M8 21h8M8.5 8 12 3l3.5 5M9.5 13h5M6 7.5l-2 2M18 7.5l2 2"/></svg>',
'''<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 3v7l3 3v8h10v-8l3-3V3h-3v4h-3V3h-4v4H7V3H4Z"/></svg>''','tower castle icon')

# Centerline display shorthand only; game math remains 3700 / 1700.
s=once(s,'<option value="y">Horizontal centerline — Y 3700</option>\n          <option value="x">Vertical centerline — X 1700</option>',
'''<option value="y">Horizontal centerline — Y 37</option>\n          <option value="x">Vertical centerline — X 17</option>''','centerline option labels')
s=once(s,'Centerline questions always cut straight through the middle of the playable map: <b>Y 3700</b> or <b>X 1700</b>.',
'''Centerline questions always cut straight through the middle of the playable map: <b>Y 37</b> or <b>X 17</b>.''','centerline description')
# Centerline history/result wording should use the same shorthand.
s=once(s,'`Hider is ${dir} of ${axis.toUpperCase()} ${value}.`',
'''`Hider is ${dir} of ${axis.toUpperCase()} ${value/100}.`''','centerline history shorthand')

# Role switch UI in player popover.
s=once(s,'<div id="roomMemberList" class="roomMemberList"></div>\n    <div class="roomPopoverMeta">',
'''<div id="roomMemberList" class="roomMemberList"></div>\n    <div id="roomRoleSwitch">\n      <select id="roomRoleSwitchSelect" aria-label="Change role"><option value="seeker">Seeker</option><option value="hider">Hider</option></select>\n      <button id="changeRoomRoleBtn" type="button">Change role</button>\n      <div id="roomRoleSwitchStatus" class="small"></div>\n    </div>\n    <div class="roomPopoverMeta">''','role switch markup')
s=once(s,'.roomPopoverMeta{display:none!important}\n',
'''.roomPopoverMeta{display:none!important}\n  #roomRoleSwitch{display:grid;grid-template-columns:1fr 112px;gap:7px;margin-top:9px;padding-top:9px;border-top:1px solid #394350}\n  #roomRoleSwitch select,#roomRoleSwitch button{padding:7px 8px;min-height:34px}\n  #roomRoleSwitchStatus{grid-column:1/-1;min-height:0;margin-top:0}\n''','role switch styles')

# Forced relocation accordion hint shorter for consistent one-line height.
s=once(s,'<summary><span>Forced relocation</span><span class="settingsHint">Private randomized cadence + movement</span></summary>',
'''<summary><span>Forced relocation</span><span class="settingsHint">Timing + movement</span></summary>''','short relocation hint')

# New mission settings accordion before Sound, keeping Development/testing last.
mission_settings='''      <details class="settingsGroup" id="missionSettingsGroup">\n        <summary><span>Hider missions</span><span class="settingsHint">Timing + offers</span></summary>\n        <div class="settingsBody">\n          <div class="scheduleGrid">\n            <label>First offer (min)\n              <input id="missionFirstMinutes" type="number" min="1" step="1" value="10">\n            </label>\n            <label>Repeat min (min)\n              <input id="missionRepeatMinMinutes" type="number" min="1" step="1" value="10">\n            </label>\n            <label>Repeat max (min)\n              <input id="missionRepeatMaxMinutes" type="number" min="1" step="1" value="15">\n            </label>\n          </div>\n          <button class="primary" id="applyMissionSettingsBtn" style="margin-top:8px">Apply mission settings</button>\n          <div id="missionSettingsValidation" class="validation"></div>\n          <p class="small">Cross the Zone remains optional and completely private to the Hider UI. Repeat timing is randomized inside the configured range.</p>\n        </div>\n      </details>\n\n'''
s=once(s,'      <details class="settingsGroup">\n        <summary><span>Sound</span><span class="settingsHint">Volume + gameplay cues</span></summary>',
mission_settings+'      <details class="settingsGroup">\n        <summary><span>Sound</span><span class="settingsHint">Volume + gameplay cues</span></summary>','mission settings group')

# Changelog entry for this pass.
changelog='''      <div class="changeEntry">\n        <h4>v1.3.0 preview — Mission + role UI pass</h4>\n        <ul>\n          <li>Restored an always-visible Hider-only mission status card and added configurable mission timing.</li>\n          <li>Added in-room role switching while preserving the one-Hider rule.</li>\n          <li>Changed the Hider match subtitle to Hiding, Relocate, or Mission Active instead of question status.</li>\n          <li>Shortened Centerline display labels to Y 37 / X 17 and refreshed the tower visibility icon.</li>\n        </ul>\n      </div>\n'''
s=once(s,'    <div id="view-changelog" class="panelView">\n      <div class="panelHeader"><h2>Changelog</h2><button class="closePanel">Hide</button></div>\n\n',
'    <div id="view-changelog" class="panelView">\n      <div class="panelHeader"><h2>Changelog</h2><button class="closePanel">Hide</button></div>\n\n'+changelog,'changelog entry')

# Mission settings state sync/input helpers.
s=once(s,'function updateRelocationSettingsInputs(){\n  const ids={relocationFirstMinMinutes:relocationSettings.firstMin/60,relocationFirstMaxMinutes:relocationSettings.firstMax/60,relocationRepeatMinMinutes:relocationSettings.intervalMin/60,relocationRepeatMaxMinutes:relocationSettings.intervalMax/60,relocationWindowMinutes:relocationSettings.window/60,relocationMinDistance:relocationSettings.minDistance,relocationSkipBelow:relocationSettings.skipBelow};\n  for(const [id,value] of Object.entries(ids))syncSettingValue(id,value);\n}\n',
'''function updateRelocationSettingsInputs(){\n  const ids={relocationFirstMinMinutes:relocationSettings.firstMin/60,relocationFirstMaxMinutes:relocationSettings.firstMax/60,relocationRepeatMinMinutes:relocationSettings.intervalMin/60,relocationRepeatMaxMinutes:relocationSettings.intervalMax/60,relocationWindowMinutes:relocationSettings.window/60,relocationMinDistance:relocationSettings.minDistance,relocationSkipBelow:relocationSettings.skipBelow};\n  for(const [id,value] of Object.entries(ids))syncSettingValue(id,value);\n}\nfunction updateMissionSettingsInputs(){\n  const ids={missionFirstMinutes:missionSettings.firstAt/60,missionRepeatMinMinutes:missionSettings.minInterval/60,missionRepeatMaxMinutes:missionSettings.maxInterval/60};\n  for(const [id,value] of Object.entries(ids))syncSettingValue(id,value);\n}\n''','mission input sync helper')

# Room chrome: mission settings follows same host/Hider visibility model as relocation.
s=once(s,'const actions=document.getElementById("topRoomActions"),popover=document.getElementById("roomConnected"),count=document.getElementById("roomPlayerCount"),playersBtn=document.getElementById("roomPlayersBtn"),qTab=document.querySelector(\'.tabBtn[data-tab="questions"]\'),relocationSettingsGroup=document.getElementById("relocationSettingsGroup");',
'''const actions=document.getElementById("topRoomActions"),popover=document.getElementById("roomConnected"),count=document.getElementById("roomPlayerCount"),playersBtn=document.getElementById("roomPlayersBtn"),qTab=document.querySelector('.tabBtn[data-tab="questions"]'),relocationSettingsGroup=document.getElementById("relocationSettingsGroup"),missionSettingsGroup=document.getElementById("missionSettingsGroup");''','room chrome settings refs')
s=once(s,'  if(relocationSettingsGroup){\n    relocationSettingsGroup.style.display=!connected||isHider||isHost?"":"none";\n    relocationSettingsGroup.querySelectorAll("input,button").forEach(el=>el.disabled=connected&&!isHost);\n  }\n',
'''  if(relocationSettingsGroup){\n    relocationSettingsGroup.style.display=!connected||isHider||isHost?"":"none";\n    relocationSettingsGroup.querySelectorAll("input,button").forEach(el=>el.disabled=connected&&!isHost);\n  }\n  if(missionSettingsGroup){\n    missionSettingsGroup.style.display=!connected||isHider||isHost?"":"none";\n    missionSettingsGroup.querySelectorAll("input,button").forEach(el=>el.disabled=connected&&!isHost);\n  }\n''','mission settings visibility')

# Hider mission card should always exist for the Hider, but never for Seekers.
s=once(s,'  if(!roomModeConnected()||!isRoomHider()){section.style.display="none";return;}\n  if(!missionState.active&&!missionState.available){section.style.display="none";return;}\n  section.style.display="block";\n',
'''  if(!roomModeConnected()||!isRoomHider()){section.style.display="none";return;}\n  section.style.display="block";\n''','always show hider mission card')
s=once(s,'  const nextAt=Number(missionState.nextAt??missionSettings.firstAt),remaining=Math.max(0,nextAt-now);\n  headline.textContent=formatTime(remaining);progress.textContent="—";\n  status.textContent=missionState.lastResult?`Last: ${missionState.lastResult}`:"Waiting";\n  if(missionSchedulerError)message.textContent=`Mission scheduler error: ${missionSchedulerError}`;\n  else if(relocationState.active&&remaining<=.01)message.textContent="The next mission offer will wait until the current forced relocation is completed.";\n  else if(!window.BigWalkRooms?.hasHider?.())message.textContent="Waiting for a Hider before the next mission can become available.";\n  else message.textContent=`Next optional mission becomes available in ${formatTime(remaining)}. After a mission ends, the next offer is scheduled randomly 10–15 minutes later.`;\n',
'''  const nextAt=Number(missionState.nextAt??missionSettings.firstAt),remaining=Math.max(0,nextAt-now);\n  headline.textContent="WAITING";progress.textContent="Optional";\n  status.textContent=`Next offer · ${formatApproxDuration(remaining)}`;\n  if(missionSchedulerError)message.textContent=`Mission scheduler error: ${missionSchedulerError}`;\n  else if(relocationState.active&&remaining<=.01)message.textContent="The next mission offer will wait until your forced relocation is completed.";\n  else message.textContent=`Cross the Zone is optional. Repeat offers are scheduled randomly ${formatApproxDuration(missionSettings.minInterval)}–${formatApproxDuration(missionSettings.maxInterval)} apart.`;\n''','compact waiting mission state')

# Hider timer subtitle is about Hider gameplay only, not Seeker question state.
s=once(s,'  const status=document.getElementById("timerStatus"),topSub=document.getElementById("topTimerSub");\n  if(testingUnlockOverride){status.textContent="Testing override active — all questions unlocked.";topSub.textContent="Testing override";return;}\n  if(!matchRunning&&currentMatchSeconds()<.01){status.textContent="Start the match when everyone is ready.";topSub.textContent="Match not started";return;}\n  if(!matchRunning){status.textContent="Match paused.";topSub.textContent="Paused";return;}\n  status.textContent="Match running.";\n  if(hidingTimeRemaining()>.01)topSub.textContent="Hiding time";\n  else if(roomModeConnected()&&relocationState.active&&isRoomHider())topSub.textContent="Forced relocation active";\n  else if(roomModeConnected()&&missionState.active&&isRoomHider())topSub.textContent="Hider mission active";\n  else if(questionCooldownActive())topSub.textContent="Questions cooling down";\n  else topSub.textContent="Questions ready";\n',
'''  const status=document.getElementById("timerStatus"),topSub=document.getElementById("topTimerSub"),hiderView=isRoomHider();\n  if(testingUnlockOverride&&!hiderView){status.textContent="Testing override active — all questions unlocked.";topSub.textContent="Testing override";return;}\n  if(!matchRunning&&currentMatchSeconds()<.01){status.textContent="Start the match when everyone is ready.";topSub.textContent="Match not started";return;}\n  if(!matchRunning){status.textContent="Match paused.";topSub.textContent="Paused";return;}\n  status.textContent=testingUnlockOverride?"Testing override active — all questions unlocked.":"Match running.";\n  if(hiderView){\n    if(relocationState.active)topSub.textContent="Relocate";\n    else if(missionState.active)topSub.textContent="Mission Active";\n    else topSub.textContent="Hiding";\n    return;\n  }\n  if(hidingTimeRemaining()>.01)topSub.textContent="Hiding time";\n  else if(questionCooldownActive())topSub.textContent="Questions cooling down";\n  else topSub.textContent="Questions ready";\n''','role-aware top subtitle')

# Mission settings shared-state sync and initialization.
s=once(s,'updateScheduleInputs();updateQuestionCostInputs();updateRelocationSettingsInputs();renderMatchTimer();syncMatchControlButtons();',
'''updateScheduleInputs();updateQuestionCostInputs();updateRelocationSettingsInputs();updateMissionSettingsInputs();renderMatchTimer();syncMatchControlButtons();''','remote mission settings sync')
s=once(s,'populate();initializeQuestionCollapsibles();bindSettingDraftProtection();updateMarkerPanel();updateRulerPanel();updateGridInputRules();updateScheduleInputs();updateQuestionCostInputs();updateRelocationSettingsInputs();',
'''populate();initializeQuestionCollapsibles();bindSettingDraftProtection();updateMarkerPanel();updateRulerPanel();updateGridInputRules();updateScheduleInputs();updateQuestionCostInputs();updateRelocationSettingsInputs();updateMissionSettingsInputs();''','initial mission settings sync')

# Bridge guard against switching away from Hider during an active private movement objective.
s=once(s,'  setRoomSharedEditAuthority(){updateQuestionLocks();},\n  onRoomDisconnected(finalSeconds){',
'''  setRoomSharedEditAuthority(){updateQuestionLocks();},\n  canChangeRoomRole(nextRole){\n    if(roomRole()==="hider"&&nextRole!=="hider"&&(relocationState.active||missionState.active))return {ok:false,message:"Finish the active relocation or mission before switching away from Hider."};\n    return {ok:true};\n  },\n  onRoomDisconnected(finalSeconds){''','role switch bridge guard')

# Mission settings Apply handler before sound controls.
anchor='document.getElementById("testUnlockOverride").onchange=e=>{testingUnlockOverride=e.target.checked;renderMatchTimer();};\n'
handler='''document.getElementById("applyMissionSettingsBtn").onclick=()=>{\n  const v=document.getElementById("missionSettingsValidation");v.textContent="";\n  if(roomModeConnected()&&!window.BigWalkRooms?.isHost?.()){v.textContent="Only the room host can change mission settings.";return;}\n  const first=+document.getElementById("missionFirstMinutes").value,min=+document.getElementById("missionRepeatMinMinutes").value,max=+document.getElementById("missionRepeatMaxMinutes").value;\n  if(![first,min,max].every(Number.isFinite)||first<=0||min<=0||max<=0){v.textContent="Mission times must be positive numbers.";return;}\n  if(max<min){v.textContent="Repeat max cannot be lower than repeat min.";return;}\n  missionSettings={firstAt:first*60,minInterval:min*60,maxInterval:max*60};\n  if(!missionState.active&&!missionState.available)missionState={...missionState,nextAt:Number(missionState.index||0)===0?missionSettings.firstAt:currentMatchSeconds()+nextMissionDelay()};\n  clearSettingDraft(["missionFirstMinutes","missionRepeatMinMinutes","missionRepeatMaxMinutes"]);\n  updateMissionSettingsInputs();renderMatchTimer();notifyRoomGameStateChanged();\n  v.style.color="#9ef1c2";v.textContent="Mission settings applied.";setTimeout(()=>{v.textContent="";v.style.color="";},1500);\n};\n'''
s=once(s,anchor,handler+anchor,'mission settings apply handler')

# rooms.js: effective role supports safe host role switching with immutable base role.
r=once(r,'function roleLabel(role){ return role === "hider" ? "Hider" : "Seeker"; }\n',
'''function roleLabel(role){ return role === "hider" ? "Hider" : "Seeker"; }\nfunction effectiveMemberRole(member){\n  return member?.roleView === "hider" || member?.roleView === "seeker" ? member.roleView : member?.role;\n}\n''','effective role helper')
r=once(r,'function setBusy(value){\n  busy = value;\n  [ui.createBtn, ui.joinBtn, ui.leaveBtn].filter(Boolean).forEach(btn => btn.disabled = value);\n}\n',
'''function setBusy(value){\n  busy = value;\n  [ui.createBtn, ui.joinBtn, ui.leaveBtn, ui.changeRoleBtn].filter(Boolean).forEach(btn => btn.disabled = value);\n}\n''','busy change role')
r=once(r,'    role.className = `roomBadge ${m?.role === "hider" ? "hider" : "seeker"}`;\n    role.textContent = roleLabel(m?.role);',
'''    const effectiveRole=effectiveMemberRole(m);\n    role.className = `roomBadge ${effectiveRole === "hider" ? "hider" : "seeker"}`;\n    role.textContent = roleLabel(effectiveRole);''','member role badge')
r=once(r,'  ui.hostControlsNote.textContent = isHost()\n    ? "You control the shared match timer."\n    : "Only the room host can start, pause, or reset the shared match timer.";\n',
'''  if(ui.roleSwitchInput)ui.roleSwitchInput.value=roomRole;\n  ui.hostControlsNote.textContent = isHost()\n    ? "You control the shared match timer."\n    : "Only the room host can start, pause, or reset the shared match timer.";\n''','sync role switch select')
r=once(r,'  return Object.entries(roomData?.members || {}).find(([,m]) => m?.role === "hider") || null;\n',
'''  return Object.entries(roomData?.members || {}).find(([,m]) => effectiveMemberRole(m) === "hider") || null;\n''','effective hider entry')
r=once(r,'  return Object.entries(members).some(([uid, member]) => uid !== user?.uid && member?.role === "hider");\n',
'''  return Object.entries(members).some(([uid, member]) => uid !== user?.uid && effectiveMemberRole(member) === "hider");\n''','effective hider uniqueness')
r=once(r,'    roomRole = roomData?.members?.[user.uid]?.role || roomRole;\n',
'''    roomRole = effectiveMemberRole(roomData?.members?.[user.uid]) || roomRole;\n''','effective subscribed role')

# In-room role switch. Hosts use roleView so their membership never disappears; non-hosts can safely re-register their member to satisfy immutable role rules.
role_fn='''\nasync function changeRoomRole(){\n  if(busy||!isConnected())return;\n  const next=ui.roleSwitchInput?.value==="hider"?"hider":"seeker";\n  if(next===roomRole){if(ui.roleSwitchStatus)ui.roleSwitchStatus.textContent=`Already ${roleLabel(next)}.`;return;}\n  const guard=bridge()?.canChangeRoomRole?.(next);\n  if(guard&&guard.ok===false){if(ui.roleSwitchStatus)ui.roleSwitchStatus.textContent=guard.message||"Cannot change role right now.";return;}\n  setBusy(true);\n  try{\n    if(next==="hider"&&await roomHasOtherHider(roomCode))throw new Error("This room already has a Hider.");\n    const {dbMod}=firebase,memberRef=dbMod.ref(db,`rooms/${roomCode}/members/${user.uid}`);\n    if(isHost()){\n      await dbMod.update(memberRef,{roleView:next,lastSeen:dbMod.serverTimestamp()});\n    }else{\n      const name=safeName(displayName||roomData?.members?.[user.uid]?.name);\n      try{await dbMod.onDisconnect(memberRef).cancel();}catch{}\n      await dbMod.remove(memberRef);\n      await dbMod.set(memberRef,{name,role:next,joinedAt:dbMod.serverTimestamp(),lastSeen:dbMod.serverTimestamp()});\n      await dbMod.onDisconnect(memberRef).remove();\n    }\n    roomRole=next;saveSession();updateRoomUi();\n    if(ui.roleSwitchStatus){ui.roleSwitchStatus.style.color="#9ef1c2";ui.roleSwitchStatus.textContent=`Role changed to ${roleLabel(next)}.`;}\n  }catch(err){\n    console.warn("Role change failed",err);\n    if(ui.roleSwitchStatus){ui.roleSwitchStatus.style.color="#ffadad";ui.roleSwitchStatus.textContent=err?.message||"Could not change role.";}\n    if(ui.roleSwitchInput)ui.roleSwitchInput.value=roomRole;\n  }finally{setBusy(false);setTimeout(()=>{if(ui.roleSwitchStatus){ui.roleSwitchStatus.textContent="";ui.roleSwitchStatus.style.color="";}},1800);}\n}\n'''
r=once(r,'\nasync function claimHostIfMissing(oldHost){',role_fn+'\nasync function claimHostIfMissing(oldHost){','role change function')

# Bind role-switch controls.
r=once(r,'  ui.roomCodeTop = byId("roomTopStatus");\n',
'''  ui.roomCodeTop = byId("roomTopStatus");\n  ui.roleSwitchInput = byId("roomRoleSwitchSelect");\n  ui.changeRoleBtn = byId("changeRoomRoleBtn");\n  ui.roleSwitchStatus = byId("roomRoleSwitchStatus");\n''','role ui refs')
r=once(r,'  ui.copyBtn.addEventListener("click", copyRoomCode);\n',
'''  ui.copyBtn.addEventListener("click", copyRoomCode);\n  ui.changeRoleBtn?.addEventListener("click", changeRoomRole);\n''','role change binding')

# Export is not necessary for role switching, but build id must remain current.

# Ensure known privacy and ordering invariants.
if s.find('Hider missions')<0: raise SystemExit('mission settings missing')
if s.find('Development / testing') < s.find('Hider missions'): raise SystemExit('Development/testing must stay after mission settings')
if 'Horizontal centerline — Y 3700' in s or 'Vertical centerline — X 1700' in s: raise SystemExit('old centerline display labels remain')
if 'M12 3v18M8 21h8' in s: raise SystemExit('old tower icon remains')
if 'Questions ready' not in s: raise SystemExit('Seeker question subtitle wording unexpectedly removed globally')

idx.write_text(s,encoding='utf-8')
rooms.write_text(r,encoding='utf-8')
