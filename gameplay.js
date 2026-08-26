const RELOCATION_KEY_PREFIX = "bigwalk.room.relocation.v1";
let gameplayTimer = null;
let relocationWriteBusy = false;
let messageTimer = null;

const ui = {};
const byId = id => document.getElementById(id);
const rooms = () => window.BigWalkRooms || null;
const bridge = () => window.BigWalkRoomBridge || null;

function formatSeconds(totalSeconds){
  totalSeconds = Math.max(0, Math.floor(Number(totalSeconds) || 0));
  const m = Math.floor(totalSeconds / 60), s = totalSeconds % 60;
  return `${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`;
}
function roomData(){ return rooms()?.getRoomData?.() || null; }
function gameplay(){ return rooms()?.getGameplayState?.() || null; }
function roomCode(){ return rooms()?.getRoomCode?.() || null; }
function myRole(){ return rooms()?.getRole?.() || null; }
function myUid(){ return rooms()?.getUserUid?.() || null; }
function connected(){ return !!rooms()?.isConnected?.(); }

function sortedHiders(){
  const entries = Object.entries(roomData()?.members || {}).filter(([,m])=>m?.role === "hider");
  entries.sort((a,b)=>{
    const aj = Number(a[1]?.joinedAt || Number.MAX_SAFE_INTEGER);
    const bj = Number(b[1]?.joinedAt || Number.MAX_SAFE_INTEGER);
    return aj - bj || a[0].localeCompare(b[0]);
  });
  return entries;
}
function hiderEntry(){ return sortedHiders()[0] || null; }
function completedCycle(){
  const h = hiderEntry(), gp = gameplay();
  if(!h || !gp) return 0;
  const hgp = h[1]?.gameplay || {};
  if(Number(hgp.relocationGeneration || 0) !== Number(gp.generation || 1)) return 0;
  return Math.max(0, Math.floor(Number(hgp.relocationCompletedCycle || 0)));
}
function relocationInfo(){
  const gp = gameplay();
  const sec = Number(rooms()?.getMatchSeconds?.() || 0);
  if(!gp) return {cycle:0,startAt:null,nextAt:Infinity};
  const first = Number(gp.settings?.firstRelocationSeconds || 1500);
  const every = Number(gp.settings?.relocationIntervalSeconds || 1200);
  if(sec < first) return {cycle:0,startAt:null,nextAt:first};
  const cycle = 1 + Math.floor((sec-first)/every);
  const startAt = first + (cycle-1)*every;
  return {cycle,startAt,nextAt:startAt+every};
}

function relocationKey(){
  const code = roomCode();
  return code ? `${RELOCATION_KEY_PREFIX}:${code}` : null;
}
function loadLocalRelocation(){
  const key = relocationKey();
  if(!key) return null;
  try{return JSON.parse(localStorage.getItem(key)||"null");}catch{return null;}
}
function saveLocalRelocation(value){
  const key = relocationKey();
  if(!key)return;
  if(value==null)localStorage.removeItem(key);
  else localStorage.setItem(key,JSON.stringify(value));
}

function showMessage(text,kind=""){
  if(!ui.message)return;
  clearTimeout(messageTimer);
  ui.message.textContent=text||"";
  ui.message.className=`roomGameplayMessage ${kind}`.trim();
  if(text)messageTimer=setTimeout(()=>{if(ui.message)ui.message.textContent="";},3500);
}

