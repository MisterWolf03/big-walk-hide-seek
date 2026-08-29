from pathlib import Path
import re

p=Path('index.html')
s=p.read_text(encoding='utf-8')

def once(old,new,label):
    global s
    n=s.count(old)
    if n!=1:
        raise SystemExit(f'{label}: expected 1 match, found {n}')
    s=s.replace(old,new,1)

# Visual cues must be reusable, not just visible the first time.
once('''  clearTimeout(gameCueTimer);\n  toast.className=meta.kind;title.textContent=meta.title;detail.textContent=detailOverride||meta.detail;\n  void toast.offsetWidth;toast.classList.add("show");\n  gameCueTimer=setTimeout(()=>{toast.classList.remove("show");setTimeout(()=>{if(!toast.classList.contains("show"))toast.style.display="none";},230);},2700);\n''','''  clearTimeout(gameCueTimer);\n  toast.style.display="";toast.className=meta.kind;title.textContent=meta.title;detail.textContent=detailOverride||meta.detail;\n  void toast.offsetWidth;toast.classList.add("show");\n  gameCueTimer=setTimeout(()=>toast.classList.remove("show"),2700);\n''','reusable visual cue')

# Rules schedule was removed; stop touching its old DOM ids.
pattern=r'''function updateRuleTimes\(\)\{\n(?:  .*\n)+?\}\nfunction updateRelocationSettingsInputs\(\)\{'''
replacement='''function updateRuleTimes(){}\nfunction updateRelocationSettingsInputs(){'''
s2,n=re.subn(pattern,replacement,s,count=1)
if n!=1:
    raise SystemExit(f'updateRuleTimes cleanup: expected 1 match, found {n}')
s=s2

# Hide exact relocation timing/configuration from connected Seekers.
once('''      <details class="settingsGroup">\n        <summary><span>Forced relocation</span><span class="settingsHint">Cadence + movement target</span></summary>\n''','''      <details class="settingsGroup" id="relocationSettingsGroup">\n        <summary><span>Forced relocation</span><span class="settingsHint">Cadence + movement target</span></summary>\n''','relocation settings id')
once('''  const actions=document.getElementById("topRoomActions"),popover=document.getElementById("roomConnected"),count=document.getElementById("roomPlayerCount"),playersBtn=document.getElementById("roomPlayersBtn"),qTab=document.querySelector('.tabBtn[data-tab="questions"]');\n''','''  const actions=document.getElementById("topRoomActions"),popover=document.getElementById("roomConnected"),count=document.getElementById("roomPlayerCount"),playersBtn=document.getElementById("roomPlayersBtn"),qTab=document.querySelector('.tabBtn[data-tab="questions"]'),relocationSettingsGroup=document.getElementById("relocationSettingsGroup");\n''','room chrome relocation settings ref')
once('''  if(qTab)qTab.style.display=isHider?"none":"";\n  if(isHider&&activeTab==="questions")showTab("game");\n''','''  if(qTab)qTab.style.display=isHider?"none":"";\n  if(relocationSettingsGroup)relocationSettingsGroup.style.display=!connected||isHider?"":"none";\n  if(isHider&&activeTab==="questions")showTab("game");\n''','hide relocation settings for seekers')

# Mission status must not leak that relocation is paused to Seekers.
once('''    next.textContent="Forced relocation · paused";return;\n''','''    next.textContent=isHider?"Forced relocation · paused":"Mission in progress";return;\n''','mission relocation privacy')

p.write_text(s,encoding='utf-8')
