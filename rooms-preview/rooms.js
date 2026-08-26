const FIREBASE_SDK_VERSION = "12.17.1";
const SESSION_KEY = "bigwalk.room.session.v1";
const ROOM_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
const ROOM_CODE_LENGTH = 6;

const ui = {};
let firebase = null;
let app = null;
let auth = null;
let db = null;
let user = null;
let roomCode = null;
let roomData = null;
let roomRole = null;
let displayName = null;
let roomUnsubscribe = null;
let connectedUnsubscribe = null;
let offsetUnsubscribe = null;
let heartbeatTimer = null;
let serverTimeOffsetMs = 0;
let backendConnected = false;
let busy = false;

function byId(id){ return document.getElementById(id); }
function bridge(){ return window.BigWalkRoomBridge || null; }
function serverNow(){ return Date.now() + serverTimeOffsetMs; }
function isConnected(){ return !!(roomCode && roomData && user); }
function isHost(){ return isConnected() && roomData?.meta?.hostUid === user.uid; }
function canControlMatch(){ return !isConnected() || isHost(); }
function canEditSharedGame(){ return !isConnected() || roomRole === "seeker" || isHost(); }

function normalizeCode(value){
  return String(value || "").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, ROOM_CODE_LENGTH);
}
function randomCode(){
  const bytes = new Uint32Array(ROOM_CODE_LENGTH);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, n => ROOM_CODE_ALPHABET[n % ROOM_CODE_ALPHABET.length]).join("");
}
function safeName(value){
  const v = String(value || "").trim().replace(/\s+/g, " ").slice(0, 28);
  return v || "Player";
}
function configReady(config){
  return !!(config && config.apiKey && config.authDomain && config.projectId && config.databaseURL);
}
function clone(value){
  return value == null ? value : JSON.parse(JSON.stringify(value));
}
function savedSession(){
  try { return JSON.parse(localStorage.getItem(SESSION_KEY) || "null"); }
  catch { return null; }
}
function saveSession(){
  if(!roomCode) return;
  localStorage.setItem(SESSION_KEY, JSON.stringify({roomCode, role:roomRole, displayName}));
}
function clearSession(){ localStorage.removeItem(SESSION_KEY); }

function setStatus(text, kind=""){
  if(!ui.roomStatus) return;
  ui.roomStatus.textContent = text;
  ui.roomStatus.className = `roomStatus ${kind}`.trim();
}
function setBusy(value){
  busy = value;
  [ui.createBtn, ui.joinBtn, ui.leaveBtn].filter(Boolean).forEach(btn => btn.disabled = value);
}
function roleLabel(role){ return role === "hider" ? "Hider" : "Seeker"; }

function updateRoomUi(){
  if(!ui.disconnected || !ui.connected) return;
  const joined = isConnected();
  ui.disconnected.style.display = joined ? "none" : "block";
  ui.connected.style.display = joined ? "block" : "none";

  if(!joined){
    ui.roomCodeTop.textContent = "Offline";
    ui.roomCodeTop.classList.remove("connected");
    bridge()?.setRoomControlAuthority?.(true, false);
    bridge()?.setRoomSharedEditAuthority?.(true, false);
    return;
  }

  ui.roomCode.textContent = roomCode;
  ui.roomRole.textContent = roleLabel(roomRole);
  ui.roomHost.textContent = isHost() ? "You are host" : `Host: ${memberName(roomData?.meta?.hostUid) || "Connected player"}`;
  ui.roomCodeTop.textContent = roomCode;
  ui.roomCodeTop.classList.add("connected");

  const members = roomData?.members || {};
  const sorted = Object.entries(members).sort((a,b) => {
    const ah = a[0] === roomData?.meta?.hostUid ? -1 : 0;
    const bh = b[0] === roomData?.meta?.hostUid ? -1 : 0;
    return ah - bh || String(a[1]?.name || "").localeCompare(String(b[1]?.name || ""));
  });
  ui.memberList.innerHTML = "";
  for(const [uid, m] of sorted){
    const row = document.createElement("div");
    row.className = "roomMember";
    const left = document.createElement("div");
    left.className = "roomMemberName";
    const name = document.createElement("b");
    name.textContent = m?.name || "Player";
    const badges = document.createElement("div");
    badges.className = "roomMemberBadges";
    const role = document.createElement("span");
    role.className = `roomBadge ${m?.role === "hider" ? "hider" : "seeker"}`;
    role.textContent = roleLabel(m?.role);
    badges.appendChild(role);
    if(uid === roomData?.meta?.hostUid){
      const host = document.createElement("span");
      host.className = "roomBadge host";
      host.textContent = "HOST";
      badges.appendChild(host);
    }
    if(uid === user?.uid){
      const you = document.createElement("span");
      you.className = "roomBadge";
      you.textContent = "YOU";
      badges.appendChild(you);
    }
    left.append(name, badges);
    row.appendChild(left);
    ui.memberList.appendChild(row);
  }

  ui.hostControlsNote.textContent = isHost()
    ? "You control the shared match timer."
    : "Only the room host can start, pause, or reset the shared match timer.";

  bridge()?.setRoomControlAuthority?.(isHost(), true);
  bridge()?.setRoomSharedEditAuthority?.(canEditSharedGame(), true);
}