function injectUi(){
  if(byId("roomGameplayOverview"))return;
  const style=document.createElement("style");
  style.textContent=`
    .roomGameplayHero{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px}
    .roomGameplayStat{padding:10px;border:1px solid #394350;border-radius:9px;background:#171b21;text-align:center}
    .roomGameplayStat b{display:block;font-size:22px;color:#ffe58b;margin-bottom:2px}
    .roomGameplayStat span{font-size:10px;color:#aab3c0;text-transform:uppercase;letter-spacing:.5px}
    .roomGameplayMessage{min-height:16px;font-size:11px;margin-top:7px;color:#cbd3dd}
    .roomGameplayMessage.warning{color:#ffe391}.roomGameplayMessage.error{color:#ffb5b5}.roomGameplayMessage.good{color:#baf6cf}
    .questionCostBadge{display:none;margin-left:7px;padding:2px 6px;border:1px solid #6d5b28;border-radius:999px;background:#292413;color:#ffe391;font-size:10px;font-weight:800;vertical-align:1px}
    .relocationProgress{height:8px;border-radius:999px;background:#11161d;border:1px solid #394350;overflow:hidden;margin-top:8px}
    .relocationProgress>div{height:100%;background:#f2c94c;width:0%}
  `;
  document.head.appendChild(style);

  const overview=document.createElement("section");
  overview.id="roomGameplayOverview";
  overview.style.display="none";
  overview.innerHTML=`
    <h3>Room gameplay</h3>
    <div id="roomSeekerGameplay" style="display:none">
      <div class="roomGameplayHero">
        <div class="roomGameplayStat"><b id="seekerPointsValue">0</b><span>Available points</span></div>
        <div class="roomGameplayStat"><b id="seekerIncomeValue">+1/min</b><span>Income</span></div>
      </div>
      <div class="metric"><b>Points earned</b><span id="seekerPointsEarned">0</span></div>
      <div class="metric"><b>Points spent</b><span id="seekerPointsSpent">0</span></div>
      <div class="metric"><b>Relocation</b><span id="seekerRelocationStatus">—</span></div>
    </div>
    <div id="roomHiderGameplay" style="display:none">
      <div class="metric"><b>Relocation</b><span id="hiderRelocationStatus">—</span></div>
      <div id="hiderRelocationDetails" class="small" style="margin-top:8px"></div>
      <div class="relocationProgress"><div id="hiderRelocationProgressBar"></div></div>
    </div>
    <div id="roomGameplayMessage" class="roomGameplayMessage"></div>`;
  byId("matchTimer")?.closest("section")?.insertAdjacentElement("afterend",overview);

  const settings=document.createElement("section");
  settings.id="roomGameplaySettingsSection";
  settings.style.display="none";
  settings.innerHTML=`
    <h3>Room gameplay</h3>
    <div class="scheduleGrid">
      <label>Seeker points / min<input id="roomPointsPerMinute" type="number" min="0.1" max="10" step="0.1" value="1"></label>
      <label>First relocation (min)<input id="roomFirstRelocationMinutes" type="number" min="1" max="180" step="1" value="25"></label>
      <label>Repeat relocation every (min)<input id="roomRelocationIntervalMinutes" type="number" min="1" max="180" step="1" value="20"></label>
      <label>Minimum displacement (units)<input id="roomRelocationDistance" type="number" min="50" max="1000" step="25" value="250"></label>
    </div>
    <button id="applyRoomGameplaySettings" class="primary" style="margin-top:8px">Apply gameplay settings</button>
    <div id="roomGameplaySettingsStatus" class="validation"></div>
    <p class="small">Relocation measures displacement from the hider's starting point, not total distance traveled. The hider must remain inside the connected legal search region. If that region is too small, the target scales down automatically and can be waived when meaningful movement is impossible.</p>`;
  const devSection=byId("testUnlockOverride")?.closest("section");
  if(devSection)devSection.insertAdjacentElement("beforebegin",settings);
  else byId("view-settings")?.appendChild(settings);

  ui.overview=overview;
  ui.seekerPanel=byId("roomSeekerGameplay");
  ui.hiderPanel=byId("roomHiderGameplay");
  ui.points=byId("seekerPointsValue");
  ui.income=byId("seekerIncomeValue");
  ui.earned=byId("seekerPointsEarned");
  ui.spent=byId("seekerPointsSpent");
  ui.seekerRelocation=byId("seekerRelocationStatus");
  ui.hiderRelocation=byId("hiderRelocationStatus");
  ui.hiderDetails=byId("hiderRelocationDetails");
  ui.progress=byId("hiderRelocationProgressBar");
  ui.message=byId("roomGameplayMessage");
  ui.settingsSection=settings;
  ui.pointsInput=byId("roomPointsPerMinute");
  ui.firstInput=byId("roomFirstRelocationMinutes");
  ui.intervalInput=byId("roomRelocationIntervalMinutes");
  ui.distanceInput=byId("roomRelocationDistance");
  ui.applyBtn=byId("applyRoomGameplaySettings");
  ui.settingsStatus=byId("roomGameplaySettingsStatus");
  ui.applyBtn?.addEventListener("click",applySettings);

  for(const [sectionId,badgeId] of [
    ["gridQuestionSection","costGrid"],["nearestQuestionSection","costNearest"],
    ["towerRadiusQuestionSection","costTowerRadius"],["landmarkQuestionSection","costLandmark"],
    ["markerQuestionSection","costMarker"]]){
    const h3=byId(sectionId)?.querySelector("h3");
    if(!h3||byId(badgeId))continue;
    const badge=document.createElement("span");badge.id=badgeId;badge.className="questionCostBadge";h3.appendChild(badge);
  }
  ["radarRadius","landmarkQuestionType","landmarkRadius","markerQuestionType","markerRadius"].forEach(id=>{
    byId(id)?.addEventListener("input",updateCostBadges);
    byId(id)?.addEventListener("change",updateCostBadges);
  });
}

