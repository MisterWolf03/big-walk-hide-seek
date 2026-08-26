from pathlib import Path

p=Path('index.html')
s=p.read_text()

def replace_once(old,new,label):
    global s
    if old not in s:
        raise SystemExit(f'Missing patch target: {label}')
    s=s.replace(old,new,1)

css='''  #roomTopStatus{
    flex:0 0 auto;font-size:11px;font-weight:800;letter-spacing:.5px;color:#9da7b4;
    border:1px solid #394350;background:#171b21;border-radius:999px;padding:5px 8px
  }
  #roomTopStatus.connected{color:#baf6cf;border-color:#38654b;background:#17271e}
  .roomStatus{
    margin-bottom:10px;padding:8px 10px;border:1px solid #394350;border-radius:9px;
    background:#171b21;color:#cbd3dd;font-size:12px;line-height:1.4
  }
  .roomStatus.good{color:#baf6cf;border-color:#38654b;background:#17271e}
  .roomStatus.warning{color:#ffe391;border-color:#6d5b28;background:#292413}
  .roomStatus.error{color:#ffb5b5;border-color:#6d3438;background:#2b1719}
  .roomSetupNotice{display:none;margin-bottom:10px;padding:9px;border-radius:9px;border:1px solid #6d5b28;background:#292413;color:#ffe391;font-size:12px;line-height:1.45}
  .roomJoinCode{text-transform:uppercase;letter-spacing:2px;font-weight:800;text-align:center}
  .roomCodeHero{
    display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px;
    border:1px solid #435064;border-radius:10px;background:#151b22
  }
  .roomCodeValue{font-size:26px;font-weight:900;letter-spacing:4px;color:#ffe58b}
  .roomCodeHero button{width:auto;padding:7px 10px}
  .roomMemberList{display:grid;gap:7px;margin-top:9px}
  .roomMember{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:8px 9px;border:1px solid #394350;border-radius:8px;background:#171b21}
  .roomMemberName{display:flex;align-items:center;justify-content:space-between;gap:8px;width:100%;min-width:0}
  .roomMemberName b{font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .roomMemberBadges{display:flex;gap:5px;flex-wrap:wrap;justify-content:flex-end}
  .roomBadge{font-size:9px;font-weight:850;letter-spacing:.5px;padding:3px 5px;border-radius:999px;border:1px solid #475464;color:#d9e0e8;background:#202731}
  .roomBadge.seeker{border-color:#4e6480;color:#cbe3ff;background:#172535}
  .roomBadge.hider{border-color:#6e4f7d;color:#efceff;background:#281b30}
  .roomBadge.host{border-color:#79642d;color:#ffe391;background:#2b2514}
'''
replace_once('  @media(max-width:900px){', css+'\n  @media(max-width:900px){', 'room CSS insertion')

replace_once('''  <div id="tabs">
    <button class="tabBtn active" data-tab="game">Game</button>''','''  <div id="tabs">
    <button class="tabBtn" data-tab="room">Room</button>
    <button class="tabBtn active" data-tab="game">Game</button>''','Room tab')
replace_once('  <div id="topTimer">','  <div id="roomTopStatus">Offline</div>\n  <div id="topTimer">','room top status')

