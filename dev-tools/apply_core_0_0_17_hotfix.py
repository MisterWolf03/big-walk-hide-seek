from pathlib import Path

core_path = Path('in-game-mod/core/CoreEntry.cs')
proj_path = Path('in-game-mod/core/BigWalkHideSeek.Core.csproj')
s = core_path.read_text(encoding='utf-8')


def once(old, new, label):
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly 1 match, found {count}')
    s = s.replace(old, new, 1)


if '0.0.16' not in s:
    raise SystemExit('Core source is not at 0.0.16')
s = s.replace('0.0.16', '0.0.17')

once(
    '    private Texture2D mapTexture;\n    private bool mapLoadAttempted;',
    '    private Texture2D mapTexture;\n    private Texture2D constraintMaskTexture;\n    private bool constraintMaskDirty = true;\n    private bool mapLoadAttempted;',
    'constraint mask fields')

once(
    '    private readonly List<string> questionHistory = new List<string>();\n',
    '    private readonly List<string> questionHistory = new List<string>();\n    private readonly List<MapConstraint> constraints = new List<MapConstraint>();\n',
    'constraint list field')

once(
    '    private GUIStyle bigNumberStyle;\n    private GUIStyle objectiveTitleStyle;',
    '    private GUIStyle bigNumberStyle;\n    private GUIStyle timerStatusStyle;\n    private GUIStyle objectiveTitleStyle;',
    'timer status style field')

once(
    '        questionHistory.Clear();\n        missionActive = false;',
    '        questionHistory.Clear();\n        constraints.Clear();\n        constraintMaskDirty = true;\n        missionActive = false;',
    'reset constraints')

once(
    '        GUI.Label(new Rect(timerRect.x, 31f, 74f, 16f), matchRunning ? "RUNNING" : (matchElapsedSeconds > 0f ? "PAUSED" : "NOT STARTED"), versionStyle);',
    '        GUI.Label(new Rect(timerRect.x - 12f, 29f, 86f, 22f), matchRunning ? "RUNNING" : (matchElapsedSeconds > 0f ? "PAUSED" : "NOT STARTED"), timerStatusStyle);',
    'timer clipping fix')

once(
    '        GUI.DrawTexture(mapRect, mapTexture, ScaleMode.StretchToFill, false);\n\n        if (showGrid)',
    '        GUI.DrawTexture(mapRect, mapTexture, ScaleMode.StretchToFill, false);\n        DrawConstraintMask(mapRect);\n\n        if (showGrid)',
    'draw constraint mask')

once(
    '            ApplyQuestion(cost, $"Centerline {line} → {answer}");',
    '            ApplyQuestion(cost, $"Centerline {line} → {answer}",\n                MapConstraint.Split(centerlineVertical ? \'x\' : \'y\', centerlineVertical ? 1700f : 3700f, centerlineAnswerIndex == 0));',
    'centerline constraint')

once(
    '            ApplyQuestion(cost, $"Nearest tower → {tower.Name}");',
    '            ApplyQuestion(cost, $"Nearest tower → {tower.Name}", MapConstraint.Nearest(tower.Name));',
    'nearest tower constraint')

once(
    '            ApplyQuestion(cost, $"{tower.Name} tower · {radius}u → {(towerRadiusInside ? "Inside" : "Outside")}");',
    '            ApplyQuestion(cost, $"{tower.Name} tower · {radius}u → {(towerRadiusInside ? "Inside" : "Outside")}",\n                MapConstraint.Radar(tower.Name, radius, towerRadiusInside));',
    'tower radius constraint')

once(
    '    private void ApplyQuestion(int cost, string description)\n    {\n        if (!questionTestOverride)',
    '    private void ApplyQuestion(int cost, string description, MapConstraint constraint)\n    {\n        if (!questionTestOverride)',
    'ApplyQuestion signature')

once(
    '        questionHistory.Add($"{FormatTime(matchElapsedSeconds)} · {description}");',
    '        if (constraint != null)\n        {\n            constraints.Add(constraint);\n            constraintMaskDirty = true;\n        }\n\n        questionHistory.Add($"{FormatTime(matchElapsedSeconds)} · {description}");',
    'store applied constraint')