function setBadge(id,constraint){
  const el=byId(id);if(!el)return;
  const show=connected()&&myRole()==="seeker";
  el.style.display=show?"inline-flex":"none";
  el.textContent=`${rooms()?.getQuestionCost?.(constraint)||0} pts`;
}
function updateCostBadges(){
  setBadge("costGrid",{type:"split"});
  setBadge("costNearest",{type:"nearest"});
  setBadge("costTowerRadius",{type:"radar",radius:Number(byId("radarRadius")?.value||500)});
  setBadge("costLandmark",byId("landmarkQuestionType")?.value==="radius"
    ?{type:"landmarkRadar",radius:Number(byId("landmarkRadius")?.value||300)}:{type:"nearestLandmark"});
  setBadge("costMarker",byId("markerQuestionType")?.value==="direction"
    ?{type:"markerDirection"}:{type:"markerRadar",radius:Number(byId("markerRadius")?.value||500)});
}

async function applySettings(){
  if(!connected()||!rooms()?.isHost?.())return;
  const settings={
    pointsPerMinute:Number(ui.pointsInput.value),
    firstRelocationSeconds:Number(ui.firstInput.value)*60,
    relocationIntervalSeconds:Number(ui.intervalInput.value)*60,
    relocationDistance:Number(ui.distanceInput.value),
  };
  ui.settingsStatus.textContent="";
  if(!Number.isFinite(settings.pointsPerMinute)||settings.pointsPerMinute<0.1||
     !Number.isFinite(settings.firstRelocationSeconds)||settings.firstRelocationSeconds<60||
     !Number.isFinite(settings.relocationIntervalSeconds)||settings.relocationIntervalSeconds<60||
     !Number.isFinite(settings.relocationDistance)||settings.relocationDistance<50){
    ui.settingsStatus.textContent="Use at least 0.1 point/min, 1 minute for relocation timers, and 50 units displacement.";return;
  }
  try{
    await rooms().applyGameplaySettings(settings);
    ui.settingsStatus.style.color="#9ef1c2";ui.settingsStatus.textContent="Gameplay settings applied.";
    setTimeout(()=>{if(ui.settingsStatus){ui.settingsStatus.textContent="";ui.settingsStatus.style.color="";}},1500);
  }catch(err){
    ui.settingsStatus.textContent=err?.message||"Could not apply gameplay settings.";
  }
}

function updateSettingsUi(){
  if(!ui.settingsSection)return;
  ui.settingsSection.style.display=connected()?"block":"none";
  const gp=gameplay();if(!connected()||!gp)return;
  const s=gp.settings||{};
  if(document.activeElement!==ui.pointsInput)ui.pointsInput.value=s.pointsPerMinute;
  if(document.activeElement!==ui.firstInput)ui.firstInput.value=Number(s.firstRelocationSeconds||0)/60;
  if(document.activeElement!==ui.intervalInput)ui.intervalInput.value=Number(s.relocationIntervalSeconds||0)/60;
  if(document.activeElement!==ui.distanceInput)ui.distanceInput.value=s.relocationDistance;
  const can=!!rooms()?.isHost?.();
  [ui.pointsInput,ui.firstInput,ui.intervalInput,ui.distanceInput,ui.applyBtn].forEach(el=>{if(el)el.disabled=!can;});
  if(!can)ui.settingsStatus.textContent="Only the room host can change gameplay settings.";
  else if(ui.settingsStatus.textContent==="Only the room host can change gameplay settings.")ui.settingsStatus.textContent="";
}