room_panel='''    <div id="view-room" class="panelView">
      <div class="panelHeader"><h2>Room <span class="small">v1.2.0 preview</span></h2><button class="closePanel">Hide</button></div>
      <div id="roomStatus" class="roomStatus">Initializing room service…</div>
      <div id="roomSetupNotice" class="roomSetupNotice">Rooms need a Firebase Realtime Database project before they can connect across devices. Follow <b>ROOMS_SETUP.md</b> in the repo, then add the Firebase web config to <b>firebase-config.js</b>.</div>

      <div id="roomDisconnected">
        <section>
          <h3>Your room identity</h3>
          <label>Display name</label>
          <input id="roomPlayerName" type="text" maxlength="28" autocomplete="nickname" placeholder="e.g. Xypher">
          <label>Role</label>
          <select id="roomRoleSelect">
            <option value="seeker">Seeker</option>
            <option value="hider">Hider</option>
          </select>
          <p class="small">Roles only control shared match tools in this first room build. Hider position is not uploaded or revealed.</p>
        </section>
        <section>
          <h3>Create a room</h3>
          <button id="createRoomBtn" class="primary">Create room</button>
          <p class="small">Creates a six-character room code and makes you the room host.</p>
        </section>
        <section>
          <h3>Join a room</h3>
          <input id="roomJoinCode" class="roomJoinCode" type="text" maxlength="6" autocomplete="off" placeholder="ABC123" aria-label="Room code">
          <button id="joinRoomBtn" style="margin-top:8px">Join room</button>
        </section>
      </div>

      <div id="roomConnected" style="display:none">
        <section>
          <h3>Current room</h3>
          <div class="roomCodeHero">
            <div id="currentRoomCode" class="roomCodeValue">—</div>
            <button id="copyRoomCodeBtn">Copy code</button>
          </div>
          <div class="metric" style="margin-top:8px"><b>Your role</b><span id="currentRoomRole">—</span></div>
          <div class="metric"><b>Host</b><span id="currentRoomHost">—</span></div>
          <p id="roomHostControlsNote" class="small"></p>
        </section>
        <section>
          <h3>Players</h3>
          <div id="roomMemberList" class="roomMemberList"></div>
        </section>
        <section>
          <h3>Shared in this preview</h3>
          <p class="small">Match timer, pause/reset state, question unlock schedule, global question cooldown, question history, and search-area constraints sync across the room. Markers and live player position stay local.</p>
          <button id="leaveRoomBtn" class="danger">Leave room</button>
        </section>
      </div>
    </div>

'''
replace_once('''  <div id="panel">

    <div id="view-game" class="panelView active">''','''  <div id="panel">

'''+room_panel+'''    <div id="view-game" class="panelView active">''','room panel')