function memberName(uid){ return roomData?.members?.[uid]?.name || null; }
function hiderMemberEntry(){
  return Object.entries(roomData?.members || {}).find(([,m]) => m?.role === "hider") || null;
}
function hasHider(){ return !!hiderMemberEntry(); }
function getHiderRelocationSignal(){
  const entry=hiderMemberEntry();
  if(!entry)return null;
  const [uid,m]=entry;
  return {uid,index:Number(m?.relocationCompleteIndex||0),result:String(m?.relocationResult||"")};
}
async function signalRelocationComplete(index,result="completed"){
  if(!isConnected() || roomRole!=="hider")return false;
  const {dbMod}=firebase;
  await dbMod.update(dbMod.ref(db, `rooms/${roomCode}/members/${user.uid}`), {
    relocationCompleteIndex:Number(index||0),
    relocationResult:String(result||"completed").slice(0,16),
    lastSeen:dbMod.serverTimestamp(),
  });
  return true;
}

function getMatchSeconds(){
  const match = roomData?.state?.match;
  if(!match) return Number.NaN;
  let elapsed = Number(match.elapsedMs || 0);
  if(match.running && Number.isFinite(Number(match.startedAt))){
    elapsed += Math.max(0, serverNow() - Number(match.startedAt));
  }
  return Math.max(0, elapsed / 1000);
}

async function ensureFirebase(){
  if(firebase) return true;
  const config = window.BIGWALK_FIREBASE_CONFIG;
  if(!configReady(config)){
    setStatus("Room backend is not configured yet. See ROOMS_SETUP.md.", "warning");
    ui.setupNotice.style.display = "block";
    ui.createBtn.disabled = true;
    ui.joinBtn.disabled = true;
    return false;
  }

  setStatus("Connecting room service…");
  try{
    const base = `https://www.gstatic.com/firebasejs/${FIREBASE_SDK_VERSION}`;
    const [appMod, authMod, dbMod] = await Promise.all([
      import(`${base}/firebase-app.js`),
      import(`${base}/firebase-auth.js`),
      import(`${base}/firebase-database.js`),
    ]);
    firebase = {appMod, authMod, dbMod};
    app = appMod.initializeApp(config);
    auth = authMod.getAuth(app);
    await authMod.setPersistence(auth, authMod.browserLocalPersistence);
    const cred = auth.currentUser ? {user:auth.currentUser} : await authMod.signInAnonymously(auth);
    user = cred.user;
    db = dbMod.getDatabase(app);

    offsetUnsubscribe = dbMod.onValue(dbMod.ref(db, ".info/serverTimeOffset"), snap => {
      serverTimeOffsetMs = Number(snap.val() || 0);
    });
    connectedUnsubscribe = dbMod.onValue(dbMod.ref(db, ".info/connected"), snap => {
      backendConnected = snap.val() === true;
      if(isConnected()) setStatus(backendConnected ? "Room connected" : "Reconnecting…", backendConnected ? "good" : "warning");
    });

    ui.setupNotice.style.display = "none";
    ui.createBtn.disabled = false;
    ui.joinBtn.disabled = false;
    setStatus("Room service ready.", "good");
    return true;
  }catch(err){
    console.error("Room service initialization failed", err);
    setStatus(`Room service failed: ${err?.message || err}`, "error");
    return false;
  }
}