mask_methods = r'''
    private void DrawConstraintMask(Rect mapRect)
    {
        if (constraints.Count == 0 || mapTexture == null)
            return;

        EnsureConstraintMaskTexture();
        if (constraintMaskTexture != null)
            GUI.DrawTexture(mapRect, constraintMaskTexture, ScaleMode.StretchToFill, true);
    }

    private void EnsureConstraintMaskTexture()
    {
        if (!constraintMaskDirty && constraintMaskTexture != null)
            return;
        if (mapTexture == null)
            return;

        if (constraintMaskTexture != null)
        {
            UnityEngine.Object.Destroy(constraintMaskTexture);
            constraintMaskTexture = null;
        }

        // Match the website's dark eliminated-area mask, but render it into one
        // cached texture so Unity only draws one overlay per frame.
        int width = Mathf.Max(1, (mapTexture.width + 3) / 4);
        int height = Mathf.Max(1, (mapTexture.height + 3) / 4);
        byte[] pixels = new byte[width * height * 4];

        for (int y = 0; y < height; y++)
        {
            float sourceY = ((y + 0.5f) / height) * mapTexture.height;
            for (int x = 0; x < width; x++)
            {
                float sourceX = ((x + 0.5f) / width) * mapTexture.width;
                Vector2 game = MapPixelToGame(sourceX, sourceY);
                if (AllowedAt(game.x, game.y))
                    continue;

                int i = (y * width + x) * 4;
                // BGRA32 equivalent of rgba(5,7,10,.72).
                pixels[i + 0] = 10;
                pixels[i + 1] = 7;
                pixels[i + 2] = 5;
                pixels[i + 3] = 184;
            }
        }

        constraintMaskTexture = new Texture2D(width, height, TextureFormat.BGRA32, false);
        constraintMaskTexture.LoadRawTextureData(ToIl2CppByteArray(pixels));
        constraintMaskTexture.Apply(false, true);
        constraintMaskTexture.wrapMode = TextureWrapMode.Clamp;
        constraintMaskTexture.filterMode = FilterMode.Bilinear;
        constraintMaskDirty = false;
    }

    private bool AllowedAt(float x, float y)
    {
        foreach (MapConstraint constraint in constraints)
        {
            if (constraint.Kind == ConstraintKind.Split)
            {
                float value = constraint.Axis == 'x' ? x : y;
                if (constraint.KeepLow)
                {
                    if (value > constraint.Value)
                        return false;
                }
                else if (value < constraint.Value)
                {
                    return false;
                }
            }
            else if (constraint.Kind == ConstraintKind.NearestTower)
            {
                MapFeature nearest = NearestTowerAt(x, y, out _);
                if (!string.Equals(nearest.Name, constraint.TowerName, StringComparison.Ordinal))
                    return false;
            }
            else if (constraint.Kind == ConstraintKind.TowerRadius)
            {
                MapFeature tower = FindTowerByName(constraint.TowerName);
                if (tower == null)
                    continue;

                float dx = x - tower.X;
                float dy = y - tower.Y;
                float distance = Mathf.Sqrt(dx * dx + dy * dy);
                if (constraint.KeepInside)
                {
                    if (distance > constraint.Radius)
                        return false;
                }
                else if (distance <= constraint.Radius)
                {
                    return false;
                }
            }
        }

        return true;
    }

    private static MapFeature FindTowerByName(string name)
    {
        foreach (MapFeature tower in Towers)
        {
            if (string.Equals(tower.Name, name, StringComparison.Ordinal))
                return tower;
        }
        return null;
    }

'''
once('    private void DrawGrid(Rect mapRect)\n    {', mask_methods + '    private void DrawGrid(Rect mapRect)\n    {', 'constraint mask methods')

once(
    '        bigNumberStyle = new GUIStyle(GUI.skin.label)\n        {\n            fontSize = 19,\n            fontStyle = FontStyle.Bold,\n            alignment = TextAnchor.MiddleRight,\n            normal = { textColor = Color.white }\n        };\n\n        objectiveTitleStyle',
    '        bigNumberStyle = new GUIStyle(GUI.skin.label)\n        {\n            fontSize = 19,\n            fontStyle = FontStyle.Bold,\n            alignment = TextAnchor.MiddleRight,\n            normal = { textColor = Color.white }\n        };\n\n        timerStatusStyle = new GUIStyle(GUI.skin.label)\n        {\n            fontSize = 9,\n            fontStyle = FontStyle.Bold,\n            alignment = TextAnchor.MiddleRight,\n            normal = { textColor = MutedText }\n        };\n\n        objectiveTitleStyle',
    'timer status style init')

once(
    '        if (mapTexture != null)\n        {\n            UnityEngine.Object.Destroy(mapTexture);\n            mapTexture = null;\n        }',
    '        if (mapTexture != null)\n        {\n            UnityEngine.Object.Destroy(mapTexture);\n            mapTexture = null;\n        }\n\n        if (constraintMaskTexture != null)\n        {\n            UnityEngine.Object.Destroy(constraintMaskTexture);\n            constraintMaskTexture = null;\n        }',
    'destroy constraint mask')

constraint_types = r'''
    private enum ConstraintKind
    {
        Split,
        NearestTower,
        TowerRadius
    }

    private sealed class MapConstraint
    {
        public readonly ConstraintKind Kind;
        public readonly char Axis;
        public readonly float Value;
        public readonly bool KeepLow;
        public readonly string TowerName;
        public readonly float Radius;
        public readonly bool KeepInside;

        private MapConstraint(ConstraintKind kind, char axis, float value, bool keepLow, string towerName, float radius, bool keepInside)
        {
            Kind = kind;
            Axis = axis;
            Value = value;
            KeepLow = keepLow;
            TowerName = towerName;
            Radius = radius;
            KeepInside = keepInside;
        }

        public static MapConstraint Split(char axis, float value, bool keepLow) =>
            new MapConstraint(ConstraintKind.Split, axis, value, keepLow, string.Empty, 0f, false);

        public static MapConstraint Nearest(string towerName) =>
            new MapConstraint(ConstraintKind.NearestTower, '\0', 0f, false, towerName, 0f, false);

        public static MapConstraint Radar(string towerName, float radius, bool keepInside) =>
            new MapConstraint(ConstraintKind.TowerRadius, '\0', 0f, false, towerName, radius, keepInside);
    }

'''
once('    private sealed class MapFeature\n    {', constraint_types + '    private sealed class MapFeature\n    {', 'constraint types')

core_path.write_text(s, encoding='utf-8')

p = proj_path.read_text(encoding='utf-8')
if '<Version>0.0.16</Version>' not in p:
    raise SystemExit('Project is not at 0.0.16')
p = p.replace('0.0.16', '0.0.17')
proj_path.write_text(p, encoding='utf-8')

print('Patched Core to 0.0.17')