bridge='''let roomApplyingRemoteState=false;
function roomModeConnected(){return !!window.BigWalkRooms?.isConnected?.();}
function roomCanEditSharedGame(){return !roomModeConnected() || !!window.BigWalkRooms?.canEditSharedGame?.();}
function notifyRoomGameStateChanged(){
  if(roomApplyingRemoteState||!roomModeConnected())return;
  Promise.resolve(window.BigWalkRooms?.pushGameState?.()).catch(err=>console.warn("Room state sync failed",err));
}
function syncMatchControlButtons(){
  const connected=roomModeConnected();
  const canControl=!connected || !!window.BigWalkRooms?.canControlMatch?.();
  const start=document.getElementById("startMatchBtn"),pause=document.getElementById("pauseMatchBtn"),reset=document.getElementById("resetMatchBtn");
  const elapsed=currentMatchSeconds();
  if(matchRunning){
    start.textContent="Running";start.disabled=true;pause.disabled=!canControl;
  }else if(elapsed>0.01){
    start.textContent="Resume";start.disabled=!canControl;pause.disabled=true;
  }else{
    start.textContent="Start match";start.disabled=!canControl;pause.disabled=true;
  }
  reset.disabled=connected&&!canControl;
}
window.BigWalkRoomBridge={
  getSharedGameState(){
    return {constraints:JSON.parse(JSON.stringify(constraints||[])),historyText:[...(historyText||[])],questionCooldownUntil:Number(questionCooldownUntil||0),unlockTimes:{...unlockTimes},questionCooldownSeconds:Number(questionCooldownSeconds||300)};
  },
  applySharedRoomState(state){
    roomApplyingRemoteState=true;
    try{
      const game=state?.game||{};
      constraints=Array.isArray(game.constraints)?JSON.parse(JSON.stringify(game.constraints)):[];
      historyText=Array.isArray(game.historyText)?[...game.historyText]:[];
      questionCooldownUntil=Number(game.questionCooldownUntil||0);
      if(game.unlockTimes && typeof game.unlockTimes==="object"){
        unlockTimes={grid:Number(game.unlockTimes.grid??unlockTimes.grid),nearest:Number(game.unlockTimes.nearest??unlockTimes.nearest),towerRadius:Number(game.unlockTimes.towerRadius??unlockTimes.towerRadius),landmark:Number(game.unlockTimes.landmark??unlockTimes.landmark),marker:Number(game.unlockTimes.marker??unlockTimes.marker)};
      }
      if(Number.isFinite(Number(game.questionCooldownSeconds))&&Number(game.questionCooldownSeconds)>0)questionCooldownSeconds=Number(game.questionCooldownSeconds);
      const match=state?.match;
      if(match){matchRunning=!!match.running;matchElapsedMs=Math.max(0,Number(match.elapsedMs||0));matchLastTick=null;}
      updateScheduleInputs();renderMatchTimer();syncMatchControlButtons();
      if(appInitialized)draw();
    }finally{roomApplyingRemoteState=false;}
  },
  resetSharedGameForRoom(){
    roomApplyingRemoteState=true;
    try{
      matchRunning=false;matchElapsedMs=0;matchLastTick=null;questionCooldownUntil=0;
      constraints=[];historyText=[];playerMarkers=[];activeMarkerId=liveMarker?"live":null;nextMarkerId=1;rulerA=null;rulerB=null;
      ["splitValidation","radarValidation","landmarkQuestionValidation","markerQuestionValidation"].forEach(id=>document.getElementById(id).textContent="");
      updateMarkerPanel();updateRulerPanel();renderMatchTimer();syncMatchControlButtons();
      if(appInitialized)draw();
      return this.getSharedGameState();
    }finally{roomApplyingRemoteState=false;}
  },
  setRoomControlAuthority(){syncMatchControlButtons();},
  setRoomSharedEditAuthority(){updateQuestionLocks();},
  onRoomDisconnected(finalSeconds){
    if(Number.isFinite(Number(finalSeconds)))matchElapsedMs=Math.max(0,Number(finalSeconds)*1000);
    matchRunning=false;matchLastTick=null;renderMatchTimer();syncMatchControlButtons();
  }
};

function currentMatchSeconds(){
  if(roomModeConnected()){
    const shared=Number(window.BigWalkRooms?.getMatchSeconds?.());
    if(Number.isFinite(shared))return Math.max(0,shared);
  }
  return matchElapsedMs/1000;
}'''
replace_once('function currentMatchSeconds(){return matchElapsedMs/1000;}',bridge,'room bridge/currentMatchSeconds')

replace_once('''  const cooldown=questionCooldownActive();
  const locked=!unlocked || cooldown;''','''  const cooldown=questionCooldownActive();
  const roomReadOnly=roomModeConnected()&&!roomCanEditSharedGame();
  const locked=!unlocked || cooldown || roomReadOnly;''','question room read-only')
replace_once('''  }else if(cooldown){
    notice.textContent=`Global question cooldown · ${formatTime(questionCooldownRemaining())} remaining.`;
  }''','''  }else if(cooldown){
    notice.textContent=`Global question cooldown · ${formatTime(questionCooldownRemaining())} remaining.`;
  }else if(roomReadOnly){
    notice.textContent="Shared room: only seekers (or the host) can submit questions.";
  }''','question room notice')

replace_once('''function tickMatchTimer(){
  if(!matchRunning)return;''','''function tickMatchTimer(){
  if(roomModeConnected()){renderMatchTimer();return;}
  if(!matchRunning)return;''','shared timer tick')
replace_once('''function addConstraint(c,text){
  constraints.push(c);''','''function addConstraint(c,text){
  if(!roomCanEditSharedGame())return;
  constraints.push(c);''','shared question guard')
replace_once('''  draw();
  renderMatchTimer();
}
function updateGridInputRules()''','''  draw();
  renderMatchTimer();
  notifyRoomGameStateChanged();
}
function updateGridInputRules()''','question state publish')

