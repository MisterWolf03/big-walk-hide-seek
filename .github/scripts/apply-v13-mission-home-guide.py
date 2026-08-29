from pathlib import Path

path = Path("index.html")
text = path.read_text(encoding="utf-8")

replacements = []

old = '''function missionHomeDistance(plan,p=liveMarker){
  if(!plan?.start||!p)return Number.NaN;
  return Math.hypot(Number(p.x)-Number(plan.start.x),Number(p.y)-Number(plan.start.y));
}

function pointInMissionTarget(p,plan){'''
new = '''function missionHomeDistance(plan,p=liveMarker){
  if(!plan?.start||!p)return Number.NaN;
  return Math.hypot(Number(p.x)-Number(plan.start.x),Number(p.y)-Number(plan.start.y));
}
function beginMissionReturnHome(plan,result="cancelled",message=""){
  if(!plan?.start)return false;
  plan.returningHome=true;
  plan.returnResult=result==="completed"?"completed":"cancelled";
  plan.returnMessage=String(message||"");
  plan.noAlternate=false;
  localHiderMissionTargetCells=[];
  const homeD=missionHomeDistance(plan);
  if(Number.isFinite(homeD)&&homeD<=5)signalMissionResult(plan.returnResult);
  if(appInitialized)draw();
  return true;
}

function pointInMissionTarget(p,plan){'''
replacements.append((old,new,"return-home helper"))

old = '''  if(plan.returningHome){
    const homeD=missionHomeDistance(plan);
    if(Number.isFinite(homeD)&&homeD<=5)signalMissionResult("cancelled");
    return;
  }'''
new = '''  if(plan.returningHome){
    const homeD=missionHomeDistance(plan);
    if(Number.isFinite(homeD)&&homeD<=5)signalMissionResult(plan.returnResult==="completed"?"completed":"cancelled");
    return;
  }'''
replacements.append((old,new,"return-home completion result"))

old = '''        if(plan.returningHome){
          progress.textContent=Number.isFinite(homeD)?`${Math.max(0,Math.round(homeD))} units to hiding spot`:"Return home";
          message.textContent="Mission aborted. Return within 5 units of the hiding spot where you started the mission. No Power Charge will be awarded.";
        }else if(plan.noAlternate){'''
new = '''        if(plan.returningHome){
          progress.textContent=Number.isFinite(homeD)?`${Math.max(0,Math.round(homeD))} units to hiding spot`:"Return home";
          message.textContent=plan.returnMessage||(plan.returnResult==="completed"?"Objective complete. Return within 5 units of your original hiding spot to finish the mission.":"Return within 5 units of your original hiding spot. No Power Charge will be awarded.");
        }else if(plan.noAlternate){'''
replacements.append((old,new,"generic return-home UI"))

old = '''  if(!window.confirm("Abort this mission? You will earn no Power Charge and must return within 5 units of your original hiding spot."))return;
  plan.returningHome=true;plan.noAlternate=false;localHiderMissionTargetCells=[];
  if(Number.isFinite(homeD)&&homeD<=5)signalMissionResult("cancelled");
  renderMatchTimer();draw();'''
new = '''  if(!window.confirm("Abort this mission? You will earn no Power Charge and must return within 5 units of your original hiding spot."))return;
  beginMissionReturnHome(plan,"cancelled","Mission aborted. Return within 5 units of the hiding spot where you started the mission. No Power Charge will be awarded.");
  renderMatchTimer();draw();'''
replacements.append((old,new,"abort uses universal return-home flow"))

old = '''  ctx.restore();
}

function drawTowerRegions(){'''
new = '''  ctx.restore();
}
function drawHiderMissionReturnGuide(){
  const plan=localHiderMissionPlan;
  if(!isRoomHider()||!plan?.returningHome||!plan.start)return;
  const hx=Number(plan.start.x),hy=Number(plan.start.y);
  if(!Number.isFinite(hx)||!Number.isFinite(hy))return;
  const home=mapToPixel(hx,hy);
  ctx.save();
  if(liveMarker&&Number.isFinite(Number(liveMarker.x))&&Number.isFinite(Number(liveMarker.y))){
    const here=mapToPixel(Number(liveMarker.x),Number(liveMarker.y));
    ctx.beginPath();ctx.moveTo(here.x,here.y);ctx.lineTo(home.x,home.y);
    ctx.setLineDash([10,8]);ctx.lineWidth=3;ctx.strokeStyle="rgba(242,201,76,.92)";
    ctx.shadowColor="rgba(0,0,0,.8)";ctx.shadowBlur=4;ctx.stroke();ctx.setLineDash([]);
  }
  ctx.shadowColor="rgba(0,0,0,.85)";ctx.shadowBlur=7;
  ctx.beginPath();ctx.arc(home.x,home.y,13,0,Math.PI*2);
  ctx.fillStyle="#1b1810";ctx.fill();ctx.lineWidth=4;ctx.strokeStyle="#f2c94c";ctx.stroke();
  ctx.shadowBlur=0;ctx.strokeStyle="#ffe58b";ctx.lineWidth=2.2;ctx.lineJoin="round";
  ctx.beginPath();ctx.moveTo(home.x-6,home.y+1);ctx.lineTo(home.x,home.y-5);ctx.lineTo(home.x+6,home.y+1);ctx.stroke();
  ctx.strokeRect(home.x-4,home.y+1,8,7);
  ctx.font="bold 13px system-ui";ctx.textBaseline="middle";ctx.lineWidth=5;ctx.strokeStyle="rgba(0,0,0,.9)";
  ctx.strokeText("Hiding Spot",home.x+18,home.y);ctx.fillStyle="#ffe58b";ctx.fillText("Hiding Spot",home.x+18,home.y);
  ctx.restore();
}

function drawTowerRegions(){'''
replacements.append((old,new,"return-home map guide renderer"))

old = '''  if(showTowers)drawTowers();
  if(showLandmarks)drawLandmarks();
  drawPlayerMarker();drawRuler();'''
new = '''  if(showTowers)drawTowers();
  if(showLandmarks)drawLandmarks();
  drawHiderMissionReturnGuide();
  drawPlayerMarker();drawRuler();'''
replacements.append((old,new,"return-home guide draw order"))

for old,new,label in replacements:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly 1 match, found {count}")
    text = text.replace(old,new,1)

path.write_text(text,encoding="utf-8")