function movementSegmentAllowed(a,b){
  if(!a||!b||typeof bridge()?.isPointAllowed!=="function")return true;
  const d=Math.hypot(Number(b.x)-Number(a.x),Number(b.y)-Number(a.y));
  const steps=Math.max(1,Math.ceil(d/20));
  for(let i=1;i<=steps;i++){
    const t=i/steps,x=Number(a.x)+(Number(b.x)-Number(a.x))*t,y=Number(a.y)+(Number(b.y)-Number(a.y))*t;
    if(!bridge().isPointAllowed(x,y))return false;
  }
  return true;
}

async function completeRelocation(cycle,result){
  if(relocationWriteBusy)return;
  relocationWriteBusy=true;
  try{
    await rooms().completeRelocation(cycle,result);
    saveLocalRelocation(null);
    showMessage(result==="waived-small-area"?"Relocation waived — remaining legal area is too small for meaningful movement.":"Relocation complete!","good");
  }catch(err){showMessage("Could not sync relocation completion. Keep the room open and try again.","error");}
  finally{relocationWriteBusy=false;}
}

async function handleRelocation(){
  if(!connected()||myRole()!=="hider"||relocationWriteBusy||!rooms()?.isRelocationActive?.())return;
  const h=hiderEntry();if(!h||h[0]!==myUid())return;
  if(!roomData()?.state?.match?.running)return;
  const info=relocationInfo(),gp=gameplay();
  const raw=bridge()?.getPrivatePlayerPosition?.();
  if(!raw||!Number.isFinite(Number(raw.x))||!Number.isFinite(Number(raw.y)))return;
  const pos={x:Number(raw.x),y:Number(raw.y)};
  const legal=typeof bridge()?.isPointAllowed==="function"?!!bridge().isPointAllowed(pos.x,pos.y):true;
  let local=loadLocalRelocation();
  if(!local||local.generation!==gp.generation||local.cycle!==info.cycle){
    if(!legal){saveLocalRelocation({generation:gp.generation,cycle:info.cycle,waitingForLegalPosition:true});return;}
    const configured=Number(gp.settings?.relocationDistance||250);
    const estimate=bridge()?.estimateRelocationTarget?.(pos.x,pos.y,configured)||{targetDistance:configured,maxDistance:configured,adjusted:false,skipped:false};
    if(estimate.skipped){await completeRelocation(info.cycle,"waived-small-area");return;}
    local={generation:gp.generation,cycle:info.cycle,start:{...pos},lastPosition:{...pos},targetDistance:Number(estimate.targetDistance||configured),maxDistance:Number(estimate.maxDistance||configured),adjusted:!!estimate.adjusted,waitingForLegalPosition:false};
    saveLocalRelocation(local);showMessage(`Relocation started: move ${Math.round(local.targetDistance)} units from your starting point.`,"warning");return;
  }
  if(local.waitingForLegalPosition){
    if(!legal)return;
    const configured=Number(gp.settings?.relocationDistance||250);
    const estimate=bridge()?.estimateRelocationTarget?.(pos.x,pos.y,configured)||{targetDistance:configured,maxDistance:configured,adjusted:false,skipped:false};
    if(estimate.skipped){await completeRelocation(info.cycle,"waived-small-area");return;}
    local={generation:gp.generation,cycle:info.cycle,start:{...pos},lastPosition:{...pos},targetDistance:Number(estimate.targetDistance||configured),maxDistance:Number(estimate.maxDistance||configured),adjusted:!!estimate.adjusted,waitingForLegalPosition:false};
    saveLocalRelocation(local);showMessage("Relocation tracking restarted from your current valid position.","warning");return;
  }
  if(!legal||!movementSegmentAllowed(local.lastPosition,pos)){
    local.waitingForLegalPosition=true;local.lastPosition={...pos};saveLocalRelocation(local);
    showMessage("You left the valid search area. Return to a valid point; relocation will restart there.","error");return;
  }
  local.lastPosition={...pos};saveLocalRelocation(local);
  const displacement=Math.hypot(pos.x-local.start.x,pos.y-local.start.y);
  if(displacement+0.5>=Number(local.targetDistance||0))await completeRelocation(info.cycle,"completed");
}