old_controls='''document.getElementById("startMatchBtn").onclick=()=>{
  if(matchRunning)return;
  matchRunning=true;matchLastTick=performance.now();
  document.getElementById("startMatchBtn").textContent="Running";
  document.getElementById("startMatchBtn").disabled=true;
  document.getElementById("pauseMatchBtn").disabled=false;renderMatchTimer();
};
document.getElementById("pauseMatchBtn").onclick=()=>{
  if(!matchRunning)return;
  tickMatchTimer();matchRunning=false;matchLastTick=null;
  document.getElementById("startMatchBtn").textContent="Resume";
  document.getElementById("startMatchBtn").disabled=false;
  document.getElementById("pauseMatchBtn").disabled=true;renderMatchTimer();
};
document.getElementById("resetMatchBtn").onclick=()=>{
  if(confirm("Reset the match timer and clear all game state?"))resetMatchState();
};'''
new_controls='''document.getElementById("startMatchBtn").onclick=()=>{
  if(roomModeConnected()){Promise.resolve(window.BigWalkRooms.startMatch()).catch(console.error);return;}
  if(matchRunning)return;
  matchRunning=true;matchLastTick=performance.now();
  document.getElementById("startMatchBtn").textContent="Running";
  document.getElementById("startMatchBtn").disabled=true;
  document.getElementById("pauseMatchBtn").disabled=false;renderMatchTimer();
};
document.getElementById("pauseMatchBtn").onclick=()=>{
  if(roomModeConnected()){Promise.resolve(window.BigWalkRooms.pauseMatch()).catch(console.error);return;}
  if(!matchRunning)return;
  tickMatchTimer();matchRunning=false;matchLastTick=null;
  document.getElementById("startMatchBtn").textContent="Resume";
  document.getElementById("startMatchBtn").disabled=false;
  document.getElementById("pauseMatchBtn").disabled=true;renderMatchTimer();
};
document.getElementById("resetMatchBtn").onclick=()=>{
  if(!confirm("Reset the match timer and clear all game state?"))return;
  if(roomModeConnected())Promise.resolve(window.BigWalkRooms.resetMatch()).catch(console.error);
  else resetMatchState();
};'''
replace_once(old_controls,new_controls,'shared timer controls')

replace_once('''document.getElementById("undoBtn").onclick=()=>{
  if(!constraints.length)return;''','''document.getElementById("undoBtn").onclick=()=>{
  if(!roomCanEditSharedGame()||!constraints.length)return;''','undo room guard')
replace_once('''  draw();
  renderMatchTimer();
};
document.getElementById("clearQuestionsBtn").onclick=()=>{''','''  draw();
  renderMatchTimer();
  notifyRoomGameStateChanged();
};
document.getElementById("clearQuestionsBtn").onclick=()=>{''','undo room publish')
replace_once('''document.getElementById("clearQuestionsBtn").onclick=()=>{
  constraints=[];''','''document.getElementById("clearQuestionsBtn").onclick=()=>{
  if(!roomCanEditSharedGame())return;
  constraints=[];''','clear room guard')
replace_once('''  draw();
  renderMatchTimer();
};

panModeBtn.onclick''','''  draw();
  renderMatchTimer();
  notifyRoomGameStateChanged();
};

panModeBtn.onclick''','clear room publish')

replace_once('''document.getElementById("applyScheduleBtn").onclick=()=>{
  const ids=''' , '''document.getElementById("applyScheduleBtn").onclick=()=>{
  if(!roomCanEditSharedGame()){document.getElementById("scheduleValidation").textContent="Shared room: only seekers (or the host) can change match timing.";return;}
  const ids=''' , 'schedule room guard')
replace_once('''  updateScheduleInputs();renderMatchTimer();
  v.style.color="#9ef1c2";v.textContent="Timing settings applied.";''','''  updateScheduleInputs();renderMatchTimer();
  notifyRoomGameStateChanged();
  v.style.color="#9ef1c2";v.textContent="Timing settings applied.";''','schedule room publish')

replace_once('''</script>
</body>''','''</script>
<script src="firebase-config.js"></script>
<script type="module" src="rooms.js"></script>
</body>''','room scripts')

p.write_text(s)
