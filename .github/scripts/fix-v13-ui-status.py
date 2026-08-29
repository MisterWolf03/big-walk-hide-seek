from pathlib import Path
p=Path('index.html')
s=p.read_text(encoding='utf-8')

def once(old,new,label):
    global s
    if s.count(old)!=1:
        raise SystemExit(f'{label}: expected 1 match, found {s.count(old)}')
    s=s.replace(old,new,1)

once('badge.classList.remove("hider","seeker");','badge.classList.remove("connected","hider","seeker");','role badge reset')
once('''  points.style.display=isSeeker?"block":"none";qSection.style.display=isSeeker?"block":"none";\n  card.classList.remove("hider","seeker","urgent");''','''  points.style.display=isSeeker?"block":"none";qSection.style.display=isSeeker?"block":"none";\n  if(isSeeker){\n    const anyUnlocked=testingUnlockOverride||Object.values(unlockTimes).some(t=>sec>=Number(t));\n    if(sec<.01&&!running){qStatus.textContent="Waiting";qNext.textContent=`First question unlocks ${formatApproxDuration(unlockTimes.grid)} after the match starts.`;}\n    else if(relocationState.active){qStatus.textContent="Locked";qNext.textContent="Questions are unavailable during forced relocation.";}\n    else if(questionCooldownActive()){qStatus.textContent=`Cooling down · ${formatApproxDuration(questionCooldownRemaining())}`;qNext.textContent=nextQuestionUnlockInfo(sec)+".";}\n    else{qStatus.textContent=anyUnlocked?"Ready":"Locked";qNext.textContent=nextQuestionUnlockInfo(sec)+".";}\n  }\n  card.classList.remove("hider","seeker","urgent");''','seeker question status precompute')
once('''  if(isSeeker){\n    if(relocationState.active)qStatus.textContent="Locked";\n    else if(questionCooldownActive())qStatus.textContent=`Cooling down · ${formatApproxDuration(questionCooldownRemaining())}`;\n    else qStatus.textContent="Ready";\n    qNext.textContent=nextQuestionUnlockInfo(sec)+".";\n  }\n}\nfunction seekerPointsEarned''','''}\nfunction seekerPointsEarned''','remove stale trailing question status')
p.write_text(s,encoding='utf-8')
