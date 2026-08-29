from pathlib import Path
p=Path('rooms.js')
s=p.read_text(encoding='utf-8')
old='''  const memberRef = dbMod.ref(db, `rooms/${code}/members/${user.uid}`);\n  if(!created){\n    await dbMod.update(memberRef, {name,role,joinedAt:dbMod.serverTimestamp(),lastSeen:dbMod.serverTimestamp()});\n  }\n  await dbMod.onDisconnect(memberRef).remove();\n'''
new='''  const memberRef = dbMod.ref(db, `rooms/${code}/members/${user.uid}`);\n  if(!created){\n    const existingSnap=await dbMod.get(memberRef);\n    if(existingSnap.exists()){\n      const existing=existingSnap.val()||{};\n      const updates={name,lastSeen:dbMod.serverTimestamp()};\n      if(existing.role===role)updates.role=role;\n      else updates.roleView=role;\n      await dbMod.update(memberRef,updates);\n    }else{\n      await dbMod.update(memberRef,{name,role,joinedAt:dbMod.serverTimestamp(),lastSeen:dbMod.serverTimestamp()});\n    }\n  }\n  await dbMod.onDisconnect(memberRef).remove();\n'''
if s.count(old)!=1: raise SystemExit(f'connect role anchor count {s.count(old)}')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