function updateUi(){
  if(!ui.overview)return;
  const isConnected=connected(),role=myRole(),gp=gameplay(),info=relocationInfo(),h=hiderEntry(),active=!!rooms()?.isRelocationActive?.();
  ui.overview.style.display=isConnected?"block":"none";
  updateCostBadges();updateSettingsUi();
  if(!isConnected||!gp)return;
  ui.seekerPanel.style.display=role==="seeker"?"block":"none";
  ui.hiderPanel.style.display=role==="hider"?"block":"none";
  if(role==="seeker"){
    ui.points.textContent=String(Math.floor(rooms()?.getAvailableSeekerPoints?.()||0));
    ui.income.textContent=`+${gp.settings.pointsPerMinute}/min`;
    const earned=Math.max(0,Math.floor((Number(rooms()?.getMatchSeconds?.()||0)/60)*Number(gp.settings.pointsPerMinute||1)+1e-9));
    ui.earned.textContent=String(earned);ui.spent.textContent=String(Math.floor(Number(gp.seekerPointsSpent||0)));
    if(!h)ui.seekerRelocation.textContent="Waiting for hider";
    else if(active)ui.seekerRelocation.textContent="IN PROGRESS — questions locked";
    else if(info.cycle===0)ui.seekerRelocation.textContent=`In ${formatSeconds(info.nextAt-Number(rooms()?.getMatchSeconds?.()||0))}`;
    else ui.seekerRelocation.textContent=`Complete · next in ${formatSeconds(info.nextAt-Number(rooms()?.getMatchSeconds?.()||0))}`;
  }
  if(role==="hider"){
    const local=loadLocalRelocation();
    if(!h||h[0]!==myUid()){ui.hiderRelocation.textContent="Hider slot conflict";ui.hiderDetails.textContent="This room already has a hider.";ui.progress.style.width="0%";}
    else if(!active){ui.hiderRelocation.textContent=info.cycle===0?`Next in ${formatSeconds(info.nextAt-Number(rooms()?.getMatchSeconds?.()||0))}`:`Complete · next in ${formatSeconds(info.nextAt-Number(rooms()?.getMatchSeconds?.()||0))}`;ui.hiderDetails.textContent="When relocation starts, your live tracker privately records your starting point. Coordinates are never uploaded to the room.";ui.progress.style.width="0%";}
    else if(!local||local.generation!==gp.generation||local.cycle!==info.cycle){ui.hiderRelocation.textContent="RELOCATE NOW";ui.hiderDetails.textContent="Connect live location if needed. Your starting point will be recorded privately as soon as a valid position is available.";ui.progress.style.width="0%";}
    else if(local.waitingForLegalPosition){ui.hiderRelocation.textContent="Return to valid search area";ui.hiderDetails.textContent="Relocation tracking will restart from your next valid position.";ui.progress.style.width="0%";}
    else{
      const pos=bridge()?.getPrivatePlayerPosition?.();
      const d=pos&&local.start?Math.hypot(Number(pos.x)-local.start.x,Number(pos.y)-local.start.y):0,target=Number(local.targetDistance||gp.settings.relocationDistance),pct=target>0?Math.min(100,Math.max(0,d/target*100)):0;
      ui.hiderRelocation.textContent=`RELOCATE · ${Math.round(d)} / ${Math.round(target)} units`;
      ui.hiderDetails.textContent=local.adjusted?`Search area is tight, so the ${Math.round(gp.settings.relocationDistance)}-unit target was reduced to ${Math.round(target)}. Stay inside the valid search area.`:`Move at least ${Math.round(target)} units from where this relocation started. Total path length does not count — only displacement. Stay inside the valid search area.`;
      ui.progress.style.width=`${pct}%`;
    }
  }
  void handleRelocation();
}

window.BigWalkGameplay={showMessage,refresh:updateUi};

function init(){
  injectUi();
  clearInterval(gameplayTimer);gameplayTimer=setInterval(updateUi,250);updateUi();
}

if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});
else init();