async function roomExists(code){
  const {dbMod} = firebase;
  const snap = await dbMod.get(dbMod.ref(db, `rooms/${code}/meta`));
  return snap.exists();
}
async function roomHasOtherHider(code){
  const {dbMod} = firebase;
  const snap = await dbMod.get(dbMod.ref(db, `rooms/${code}/members`));
  const members = snap.val() || {};
  return Object.entries(members).some(([uid, member]) => uid !== user?.uid && member?.role === "hider");
}

async function createRoom(){
  if(busy || !(await ensureFirebase())) return;
  const name = safeName(ui.nameInput.value);
  const role = ui.roleInput.value === "hider" ? "hider" : "seeker";
  setBusy(true);
  try{
    let code = null;
    for(let i=0;i<12;i++){
      const candidate = randomCode();
      if(!(await roomExists(candidate))){ code = candidate; break; }
    }
    if(!code) throw new Error("Couldn't reserve a room code. Try again.");

    const {dbMod} = firebase;
    const game = bridge()?.getSharedGameState?.() || {};
    const initial = {
      meta:{
        hostUid:user.uid,
        createdAt:dbMod.serverTimestamp(),
        updatedAt:dbMod.serverTimestamp(),
        schema:1,
      },
      members:{
        [user.uid]:{name,role,joinedAt:dbMod.serverTimestamp(),lastSeen:dbMod.serverTimestamp()}
      },
      state:{
        match:{running:false,elapsedMs:0,startedAt:null},
        game,
        revision:0,
        updatedAt:dbMod.serverTimestamp(),
        updatedBy:user.uid,
      }
    };
    await dbMod.set(dbMod.ref(db, `rooms/${code}`), initial);
    await connectToRoom(code, name, role, true);
  }catch(err){
    console.error(err);
    setStatus(err?.message || "Could not create room.", "error");
  }finally{ setBusy(false); }
}

async function joinRoom(){
  if(busy || !(await ensureFirebase())) return;
  const code = normalizeCode(ui.joinCode.value);
  if(code.length !== ROOM_CODE_LENGTH){
    setStatus(`Enter a ${ROOM_CODE_LENGTH}-character room code.`, "warning");
    return;
  }
  setBusy(true);
  try{
    if(!(await roomExists(code))) throw new Error("Room not found. Check the code and try again.");
    const role = ui.roleInput.value === "hider" ? "hider" : "seeker";
    if(role === "hider" && await roomHasOtherHider(code)){
      throw new Error("This room already has a hider. Join as a seeker instead.");
    }
    await connectToRoom(code, safeName(ui.nameInput.value), role, false);
  }catch(err){
    console.error(err);
    setStatus(err?.message || "Could not join room.", "error");
  }finally{ setBusy(false); }
}

async function connectToRoom(code, name, role, created){
  const {dbMod} = firebase;
  roomCode = code;
  displayName = name;
  roomRole = role;

  const memberRef = dbMod.ref(db, `rooms/${code}/members/${user.uid}`);
  if(!created){
    await dbMod.set(memberRef, {name,role,joinedAt:dbMod.serverTimestamp(),lastSeen:dbMod.serverTimestamp()});
  }
  await dbMod.onDisconnect(memberRef).remove();

  if(roomUnsubscribe) roomUnsubscribe();
  roomUnsubscribe = dbMod.onValue(dbMod.ref(db, `rooms/${code}`), snap => {
    if(!snap.exists()){
      setStatus("This room no longer exists.", "error");
      disconnectLocal(false);
      return;
    }
    roomData = snap.val();
    const oldHost = roomData?.meta?.hostUid;
    if(oldHost && !roomData?.members?.[oldHost]) claimHostIfMissing(oldHost);
    roomRole = roomData?.members?.[user.uid]?.role || roomRole;
    displayName = roomData?.members?.[user.uid]?.name || displayName;
    updateRoomUi();
    saveSession();
    bridge()?.applySharedRoomState?.(clone(roomData.state || {}));
    if(backendConnected) setStatus("Room connected", "good");
  });

  clearInterval(heartbeatTimer);
  heartbeatTimer = setInterval(() => {
    if(!isConnected()) return;
    dbMod.update(dbMod.ref(db, `rooms/${roomCode}/members/${user.uid}`), {lastSeen:dbMod.serverTimestamp()}).catch(()=>{});
  }, 20000);

  saveSession();
  updateRoomUi();
  const url = new URL(location.href);
  url.searchParams.set("room", code);
  history.replaceState(null, "", url);
  setStatus("Joining room…");
}

