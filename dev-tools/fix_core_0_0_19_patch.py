from pathlib import Path

path = Path('dev-tools/apply_core_0_0_19_foundation.py')
s = path.read_text(encoding='utf-8')

start_marker = "once(\n'''        if (constraintMaskTexture != null)\n"
end_marker = "\n\ntypes = r'''"
start = s.find(start_marker)
if start < 0:
    raise SystemExit('ambiguous audio-destroy patch block not found')
end = s.find(end_marker, start)
if end < 0:
    raise SystemExit('types marker after audio-destroy block not found')

replacement = r'''once(
'''    public void OnDestroy()
    {
        if (overlayOpen)
            SetOverlayOpen(false);

        if (mapTexture != null)
        {
            UnityEngine.Object.Destroy(mapTexture);
            mapTexture = null;
        }

        if (constraintMaskTexture != null)
        {
            UnityEngine.Object.Destroy(constraintMaskTexture);
            constraintMaskTexture = null;
        }
    }
''',
'''    public void OnDestroy()
    {
        if (overlayOpen)
            SetOverlayOpen(false);

        if (mapTexture != null)
        {
            UnityEngine.Object.Destroy(mapTexture);
            mapTexture = null;
        }

        if (constraintMaskTexture != null)
        {
            UnityEngine.Object.Destroy(constraintMaskTexture);
            constraintMaskTexture = null;
        }

        if (softToneClip != null)
            UnityEngine.Object.Destroy(softToneClip);
        if (normalToneClip != null)
            UnityEngine.Object.Destroy(normalToneClip);
        if (importantToneClip != null)
            UnityEngine.Object.Destroy(importantToneClip);
    }
''',
'audio destroy')'''

s = s[:start] + replacement + s[end:]
path.write_text(s, encoding='utf-8')
print('Made 0.0.19 audio cleanup patch target OnDestroy specifically.')