async function claimHostIfMissing(oldHost){
  if(!isConnected() || roomData?.members?.[oldHost]) return;
  try{
    const {dbMod} = firebase;
    await dbMod.runTransaction(dbMod.ref(db, `rooms/${roomCode}/meta/hostUid`), current => {
      if(current && current !== oldHost) return current;
      return user.uid;
    });
  }catch(err){ console.warn("Host handoff failed", err); }
}

async function leaveRoom(){
  if(!isConnected()) return;
  const code = roomCode;
  const uid = user.uid;
  const wasHost = isHost();
  const {dbMod} = firebase;
  setBusy(true);
  try{
    const members = roomData?.members || {};
    const remaining = Object.keys(members).filter(id => id !== uid);
    if(wasHost && remaining.length){
      const nextHost = remaining[0];
      await dbMod.update(dbMod.ref(db, `rooms/${code}`), {
        "meta/hostUid":nextHost,
        "meta/updatedAt":dbMod.serverTimestamp(),
      });
    }
    await dbMod.remove(dbMod.ref(db, `rooms/${code}/members/${uid}`));
    if(wasHost && !remaining.length){
      await dbMod.remove(dbMod.ref(db, `rooms/${code}`));
    }
  }catch(err){ console.warn("Leave room cleanup failed", err); }
  disconnectLocal(true);
  setBusy(false);
}

function disconnectLocal(clear=true){
  const finalMatchSeconds = getMatchSeconds();
  if(roomUnsubscribe){ roomUnsubscribe(); roomUnsubscribe = null; }
  clearInterval(heartbeatTimer); heartbeatTimer = null;
  roomCode = null; roomData = null; roomRole = null; displayName = null;
  if(clear) clearSession();
  const url = new URL(location.href);
  url.searchParams.delete("room");
  history.replaceState(null, "", url);
  bridge()?.onRoomDisconnected?.(Number.isFinite(finalMatchSeconds) ? finalMatchSeconds : null);
  updateRoomUi();
  setStatus("Not in a room.");
}

async function pushGameState(){
  if(!isConnected() || !canEditSharedGame()) return false;
  const game = bridge()?.getSharedGameState?.();
  if(!game) return false;
  const {dbMod} = firebase;
  await dbMod.update(dbMod.ref(db, `rooms/${roomCode}`), {
    "state/game":clone(game),
    "state/updatedAt":dbMod.serverTimestamp(),
    "state/updatedBy":user.uid,
    "meta/updatedAt":dbMod.serverTimestamp(),
  });
  return true;
}

async function startMatch(){
  if(!isConnected()) return false;
  if(!isHost()){ setStatus("Only the host can control the match timer.", "warning"); return false; }
  const match = roomData?.state?.match || {elapsedMs:0,running:false,startedAt:null};
  if(match.running) return true;
  const {dbMod} = firebase;
  await dbMod.update(dbMod.ref(db, `rooms/${roomCode}/state`), {
    match:{running:true,elapsedMs:Number(match.elapsedMs || 0),startedAt:dbMod.serverTimestamp()},
    updatedAt:dbMod.serverTimestamp(), updatedBy:user.uid,
  });
  return true;
}

async function pauseMatch(){
  if(!isConnected()) return false;
  if(!isHost()){ setStatus("Only the host can control the match timer.", "warning"); return false; }
  const elapsedMs = Math.round(getMatchSeconds() * 1000);
  const {dbMod} = firebase;
  await dbMod.update(dbMod.ref(db, `rooms/${roomCode}/state`), {
    match:{running:false,elapsedMs,startedAt:null},
    updatedAt:dbMod.serverTimestamp(), updatedBy:user.uid,
  });
  return true;
}

async function resetMatch(){
  if(!isConnected()) return false;
  if(!isHost()){ setStatus("Only the host can reset the match.", "warning"); return false; }
  const {dbMod} = firebase;
  const game = bridge()?.resetSharedGameForRoom?.() || bridge()?.getSharedGameState?.() || {};
  await dbMod.update(dbMod.ref(db, `rooms/${roomCode}`), {
    "state/match":{running:false,elapsedMs:0,startedAt:null},
    "state/game":clone(game),
    "state/updatedAt":dbMod.serverTimestamp(),
    "state/updatedBy":user.uid,
    "meta/updatedAt":dbMod.serverTimestamp(),
  });
  return true;
}

async function copyRoomCode(){
  if(!roomCode) return;
  try{ await navigator.clipboard.writeText(roomCode); }
  catch{
    const ta = document.createElement("textarea"); ta.value = roomCode; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove();
  }
  const old = ui.copyBtn.textContent;
  ui.copyBtn.textContent = "Copied";
  setTimeout(()=>ui.copyBtn.textContent=old, 1200);
}

async function restoreSession(){
  const param = normalizeCode(new URL(location.href).searchParams.get("room"));
  const saved = savedSession();
  if(param && param.length === ROOM_CODE_LENGTH) ui.joinCode.value = param;
  if(saved?.displayName) ui.nameInput.value = saved.displayName;
  if(saved?.role) ui.roleInput.value = saved.role;
  if(!(await ensureFirebase())) return;

  const code = param.length === ROOM_CODE_LENGTH ? param : normalizeCode(saved?.roomCode);
  if(code.length !== ROOM_CODE_LENGTH || !saved?.displayName || !saved?.role) return;
  try{
    if(await roomExists(code)){
      const role = saved.role === "hider" ? "hider" : "seeker";
      if(role === "hider" && await roomHasOtherHider(code)){
        clearSession();
        setStatus("This room already has a hider. Rejoin as a seeker.", "warning");
      }else{
        await connectToRoom(code, safeName(saved.displayName), role, false);
      }
    }else clearSession();
  }catch(err){ console.warn("Room reconnect failed", err); }
}

function bindUi(){
  ui.disconnected = byId("roomDisconnected");
  ui.connected = byId("roomConnected");
  ui.nameInput = byId("roomPlayerName");
  ui.roleInput = byId("roomRoleSelect");
  ui.joinCode = byId("roomJoinCode");
  ui.createBtn = byId("createRoomBtn");
  ui.joinBtn = byId("joinRoomBtn");
  ui.leaveBtn = byId("leaveRoomBtn");
  ui.copyBtn = byId("copyRoomCodeBtn");
  ui.roomCode = byId("currentRoomCode");
  ui.roomRole = byId("currentRoomRole");
  ui.roomHost = byId("currentRoomHost");
  ui.memberList = byId("roomMemberList");
  ui.roomStatus = byId("roomStatus");
  ui.setupNotice = byId("roomSetupNotice");
  ui.hostControlsNote = byId("roomHostControlsNote");
  ui.roomCodeTop = byId("roomTopStatus");

  ui.joinCode.addEventListener("input", ()=>ui.joinCode.value=normalizeCode(ui.joinCode.value));
  ui.joinCode.addEventListener("keydown", e=>{ if(e.key === "Enter") joinRoom(); });
  ui.nameInput.addEventListener("keydown", e=>{ if(e.key === "Enter" && normalizeCode(ui.joinCode.value).length === ROOM_CODE_LENGTH) joinRoom(); });
  ui.createBtn.addEventListener("click", createRoom);
  ui.joinBtn.addEventListener("click", joinRoom);
  ui.leaveBtn.addEventListener("click", leaveRoom);
  ui.copyBtn.addEventListener("click", copyRoomCode);
  updateRoomUi();
}

window.BigWalkRooms = {
  isConnected,
  isHost,
  canControlMatch,
  canEditSharedGame,
  getMatchSeconds,
  pushGameState,
  startMatch,
  pauseMatch,
  resetMatch,
  leaveRoom,
  getRoomCode:()=>roomCode,
  getRole:()=>roomRole,
  hasHider,
  getHiderRelocationSignal,
  signalRelocationComplete,
};

bindUi();
restoreSession();
