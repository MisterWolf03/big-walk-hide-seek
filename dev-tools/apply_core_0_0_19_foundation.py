from pathlib import Path
import re

core_path = Path('in-game-mod/core/CoreEntry.cs')
proj_path = Path('in-game-mod/core/BigWalkHideSeek.Core.csproj')
s = core_path.read_text(encoding='utf-8')
p = proj_path.read_text(encoding='utf-8')

if '0.0.18' not in s:
    raise SystemExit('Core source is not at 0.0.18')
if '<Version>0.0.18</Version>' not in p:
    raise SystemExit('Core project is not at 0.0.18')

def once(old, new, label):
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly 1 match, found {count}')
    s = s.replace(old, new, 1)

def replace_between(start_marker, end_marker, new_text, label):
    global s
    start = s.find(start_marker)
    if start < 0:
        raise SystemExit(f'{label}: start marker not found')
    end = s.find(end_marker, start)
    if end < 0:
        raise SystemExit(f'{label}: end marker not found')
    s = s[:start] + new_text.rstrip() + '\n\n' + s[end:]

s = s.replace('0.0.18', '0.0.19')
p = p.replace('<Version>0.0.18</Version>', '<Version>0.0.19</Version>')
p = p.replace('<AssemblyVersion>0.0.18.0</AssemblyVersion>', '<AssemblyVersion>0.0.19.0</AssemblyVersion>')
p = p.replace('<FileVersion>0.0.18.0</FileVersion>', '<FileVersion>0.0.19.0</FileVersion>')

once('using System.Reflection;\n', 'using System.Reflection;\nusing System.Text.Json;\n', 'json using')

old_consts = '''    private const int PointsPerMinute = 1;
    private const float QuestionCooldownSeconds = 300f;
    private const float CenterlineUnlockSeconds = 600f;
    private const float NearestTowerUnlockSeconds = 1200f;
    private const float TowerRadiusUnlockSeconds = 1800f;
    private const float MissionTargetDistance = 200f;
'''
new_consts = '''    private const float MiniMapWidth = 210f;
    private const float MiniMapHeight = 164f;
    private const float NavHudWidth = 176f;
    private const float PassiveHudMargin = 14f;
'''
once(old_consts, new_consts, 'gameplay constants')

once(
'''    private float gameX;
    private float gameY;

    private float zoom = 1f;
''',
'''    private float gameX;
    private float gameY;
    private float playerHeadingDegrees;
    private string playerHeadingDirection = "N";

    private LocalSettings settings = new LocalSettings();
    private string settingsPath = string.Empty;
    private bool initialized;

    private readonly List<UiNotification> notifications = new List<UiNotification>();
    private AudioSource uiAudioSource;
    private AudioClip softToneClip;
    private AudioClip normalToneClip;
    private AudioClip importantToneClip;
    private bool previousCooldownActive;
    private bool previousCanAffordNearest;
    private bool previousCanAffordRadius;

    private float zoom = 1f;
''',
'state fields')

once(
'''    private bool centerlineVertical;
    private int centerlineAnswerIndex;
''',
'''    private bool centerlineVertical;
    private int centerlineAnswerIndex;
    private int centerlineUses;
''',
'centerline uses field')

update_method = r'''    public void Update()
    {
        EnsureInitialized();
        UpdateMatchTimer();

        bool needsPosition = overlayOpen
            || missionActive
            || settings.MiniMapEnabled
            || settings.NavHudEnabled
            || settings.MissionHudEnabled;
        if (needsPosition)
            UpdatePlayerPosition();

        UpdateMissionProgress();
        UpdateGameplayNotifications();

        if (Input.GetKeyDown(KeyCode.M) || Input.GetKeyDown(KeyCode.F7))
        {
            SetOverlayOpen(!overlayOpen);
            return;
        }

        if (selectedRole == PlayerRole.Hider
            && missionActive
            && missionReady
            && Input.GetKeyDown(KeyCode.R))
        {
            CompleteMovementMission();
            return;
        }

        if (overlayOpen && Input.GetKeyDown(KeyCode.Escape))
        {
            SetOverlayOpen(false);
            return;
        }

        if (!overlayOpen)
            return;

        Cursor.visible = true;
        Cursor.lockState = CursorLockMode.None;
        EnsureMapTexture();
    }'''
replace_between('    public void Update()\n', '    private void UpdateMatchTimer()\n', update_method, 'Update method')

match_methods = r'''    private void UpdateMatchTimer()
    {
        float now = Time.unscaledTime;
        if (!matchRunning)
        {
            matchLastTick = now;
            return;
        }

        if (matchLastTick <= 0f)
            matchLastTick = now;

        float delta = Mathf.Max(0f, now - matchLastTick);
        matchElapsedSeconds += delta;
        matchLastTick = now;
    }

    private void StartOrResumeMatch()
    {
        bool resuming = matchElapsedSeconds > 0.01f;
        matchLastTick = Time.unscaledTime;
        matchRunning = true;
        Notify(resuming ? "MATCH RESUMED" : "MATCH STARTED",
            resuming ? $"Timer resumed at {FormatTime(matchElapsedSeconds)}." : "The Hide + Seek timer is running.",
            AccentGreen, resuming ? NotificationTone.Normal : NotificationTone.Important);
        CoreEntry.Logger?.LogInfo(resuming ? "Hide + Seek match resumed." : "Hide + Seek match started.");
    }

    private void PauseMatch()
    {
        if (!matchRunning)
            return;

        UpdateMatchTimer();
        matchRunning = false;
        Notify("MATCH PAUSED", $"Timer paused at {FormatTime(matchElapsedSeconds)}.", AccentYellow, NotificationTone.Normal);
        CoreEntry.Logger?.LogInfo("Hide + Seek match paused.");
    }

    private void ResetMatchState()
    {
        matchRunning = false;
        matchElapsedSeconds = 0f;
        matchLastTick = Time.unscaledTime;
        seekerPointsSpent = 0;
        questionCooldownUntil = 0f;
        centerlineUses = 0;
        questionHistory.Clear();
        constraints.Clear();
        constraintMaskDirty = true;
        missionActive = false;
        missionCompleted = false;
        missionReady = false;
        missionDistance = 0f;
        missionStart = Vector2.zero;
        previousCooldownActive = false;
        previousCanAffordNearest = false;
        previousCanAffordRadius = false;
        Notify("MATCH RESET", "Timer, points, questions, constraints, and mission state were reset.", AccentYellow, NotificationTone.Important);
        CoreEntry.Logger?.LogInfo("Hide + Seek gameplay state reset.");
    }'''
replace_between('    private void UpdateMatchTimer()\n', '    private void SetOverlayOpen(bool open)\n', match_methods, 'match methods')

player_position = r'''    private void UpdatePlayerPosition()
    {
        if (playerRb == null && Time.unscaledTime >= nextPlayerSearchAt)
        {
            nextPlayerSearchAt = Time.unscaledTime + 1f;
            FindPlayerRigidbody();
        }

        if (playerRb == null)
        {
            hasPlayerPosition = false;
            return;
        }

        try
        {
            Vector3 p = playerRb.position;
            UnityToBigWalk(p.x, p.z, out gameX, out gameY);

            Vector3 forward = playerRb.transform.forward;
            UnityToBigWalk(p.x + forward.x * 10f, p.z + forward.z * 10f, out float headingX, out float headingY);
            BearingInfo(gameX, gameY, headingX, headingY, out playerHeadingDegrees, out playerHeadingDirection);

            hasPlayerPosition = true;
        }
        catch
        {
            playerRb = null;
            hasPlayerPosition = false;
        }
    }'''
replace_between('    private void UpdatePlayerPosition()\n', '    private void FindPlayerRigidbody()\n', player_position, 'player position')

ongui = r'''    public void OnGUI()
    {
        EnsureInitialized();
        EnsureStyles();
        GUI.depth = -10000;

        Color oldColor = GUI.color;
        Color oldBackground = GUI.backgroundColor;

        if (!overlayOpen)
        {
            if (settings.MiniMapEnabled || settings.NavHudEnabled || (settings.MissionHudEnabled && missionActive))
            {
                if (settings.MiniMapEnabled)
                    EnsureMapTexture();
                DrawPassiveHud();
            }

            DrawNotifications();
            GUI.color = oldColor;
            GUI.backgroundColor = oldBackground;
            return;
        }

        EnsureMapTexture();

        GUI.color = PageBackground;
        GUI.DrawTexture(new Rect(0f, 0f, Screen.width, Screen.height), Texture2D.whiteTexture);
        GUI.color = Color.white;

        DrawTopBar();
        Rect viewport = new Rect(0f, TopBarHeight, Screen.width, Mathf.Max(100f, Screen.height - TopBarHeight));
        DrawMap(viewport);
        DrawNotifications();

        GUI.color = oldColor;
        GUI.backgroundColor = oldBackground;

        Event evt = Event.current;
        if (evt != null && (evt.isMouse || evt.type == EventType.ScrollWheel))
            evt.Use();
    }

    private void DrawPassiveHud()
    {
        if (settings.MissionHudEnabled && selectedRole == PlayerRole.Hider && missionActive)
            DrawMissionHud(new Rect(PassiveHudMargin, PassiveHudMargin, 286f, missionReady ? 112f : 100f));

        float mapX = Screen.width - PassiveHudMargin - MiniMapWidth;
        Rect miniMapRect = new Rect(mapX, PassiveHudMargin, MiniMapWidth, MiniMapHeight);

        if (settings.MiniMapEnabled && mapTexture != null)
            DrawMiniMap(miniMapRect);

        if (settings.NavHudEnabled)
        {
            float navX = settings.MiniMapEnabled
                ? miniMapRect.x - 8f - NavHudWidth
                : Screen.width - PassiveHudMargin - NavHudWidth;
            DrawNavHud(new Rect(navX, PassiveHudMargin, NavHudWidth, MiniMapHeight));
        }
    }

    private void DrawMiniMap(Rect rect)
    {
        DrawPanelRect(rect, new Color(0.045f, 0.055f, 0.07f, 0.94f), BorderColor);
        Rect map = new Rect(rect.x + 5f, rect.y + 5f, rect.width - 10f, rect.height - 10f);

        if (!hasPlayerPosition)
        {
            GUI.Label(map, "LOCATING PLAYER…", statusStyle);
            return;
        }

        Vector2 centerPixel = GameToMapPixel(gameX, gameY);
        float sourceWidth = 620f;
        float sourceHeight = sourceWidth * (map.height / map.width);
        sourceWidth = Mathf.Min(sourceWidth, mapTexture.width);
        sourceHeight = Mathf.Min(sourceHeight, mapTexture.height);

        float sourceX = Mathf.Clamp(centerPixel.x - sourceWidth * 0.5f, 0f, Mathf.Max(0f, mapTexture.width - sourceWidth));
        float sourceY = Mathf.Clamp(centerPixel.y - sourceHeight * 0.5f, 0f, Mathf.Max(0f, mapTexture.height - sourceHeight));

        Rect uv = new Rect(
            sourceX / mapTexture.width,
            1f - ((sourceY + sourceHeight) / mapTexture.height),
            sourceWidth / mapTexture.width,
            sourceHeight / mapTexture.height);

        GUI.DrawTextureWithTexCoords(map, mapTexture, uv, false);

        foreach (MapFeature tower in Towers)
        {
            Vector2 towerPixel = GameToMapPixel(tower.X, tower.Y);
            if (towerPixel.x < sourceX || towerPixel.x > sourceX + sourceWidth
                || towerPixel.y < sourceY || towerPixel.y > sourceY + sourceHeight)
                continue;

            float tx = map.x + ((towerPixel.x - sourceX) / sourceWidth) * map.width;
            float ty = map.y + ((towerPixel.y - sourceY) / sourceHeight) * map.height;
            DrawSolidRect(new Rect(tx - 3f, ty - 3f, 6f, 6f), tower.Color);
        }

        float px = map.x + ((centerPixel.x - sourceX) / sourceWidth) * map.width;
        float py = map.y + ((centerPixel.y - sourceY) / sourceHeight) * map.height;
        DrawSolidRect(new Rect(px - 5f, py - 5f, 10f, 10f), Color.white);
        DrawSolidRect(new Rect(px - 3f, py - 3f, 6f, 6f), AccentCyan);

        Rect north = new Rect(map.x + map.width * 0.5f - 14f, map.y + 3f, 28f, 18f);
        DrawPanelRect(north, new Color(0.03f, 0.04f, 0.055f, 0.82f), new Color(1f, 1f, 1f, 0.12f));
        GUI.Label(north, "N", statusStyle);
    }

    private void DrawNavHud(Rect rect)
    {
        DrawPanelRect(rect, new Color(0.055f, 0.068f, 0.088f, 0.94f), BorderColor);
        GUI.Label(new Rect(rect.x + 10f, rect.y + 8f, rect.width - 20f, 18f), "NAVIGATION", liveCardHeadingStyle);

        if (!hasPlayerPosition)
        {
            GUI.Label(new Rect(rect.x + 10f, rect.y + 38f, rect.width - 20f, 50f), "Searching for PlayerCharacter…", emptyStateStyle);
            return;
        }

        MapFeature nearest = NearestTowerAt(gameX, gameY, out float distance);

        GUI.Label(new Rect(rect.x + 10f, rect.y + 32f, rect.width - 20f, 18f), $"Y {gameY:0}  X {gameX:0}", metricValueStyle);
        GUI.Label(new Rect(rect.x + 10f, rect.y + 52f, rect.width - 20f, 17f), GridSquare(gameX, gameY), hintStyle);

        DrawPanelRect(new Rect(rect.x + 10f, rect.y + 76f, rect.width - 20f, 42f),
            new Color(0.04f, 0.055f, 0.07f, 0.96f), new Color(AccentCyan.r * 0.5f, AccentCyan.g * 0.5f, AccentCyan.b * 0.5f, 1f));
        GUI.Label(new Rect(rect.x + 14f, rect.y + 79f, rect.width - 28f, 16f), "COMPASS", dockLabelStyle);
        GUI.Label(new Rect(rect.x + 14f, rect.y + 94f, rect.width - 28f, 22f),
            $"{playerHeadingDirection} · {playerHeadingDegrees:000}°", statusStyle);

        GUI.Label(new Rect(rect.x + 10f, rect.y + 126f, rect.width - 20f, 16f), $"Nearest: {nearest.Name}", hintStyle);
        GUI.Label(new Rect(rect.x + 10f, rect.y + 143f, rect.width - 20f, 16f), $"{distance:0} units away", hintStyle);
    }

    private void DrawMissionHud(Rect rect)
    {
        Color border = missionReady ? AccentGreen : AccentPurple;
        DrawPanelRect(rect, new Color(0.095f, 0.065f, 0.13f, 0.95f), border);
        GUI.Label(new Rect(rect.x + 12f, rect.y + 8f, rect.width - 24f, 18f), missionReady ? "MISSION READY" : "HIDER MISSION", missionCardHeadingStyle);

        if (missionReady)
        {
            GUI.Label(new Rect(rect.x + 12f, rect.y + 34f, rect.width - 24f, 22f), "Movement requirement complete.", statusStyle);
            GUI.Label(new Rect(rect.x + 12f, rect.y + 66f, rect.width - 24f, 30f), "PRESS R WHEN READY", statusStyle);
            return;
        }

        float target = Mathf.Max(1f, settings.MissionTargetDistance);
        float progress = Mathf.Clamp01(missionDistance / target);
        GUI.Label(new Rect(rect.x + 12f, rect.y + 33f, rect.width - 24f, 20f),
            $"Move {settings.MissionTargetDistance:0} units · {missionDistance:0}/{settings.MissionTargetDistance:0}", hintStyle);

        Rect bar = new Rect(rect.x + 12f, rect.y + 62f, rect.width - 24f, 12f);
        DrawSolidRect(bar, new Color(0.04f, 0.05f, 0.07f, 1f));
        DrawSolidRect(new Rect(bar.x, bar.y, bar.width * progress, bar.height), AccentPurple);
        GUI.Label(new Rect(rect.x + 12f, rect.y + 78f, rect.width - 24f, 16f),
            $"{Mathf.Max(0f, settings.MissionTargetDistance - missionDistance):0} units remaining", hintStyle);
    }'''
replace_between('    public void OnGUI()\n', '    private void DrawTopBar()\n', ongui, 'OnGUI/passive HUD')

topbar = r'''    private void DrawTopBar()
    {
        DrawSolidRect(new Rect(0f, 0f, Screen.width, TopBarHeight), TopBarBackground);
        DrawSolidRect(new Rect(0f, TopBarHeight - 1f, Screen.width, 1f), BorderColor);

        GUI.Label(new Rect(14f, 8f, 130f, 22f), "BIG WALK H+S", brandStyle);
        GUI.Label(new Rect(15f, 31f, 130f, 16f), "CORE v0.0.19", versionStyle);

        float tabX = 150f;
        DrawTopTab(ref tabX, "GAME", UiTab.Game, 64f);
        if (selectedRole == PlayerRole.Seeker)
            DrawTopTab(ref tabX, "QUESTIONS", UiTab.Questions, 88f);
        DrawTopTab(ref tabX, "MAP", UiTab.Map, 58f);
        DrawTopTab(ref tabX, "MORE", UiTab.More, 60f);

        float chipX = tabX + 12f;
        if (selectedRole == PlayerRole.Seeker)
        {
            DrawTopChip(new Rect(chipX, 15f, 150f, 28f),
                $"{SeekerPointsBalance()} SP · +{settings.PointsPerMinute}/min", AccentYellow);
            chipX += 158f;
        }

        DrawTopChip(new Rect(chipX, 15f, 86f, 28f),
            selectedRole == PlayerRole.Seeker ? "SEEKER" : "HIDER",
            selectedRole == PlayerRole.Seeker ? AccentBlue : AccentPurple);

        float closeX = Screen.width - 90f;
        float timerRight = closeX - 10f;
        DrawTopMatchControls(timerRight);

        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = new Color(0.16f, 0.19f, 0.23f, 1f);
        if (GUI.Button(new Rect(closeX, 11f, 76f, 36f), "CLOSE", compactButtonStyle))
            SetOverlayOpen(false);
        GUI.backgroundColor = oldBackground;
    }'''
replace_between('    private void DrawTopBar()\n', '    private void DrawTopTab(', topbar, 'top bar')

game_block = r'''    private void DrawGamePanel(Rect panel)
    {
        GUI.Label(new Rect(panel.x + 14f, panel.y + 10f, panel.width - 28f, 21f), "GAME", panelHeadingStyle);
        GUI.Label(new Rect(panel.x + 14f, panel.y + 29f, panel.width - 28f, 18f), "Role, match state, and current objective", panelSubtitleStyle);

        float cardX = panel.x + 12f;
        float cardWidth = panel.width - 24f;
        float y = panel.y + 57f;

        Rect objective = new Rect(cardX, y, cardWidth, 132f);
        DrawCurrentObjectiveCard(objective);
        y += objective.height + 10f;

        Rect roleCard = new Rect(cardX, y, cardWidth, 104f);
        DrawRoleCard(roleCard);
        y += roleCard.height + 10f;

        Rect matchCard = new Rect(cardX, y, cardWidth, 100f);
        DrawMatchCard(matchCard);
        y += matchCard.height + 10f;

        if (selectedRole == PlayerRole.Hider)
        {
            Rect missionCard = new Rect(cardX, y, cardWidth, 174f);
            DrawMissionCard(missionCard);
        }
    }

    private void DrawCurrentObjectiveCard(Rect card)
    {
        Color border = selectedRole == PlayerRole.Hider
            ? new Color(0.43f, 0.31f, 0.49f, 1f)
            : new Color(0.31f, 0.40f, 0.50f, 1f);
        DrawPanelRect(card, new Color(0.10f, 0.13f, 0.17f, 0.98f), border);
        GUI.Label(new Rect(card.x + 13f, card.y + 8f, card.width - 26f, 16f), "CURRENT STATUS", objectiveEyebrowStyle);

        string title;
        string detail;
        if (!matchRunning && matchElapsedSeconds <= 0.01f)
        {
            title = "Waiting to start";
            detail = selectedRole == PlayerRole.Seeker
                ? "Start the timer once the Hider confirms they have found their spot."
                : "Find your hiding spot, then tell the Seeker when you are ready.";
        }
        else if (selectedRole == PlayerRole.Hider && missionActive)
        {
            title = missionReady ? "Mission target reached" : $"Move {settings.MissionTargetDistance:0} units";
            detail = missionReady
                ? "Press R whenever you are ready to complete the mission."
                : $"Travel {Mathf.Max(0f, settings.MissionTargetDistance - missionDistance):0} more units from your mission start.";
        }
        else if (selectedRole == PlayerRole.Hider)
        {
            title = "Stay hidden";
            detail = "No movement objective is active. The current test mission can be triggered below.";
        }
        else
        {
            title = "Search for the Hider";
            detail = QuestionCooldownActive()
                ? $"Questions cooling down · {FormatTime(QuestionCooldownRemaining())} remaining."
                : NextQuestionStatus();
        }

        GUI.Label(new Rect(card.x + 13f, card.y + 30f, card.width - 26f, 34f), title, objectiveTitleStyle);
        GUI.Label(new Rect(card.x + 13f, card.y + 72f, card.width - 26f, 50f), detail, emptyStateStyle);
    }

    private void DrawRoleCard(Rect card)
    {
        DrawPanelRect(card, CardBackground, BorderColor);
        GUI.Label(new Rect(card.x + 12f, card.y + 7f, card.width - 24f, 20f), "ROLE", cardHeadingStyle);
        GUI.Label(new Rect(card.x + 12f, card.y + 29f, card.width - 24f, 18f), "Local role selection for this client", panelSubtitleStyle);

        if (DrawRoleButton(new Rect(card.x + 12f, card.y + 55f, (card.width - 30f) * 0.5f, 37f), "SEEKER", PlayerRole.Seeker))
            SetRole(PlayerRole.Seeker);
        if (DrawRoleButton(new Rect(card.x + 18f + (card.width - 30f) * 0.5f, card.y + 55f, (card.width - 30f) * 0.5f, 37f), "HIDER", PlayerRole.Hider))
            SetRole(PlayerRole.Hider);
    }

    private void SetRole(PlayerRole role)
    {
        if (selectedRole == role)
            return;

        selectedRole = role;
        if (selectedRole == PlayerRole.Hider && activeTab == UiTab.Questions)
            activeTab = UiTab.Game;

        previousCanAffordNearest = false;
        previousCanAffordRadius = false;
    }

    private bool DrawRoleButton(Rect rect, string label, PlayerRole role)
    {
        Color oldBackground = GUI.backgroundColor;
        bool active = selectedRole == role;
        Color accent = role == PlayerRole.Seeker ? AccentBlue : AccentPurple;
        GUI.backgroundColor = active
            ? new Color(accent.r * 0.38f, accent.g * 0.38f, accent.b * 0.38f, 1f)
            : new Color(0.12f, 0.14f, 0.17f, 1f);
        bool clicked = GUI.Button(rect, label, compactButtonStyle);
        if (active)
            DrawSolidRect(new Rect(rect.x + 8f, rect.yMax - 2f, rect.width - 16f, 2f), accent);
        GUI.backgroundColor = oldBackground;
        return clicked;
    }

    private void DrawMatchCard(Rect card)
    {
        DrawPanelRect(card, CardBackground, BorderColor);
        GUI.Label(new Rect(card.x + 12f, card.y + 7f, card.width - 24f, 20f), "MATCH", cardHeadingStyle);
        float y = card.y + 31f;
        DrawMetricRow(card, y, "Elapsed", FormatTime(matchElapsedSeconds)); y += 22f;
        DrawMetricRow(card, y, "State", matchRunning ? "Running" : (matchElapsedSeconds > 0f ? "Paused" : "Not started")); y += 22f;
        DrawMetricRow(card, y, "Role", selectedRole == PlayerRole.Seeker ? "Seeker" : "Hider");
    }

    private void DrawMissionCard(Rect card)
    {
        Color bg = missionActive
            ? new Color(0.15f, 0.105f, 0.21f, 0.98f)
            : CardBackground;
        Color border = missionActive
            ? new Color(0.50f, 0.35f, 0.75f, 1f)
            : BorderColor;
        DrawPanelRect(card, bg, border);
        GUI.Label(new Rect(card.x + 12f, card.y + 7f, card.width - 24f, 20f), "HIDER MISSION", missionCardHeadingStyle);

        if (!missionActive)
        {
            string message = missionCompleted
                ? "Mission complete. Trigger it again whenever you want to retest."
                : $"Start here, then move {settings.MissionTargetDistance:0} map units away.";
            GUI.Label(new Rect(card.x + 12f, card.y + 35f, card.width - 24f, 48f), message, emptyStateStyle);

            GUI.enabled = hasPlayerPosition;
            Color oldBackground = GUI.backgroundColor;
            GUI.backgroundColor = new Color(0.30f, 0.20f, 0.43f, 1f);
            if (GUI.Button(new Rect(card.x + 12f, card.y + 122f, card.width - 24f, 38f), "START MOVEMENT MISSION", compactButtonStyle))
                StartMovementMission();
            GUI.backgroundColor = oldBackground;
            GUI.enabled = true;
            return;
        }

        DrawMetricRow(card, card.y + 33f, "Progress", $"{missionDistance:0} / {settings.MissionTargetDistance:0} units");
        DrawMetricRow(card, card.y + 55f, "Remaining", $"{Mathf.Max(0f, settings.MissionTargetDistance - missionDistance):0} units");
        DrawMetricRow(card, card.y + 77f, "Status", missionReady ? "Press R when ready" : "Keep moving");

        Color oldBg = GUI.backgroundColor;
        if (missionReady)
        {
            GUI.backgroundColor = new Color(0.20f, 0.43f, 0.29f, 1f);
            if (GUI.Button(new Rect(card.x + 12f, card.y + 122f, 154f, 38f), "READY · R", compactButtonStyle))
                CompleteMovementMission();
            GUI.backgroundColor = new Color(0.28f, 0.13f, 0.15f, 1f);
            if (GUI.Button(new Rect(card.x + card.width - 116f, card.y + 122f, 104f, 38f), "CANCEL", compactButtonStyle))
                CancelMovementMission();
        }
        else
        {
            GUI.backgroundColor = new Color(0.28f, 0.13f, 0.15f, 1f);
            if (GUI.Button(new Rect(card.x + 12f, card.y + 122f, card.width - 24f, 38f), "CANCEL MISSION", compactButtonStyle))
                CancelMovementMission();
        }
        GUI.backgroundColor = oldBg;
    }

    private void StartMovementMission()
    {
        if (!hasPlayerPosition)
            return;

        missionStart = new Vector2(gameX, gameY);
        missionDistance = 0f;
        missionReady = false;
        missionCompleted = false;
        missionActive = true;
        Notify("NEW MISSION", $"Move {settings.MissionTargetDistance:0} units from your starting position.", AccentPurple, NotificationTone.Important, PlayerRole.Hider);
        CoreEntry.Logger?.LogInfo($"Movement mission started at Y {gameY:0}, X {gameX:0}. Target: {settings.MissionTargetDistance:0} units.");
    }

    private void UpdateMissionProgress()
    {
        if (!missionActive || !hasPlayerPosition)
            return;

        bool wasReady = missionReady;
        missionDistance = Vector2.Distance(missionStart, new Vector2(gameX, gameY));
        missionReady = missionDistance >= settings.MissionTargetDistance;

        if (!wasReady && missionReady)
            Notify("MISSION READY", "Movement requirement met. Press R when you are ready.", AccentGreen, NotificationTone.Important, PlayerRole.Hider);
    }

    private void CompleteMovementMission()
    {
        if (!missionActive || !missionReady)
            return;

        missionActive = false;
        missionCompleted = true;
        missionReady = false;
        Notify("MISSION COMPLETE", "Movement mission completed.", AccentGreen, NotificationTone.Normal, PlayerRole.Hider);
        CoreEntry.Logger?.LogInfo($"Movement mission completed after travelling {missionDistance:0} units.");
    }

    private void CancelMovementMission()
    {
        missionActive = false;
        missionReady = false;
        missionDistance = 0f;
        CoreEntry.Logger?.LogInfo("Movement mission cancelled.");
    }'''
replace_between('    private void DrawGamePanel(Rect panel)\n', '    private void DrawQuestionsPanel(Rect panel)\n', game_block, 'game block')

questions_block = r'''    private void DrawQuestionsPanel(Rect panel)
    {
        GUI.Label(new Rect(panel.x + 14f, panel.y + 10f, panel.width - 28f, 21f), "QUESTIONS", panelHeadingStyle);
        GUI.Label(new Rect(panel.x + 14f, panel.y + 29f, panel.width - 28f, 18f), "Seeker Points + manual answer controls", panelSubtitleStyle);

        if (selectedRole != PlayerRole.Seeker)
        {
            activeTab = UiTab.Game;
            return;
        }

        float cardX = panel.x + 12f;
        float cardWidth = panel.width - 24f;
        float y = panel.y + 57f;

        Rect pointsCard = new Rect(cardX, y, cardWidth, 92f);
        DrawSeekerPointsCard(pointsCard);
        y += pointsCard.height + 8f;

        Rect centerline = new Rect(cardX, y, cardWidth, 142f);
        DrawCenterlineQuestionCard(centerline);
        y += centerline.height + 8f;

        Rect nearest = new Rect(cardX, y, cardWidth, 118f);
        DrawNearestTowerQuestionCard(nearest);
        y += nearest.height + 8f;

        Rect radius = new Rect(cardX, y, cardWidth, 150f);
        DrawTowerRadiusQuestionCard(radius);
        y += radius.height + 8f;

        if (y + 84f < panel.yMax - 8f)
        {
            Rect history = new Rect(cardX, y, cardWidth, Mathf.Min(96f, panel.yMax - y - 12f));
            DrawQuestionHistoryCard(history);
        }
    }

    private void DrawSeekerPointsCard(Rect card)
    {
        DrawPanelRect(card, CardBackground, BorderColor);
        GUI.Label(new Rect(card.x + 12f, card.y + 7f, card.width - 24f, 20f), "SEEKER POINTS", cardHeadingStyle);
        DrawMetricRow(card, card.y + 31f, "Available", questionTestOverride ? $"{SeekerPointsBalance()} · TEST BYPASS" : SeekerPointsBalance().ToString());
        DrawMetricRow(card, card.y + 53f, "Earned / spent", $"{SeekerPointsEarned()} / {seekerPointsSpent}");
        string cooldown = questionTestOverride ? "Test bypass" : (QuestionCooldownActive() ? FormatTime(QuestionCooldownRemaining()) : "READY");
        DrawMetricRow(card, card.y + 75f, "Cooldown", cooldown);
    }

    private void DrawCenterlineQuestionCard(Rect card)
    {
        const int cost = 0;
        bool usedUp = centerlineUses >= settings.CenterlineMaxUses;
        DrawQuestionCardBase(card, "CENTERLINE", cost, out bool available, usedUp ? "USED" : null);

        string line = centerlineVertical ? "X 17" : "Y 37";
        string answer = centerlineVertical
            ? (centerlineAnswerIndex == 0 ? "WEST" : "EAST")
            : (centerlineAnswerIndex == 0 ? "NORTH" : "SOUTH");

        float y = card.y + 47f;
        if (DrawCycleButton(new Rect(card.x + 12f, y, (card.width - 30f) * 0.5f, 29f), $"LINE · {line}"))
            centerlineVertical = !centerlineVertical;
        if (DrawCycleButton(new Rect(card.x + 18f + (card.width - 30f) * 0.5f, y, (card.width - 30f) * 0.5f, 29f), $"ANSWER · {answer}"))
            centerlineAnswerIndex = 1 - centerlineAnswerIndex;

        GUI.enabled = available;
        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = new Color(0.42f, 0.34f, 0.12f, 1f);
        if (GUI.Button(new Rect(card.x + 12f, card.y + 101f, card.width - 24f, 31f), usedUp ? "USED THIS MATCH" : "APPLY FREE ANSWER", compactButtonStyle))
        {
            ApplyQuestion(cost, $"Centerline {line} → {answer}",
                MapConstraint.Split(centerlineVertical ? 'x' : 'y', centerlineVertical ? 1700f : 3700f, centerlineAnswerIndex == 0));
            centerlineUses++;
        }
        GUI.backgroundColor = oldBackground;
        GUI.enabled = true;
    }

    private void DrawNearestTowerQuestionCard(Rect card)
    {
        int cost = settings.NearestTowerCost;
        DrawQuestionCardBase(card, "NEAREST TOWER", cost, out bool available);

        MapFeature tower = Towers[Mathf.Clamp(nearestTowerAnswerIndex, 0, Towers.Length - 1)];
        if (DrawCycleButton(new Rect(card.x + 12f, card.y + 47f, card.width - 24f, 29f), $"ANSWER · {tower.Name}"))
            nearestTowerAnswerIndex = (nearestTowerAnswerIndex + 1) % Towers.Length;

        GUI.enabled = available;
        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = new Color(0.42f, 0.34f, 0.12f, 1f);
        if (GUI.Button(new Rect(card.x + 12f, card.y + 80f, card.width - 24f, 29f), "APPLY ANSWER", compactButtonStyle))
            ApplyQuestion(cost, $"Nearest tower → {tower.Name}", MapConstraint.Nearest(tower.Name));
        GUI.backgroundColor = oldBackground;
        GUI.enabled = true;
    }

    private void DrawTowerRadiusQuestionCard(Rect card)
    {
        int radius = TowerRadiusOptions[Mathf.Clamp(towerRadiusOptionIndex, 0, TowerRadiusOptions.Length - 1)];
        int cost = TowerRadiusCost(towerRadiusOptionIndex);
        DrawQuestionCardBase(card, "TOWER RADIUS", cost, out bool available);

        MapFeature tower = Towers[Mathf.Clamp(towerRadiusTowerIndex, 0, Towers.Length - 1)];
        float half = (card.width - 30f) * 0.5f;
        if (DrawCycleButton(new Rect(card.x + 12f, card.y + 47f, half, 29f), $"TOWER · {tower.Name}"))
            towerRadiusTowerIndex = (towerRadiusTowerIndex + 1) % Towers.Length;
        if (DrawCycleButton(new Rect(card.x + 18f + half, card.y + 47f, half, 29f), $"RADIUS · {radius}"))
            towerRadiusOptionIndex = (towerRadiusOptionIndex + 1) % TowerRadiusOptions.Length;
        if (DrawCycleButton(new Rect(card.x + 12f, card.y + 80f, card.width - 24f, 29f), $"ANSWER · {(towerRadiusInside ? "INSIDE" : "OUTSIDE")}"))
            towerRadiusInside = !towerRadiusInside;

        GUI.enabled = available;
        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = new Color(0.42f, 0.34f, 0.12f, 1f);
        if (GUI.Button(new Rect(card.x + 12f, card.y + 113f, card.width - 24f, 29f), "APPLY ANSWER", compactButtonStyle))
            ApplyQuestion(cost, $"{tower.Name} tower · {radius}u → {(towerRadiusInside ? "Inside" : "Outside")}",
                MapConstraint.Radar(tower.Name, radius, towerRadiusInside));
        GUI.backgroundColor = oldBackground;
        GUI.enabled = true;
    }

    private void DrawQuestionCardBase(Rect card, string name, int cost, out bool available, string forcedState = null)
    {
        available = CanApplyQuestion(cost) && string.IsNullOrEmpty(forcedState);
        DrawPanelRect(card, CardBackground, new Color(0.34f, 0.30f, 0.17f, 1f));

        GUI.Label(new Rect(card.x + 12f, card.y + 7f, card.width - 150f, 20f), name, cardHeadingStyle);
        GUI.Label(new Rect(card.x + card.width - 136f, card.y + 7f, 124f, 20f),
            cost <= 0 ? "FREE" : $"COST · {cost} SP", metricValueStyle);

        string state;
        if (!string.IsNullOrEmpty(forcedState))
            state = forcedState;
        else if (questionTestOverride)
            state = "TEST OVERRIDE";
        else if (QuestionCooldownActive())
            state = $"COOLDOWN {FormatTime(QuestionCooldownRemaining())}";
        else if (SeekerPointsBalance() < cost)
            state = $"NEED {cost - SeekerPointsBalance()} SP";
        else
            state = "READY";

        Color old = GUI.color;
        GUI.color = available ? AccentGreen : MutedText;
        GUI.Label(new Rect(card.x + 12f, card.y + 27f, card.width - 24f, 17f), state, versionStyle);
        GUI.color = old;
    }

    private bool DrawCycleButton(Rect rect, string label)
    {
        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = new Color(0.11f, 0.14f, 0.17f, 1f);
        bool clicked = GUI.Button(rect, label, compactButtonStyle);
        GUI.backgroundColor = oldBackground;
        return clicked;
    }

    private void DrawQuestionHistoryCard(Rect card)
    {
        DrawPanelRect(card, CardBackground, BorderColor);
        GUI.Label(new Rect(card.x + 12f, card.y + 7f, card.width - 24f, 20f), "RECENT ANSWERS", cardHeadingStyle);
        if (questionHistory.Count == 0)
        {
            GUI.Label(new Rect(card.x + 12f, card.y + 32f, card.width - 24f, card.height - 40f), "No questions answered yet.", emptyStateStyle);
            return;
        }

        int count = Mathf.Min(3, questionHistory.Count);
        for (int i = 0; i < count; i++)
        {
            string item = questionHistory[questionHistory.Count - 1 - i];
            GUI.Label(new Rect(card.x + 12f, card.y + 31f + i * 19f, card.width - 24f, 18f), item, emptyStateStyle);
        }
    }

    private bool QuestionCooldownActive()
    {
        return !questionTestOverride && questionCooldownUntil > matchElapsedSeconds;
    }

    private float QuestionCooldownRemaining()
    {
        return Mathf.Max(0f, questionCooldownUntil - matchElapsedSeconds);
    }

    private bool CanApplyQuestion(int cost)
    {
        if (selectedRole != PlayerRole.Seeker)
            return false;
        if (questionTestOverride)
            return true;
        if (QuestionCooldownActive())
            return false;
        return SeekerPointsBalance() >= cost;
    }

    private void ApplyQuestion(int cost, string description, MapConstraint constraint)
    {
        if (!questionTestOverride)
        {
            if (SeekerPointsBalance() < cost || QuestionCooldownActive())
                return;
            seekerPointsSpent += cost;
            questionCooldownUntil = matchElapsedSeconds + settings.QuestionCooldownSeconds;
        }

        if (constraint != null)
        {
            constraints.Add(constraint);
            constraintMaskDirty = true;
        }

        questionHistory.Add($"{FormatTime(matchElapsedSeconds)} · {description}");
        if (questionHistory.Count > 20)
            questionHistory.RemoveAt(0);
        CoreEntry.Logger?.LogInfo($"Question applied: {description}. Cost {cost} SP{(questionTestOverride ? " (test bypass)" : string.Empty)}.");
    }

    private int SeekerPointsEarned()
    {
        return Mathf.FloorToInt(matchElapsedSeconds / 60f) * settings.PointsPerMinute;
    }

    private int SeekerPointsBalance()
    {
        return Mathf.Max(0, SeekerPointsEarned() - seekerPointsSpent);
    }

    private int TowerRadiusCost(int optionIndex)
    {
        switch (Mathf.Clamp(optionIndex, 0, 3))
        {
            case 0: return settings.TowerRadius500Cost;
            case 1: return settings.TowerRadius400Cost;
            case 2: return settings.TowerRadius300Cost;
            default: return settings.TowerRadius250Cost;
        }
    }

    private int LowestTowerRadiusCost()
    {
        return Mathf.Min(
            Mathf.Min(settings.TowerRadius500Cost, settings.TowerRadius400Cost),
            Mathf.Min(settings.TowerRadius300Cost, settings.TowerRadius250Cost));
    }

    private string NextQuestionStatus()
    {
        if (questionTestOverride)
            return "Question test override is active.";

        if (QuestionCooldownActive())
            return $"Question cooldown · {FormatTime(QuestionCooldownRemaining())} remaining.";

        int balance = SeekerPointsBalance();
        if (centerlineUses < settings.CenterlineMaxUses)
            return $"Centerline is free · {settings.CenterlineMaxUses - centerlineUses} use(s) remaining.";

        return $"{balance} SP available · Nearest Tower {settings.NearestTowerCost} SP · Tower Radius from {LowestTowerRadiusCost()} SP.";
    }

    private void UpdateGameplayNotifications()
    {
        if (!initialized)
            return;

        bool cooldownActive = QuestionCooldownActive();
        if (!questionTestOverride && previousCooldownActive && !cooldownActive)
            Notify("QUESTION COOLDOWN ENDED", "Questions are available again.", AccentGreen, NotificationTone.Normal, PlayerRole.Seeker);
        previousCooldownActive = questionTestOverride ? false : cooldownActive;

        if (selectedRole != PlayerRole.Seeker || questionTestOverride || !matchRunning)
        {
            previousCanAffordNearest = false;
            previousCanAffordRadius = false;
            return;
        }

        int balance = SeekerPointsBalance();
        bool canNearest = balance >= settings.NearestTowerCost;
        bool canRadius = balance >= LowestTowerRadiusCost();

        string newlyAffordable = string.Empty;
        if (canNearest && !previousCanAffordNearest)
            newlyAffordable = "Nearest Tower";
        if (canRadius && !previousCanAffordRadius)
            newlyAffordable = string.IsNullOrEmpty(newlyAffordable) ? "Tower Radius" : "Nearest Tower + Tower Radius";

        if (!string.IsNullOrEmpty(newlyAffordable))
            Notify("QUESTION AFFORDABLE", $"{newlyAffordable} can now be afforded.", AccentYellow, NotificationTone.Soft, PlayerRole.Seeker);

        previousCanAffordNearest = canNearest;
        previousCanAffordRadius = canRadius;
    }'''
replace_between('    private void DrawQuestionsPanel(Rect panel)\n', '    private void DrawNavigationPanel(Rect panel)\n', questions_block, 'questions block')

more_block = r'''    private void DrawMorePanel(Rect panel)
    {
        GUI.Label(new Rect(panel.x + 14f, panel.y + 10f, panel.width - 28f, 21f), "MORE", panelHeadingStyle);
        GUI.Label(new Rect(panel.x + 14f, panel.y + 29f, panel.width - 28f, 18f), "Match settings, HUD, audio, and testing", panelSubtitleStyle);

        float cardX = panel.x + 12f;
        float cardWidth = panel.width - 24f;
        float y = panel.y + 57f;

        Rect gameplay = new Rect(cardX, y, cardWidth, 118f);
        DrawPanelRect(gameplay, CardBackground, BorderColor);
        GUI.Label(new Rect(gameplay.x + 12f, gameplay.y + 7f, gameplay.width - 24f, 20f), "GAMEPLAY", cardHeadingStyle);

        int oldPoints = settings.PointsPerMinute;
        settings.PointsPerMinute = DrawIntSettingRow(gameplay, gameplay.y + 31f, "Seeker points / min", settings.PointsPerMinute, 0, 10, 1, string.Empty);
        if (settings.PointsPerMinute != oldPoints) SaveSettings();

        int oldCooldown = Mathf.RoundToInt(settings.QuestionCooldownSeconds);
        int newCooldown = DrawIntSettingRow(gameplay, gameplay.y + 53f, "Question cooldown", oldCooldown, 0, 900, 30, "s");
        if (newCooldown != oldCooldown)
        {
            settings.QuestionCooldownSeconds = newCooldown;
            SaveSettings();
        }

        int oldMission = Mathf.RoundToInt(settings.MissionTargetDistance);
        int newMission = DrawIntSettingRow(gameplay, gameplay.y + 75f, "Mission distance", oldMission, 25, 1000, 25, "u");
        if (newMission != oldMission)
        {
            settings.MissionTargetDistance = newMission;
            SaveSettings();
        }
        y += gameplay.height + 8f;

        Rect questions = new Rect(cardX, y, cardWidth, 168f);
        DrawPanelRect(questions, CardBackground, BorderColor);
        GUI.Label(new Rect(questions.x + 12f, questions.y + 7f, questions.width - 24f, 20f), "QUESTION RULES", cardHeadingStyle);

        int oldCenterUses = settings.CenterlineMaxUses;
        settings.CenterlineMaxUses = DrawIntSettingRow(questions, questions.y + 31f, "Centerline uses", settings.CenterlineMaxUses, 0, 5, 1, string.Empty);
        if (settings.CenterlineMaxUses != oldCenterUses) SaveSettings();

        int oldNearest = settings.NearestTowerCost;
        settings.NearestTowerCost = DrawIntSettingRow(questions, questions.y + 53f, "Nearest Tower cost", settings.NearestTowerCost, 0, 30, 1, "SP");
        if (settings.NearestTowerCost != oldNearest) SaveSettings();

        int old500 = settings.TowerRadius500Cost;
        settings.TowerRadius500Cost = DrawIntSettingRow(questions, questions.y + 75f, "Radius 500 cost", settings.TowerRadius500Cost, 0, 30, 1, "SP");
        if (settings.TowerRadius500Cost != old500) SaveSettings();

        int old400 = settings.TowerRadius400Cost;
        settings.TowerRadius400Cost = DrawIntSettingRow(questions, questions.y + 97f, "Radius 400 cost", settings.TowerRadius400Cost, 0, 30, 1, "SP");
        if (settings.TowerRadius400Cost != old400) SaveSettings();

        int old300 = settings.TowerRadius300Cost;
        settings.TowerRadius300Cost = DrawIntSettingRow(questions, questions.y + 119f, "Radius 300 cost", settings.TowerRadius300Cost, 0, 30, 1, "SP");
        if (settings.TowerRadius300Cost != old300) SaveSettings();

        int old250 = settings.TowerRadius250Cost;
        settings.TowerRadius250Cost = DrawIntSettingRow(questions, questions.y + 141f, "Radius 250 cost", settings.TowerRadius250Cost, 0, 30, 1, "SP");
        if (settings.TowerRadius250Cost != old250) SaveSettings();
        y += questions.height + 8f;

        Rect hud = new Rect(cardX, y, cardWidth, 118f);
        DrawPanelRect(hud, CardBackground, BorderColor);
        GUI.Label(new Rect(hud.x + 12f, hud.y + 7f, hud.width - 24f, 20f), "PASSIVE HUD", cardHeadingStyle);

        bool oldMini = settings.MiniMapEnabled;
        settings.MiniMapEnabled = DrawToggleSettingRow(hud, hud.y + 31f, "North-up mini-map", settings.MiniMapEnabled);
        if (settings.MiniMapEnabled != oldMini) SaveSettings();

        bool oldNav = settings.NavHudEnabled;
        settings.NavHudEnabled = DrawToggleSettingRow(hud, hud.y + 53f, "Coordinates + compass", settings.NavHudEnabled);
        if (settings.NavHudEnabled != oldNav) SaveSettings();

        bool oldMissionHud = settings.MissionHudEnabled;
        settings.MissionHudEnabled = DrawToggleSettingRow(hud, hud.y + 75f, "Mission HUD", settings.MissionHudEnabled);
        if (settings.MissionHudEnabled != oldMissionHud) SaveSettings();

        bool oldPopups = settings.NotificationsEnabled;
        settings.NotificationsEnabled = DrawToggleSettingRow(hud, hud.y + 97f, "Notification popups", settings.NotificationsEnabled);
        if (settings.NotificationsEnabled != oldPopups) SaveSettings();
        y += hud.height + 8f;

        Rect audio = new Rect(cardX, y, cardWidth, 96f);
        DrawPanelRect(audio, CardBackground, BorderColor);
        GUI.Label(new Rect(audio.x + 12f, audio.y + 7f, audio.width - 24f, 20f), "AUDIO", cardHeadingStyle);

        bool oldSounds = settings.SoundsEnabled;
        settings.SoundsEnabled = DrawToggleSettingRow(audio, audio.y + 31f, "Sounds", settings.SoundsEnabled);
        if (settings.SoundsEnabled != oldSounds) SaveSettings();

        bool oldNotifSounds = settings.NotificationSoundsEnabled;
        settings.NotificationSoundsEnabled = DrawToggleSettingRow(audio, audio.y + 53f, "Notification sounds", settings.NotificationSoundsEnabled);
        if (settings.NotificationSoundsEnabled != oldNotifSounds) SaveSettings();

        int oldVolume = Mathf.RoundToInt(settings.SoundVolume * 100f);
        int newVolume = DrawIntSettingRow(audio, audio.y + 75f, "Volume", oldVolume, 0, 100, 10, "%");
        if (newVolume != oldVolume)
        {
            settings.SoundVolume = newVolume / 100f;
            SaveSettings();
        }
        y += audio.height + 8f;

        Rect testing = new Rect(cardX, y, cardWidth, 104f);
        DrawPanelRect(testing, CardBackground, BorderColor);
        GUI.Label(new Rect(testing.x + 12f, testing.y + 7f, testing.width - 24f, 20f), "QUESTION TESTING", cardHeadingStyle);
        GUI.Label(new Rect(testing.x + 12f, testing.y + 30f, testing.width - 24f, 35f),
            "Bypasses point costs and cooldowns. Centerline use limits remain enforced.", emptyStateStyle);

        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = questionTestOverride
            ? new Color(0.20f, 0.43f, 0.29f, 1f)
            : new Color(0.16f, 0.19f, 0.23f, 1f);
        if (GUI.Button(new Rect(testing.x + 12f, testing.y + 67f, testing.width - 24f, 29f),
            questionTestOverride ? "TEST OVERRIDE · ON" : "TEST OVERRIDE · OFF", compactButtonStyle))
            questionTestOverride = !questionTestOverride;
        GUI.backgroundColor = oldBackground;
    }

    private int DrawIntSettingRow(Rect card, float y, string label, int value, int min, int max, int step, string suffix)
    {
        GUI.Label(new Rect(card.x + 12f, y, card.width * 0.55f, 19f), label, metricLabelStyle);

        float right = card.xMax - 12f;
        if (GUI.Button(new Rect(right - 102f, y - 1f, 25f, 20f), "−", compactButtonStyle))
            value = Mathf.Clamp(value - step, min, max);

        GUI.Label(new Rect(right - 75f, y, 48f, 19f), string.IsNullOrEmpty(suffix) ? value.ToString() : $"{value}{suffix}", metricValueStyle);

        if (GUI.Button(new Rect(right - 25f, y - 1f, 25f, 20f), "+", compactButtonStyle))
            value = Mathf.Clamp(value + step, min, max);

        return value;
    }

    private bool DrawToggleSettingRow(Rect card, float y, string label, bool value)
    {
        GUI.Label(new Rect(card.x + 12f, y, card.width * 0.62f, 19f), label, metricLabelStyle);

        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = value ? new Color(0.15f, 0.24f, 0.19f, 1f) : new Color(0.16f, 0.19f, 0.23f, 1f);
        if (GUI.Button(new Rect(card.xMax - 82f, y - 2f, 70f, 22f), value ? "ON" : "OFF", compactButtonStyle))
            value = !value;
        GUI.backgroundColor = oldBackground;
        return value;
    }'''
replace_between('    private void DrawMorePanel(Rect panel)\n', '    private void DrawToolDock(Rect dock)\n', more_block, 'More/settings block')

support_methods = r'''
    private void EnsureInitialized()
    {
        if (initialized)
            return;

        initialized = true;
        LoadSettings();
        TryInitializeAudio();
    }

    private void LoadSettings()
    {
        try
        {
            string runtimeDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location) ?? ".";
            settingsPath = Path.Combine(runtimeDir, "settings.json");

            if (File.Exists(settingsPath))
            {
                LocalSettings loaded = JsonSerializer.Deserialize<LocalSettings>(File.ReadAllText(settingsPath));
                if (loaded != null)
                    settings = loaded;
            }

            settings.Clamp();
            SaveSettings();
            CoreEntry.Logger?.LogInfo($"Hide + Seek settings loaded from {settingsPath}");
        }
        catch (Exception ex)
        {
            settings = new LocalSettings();
            CoreEntry.Logger?.LogWarning($"Could not load Hide + Seek settings; using defaults. {ex.Message}");
        }
    }

    private void SaveSettings()
    {
        if (string.IsNullOrEmpty(settingsPath))
            return;

        try
        {
            settings.Clamp();
            var options = new JsonSerializerOptions { WriteIndented = true };
            File.WriteAllText(settingsPath, JsonSerializer.Serialize(settings, options));
        }
        catch (Exception ex)
        {
            CoreEntry.Logger?.LogWarning($"Could not save Hide + Seek settings: {ex.Message}");
        }
    }

    private void TryInitializeAudio()
    {
        try
        {
            uiAudioSource = gameObject.AddComponent<AudioSource>();
            uiAudioSource.playOnAwake = false;
            uiAudioSource.loop = false;
            uiAudioSource.spatialBlend = 0f;

            softToneClip = CreateToneClip("BWHS Soft", 620f, 0.08f);
            normalToneClip = CreateToneClip("BWHS Normal", 760f, 0.14f);
            importantToneClip = CreateToneClip("BWHS Important", 880f, 0.22f);
        }
        catch (Exception ex)
        {
            CoreEntry.Logger?.LogWarning($"Hide + Seek notification audio unavailable: {ex.Message}");
            uiAudioSource = null;
        }
    }

    private static AudioClip CreateToneClip(string name, float frequency, float duration)
    {
        const int sampleRate = 44100;
        int sampleCount = Mathf.Max(1, Mathf.RoundToInt(sampleRate * duration));
        AudioClip clip = AudioClip.Create(name, sampleCount, 1, sampleRate, false);
        var data = new Il2CppStructArray<float>(sampleCount);

        for (int i = 0; i < sampleCount; i++)
        {
            float t = i / (float)sampleRate;
            float attack = Mathf.Clamp01(i / (sampleRate * 0.008f));
            float release = Mathf.Clamp01((sampleCount - 1 - i) / (sampleRate * 0.025f));
            float envelope = Mathf.Min(attack, release);
            data[i] = Mathf.Sin(2f * Mathf.PI * frequency * t) * 0.18f * envelope;
        }

        clip.SetData(data, 0);
        return clip;
    }

    private void Notify(string title, string message, Color accent, NotificationTone tone, PlayerRole? role = null)
    {
        if (role.HasValue && selectedRole != role.Value)
            return;

        if (settings.NotificationsEnabled)
        {
            if (notifications.Count >= 5)
                notifications.RemoveAt(0);
            notifications.Add(new UiNotification(title, message, accent, Time.unscaledTime, 4.5f));
        }

        if (settings.SoundsEnabled && settings.NotificationSoundsEnabled)
            PlayNotificationTone(tone);
    }

    private void PlayNotificationTone(NotificationTone tone)
    {
        if (uiAudioSource == null)
            return;

        AudioClip clip = tone == NotificationTone.Important
            ? importantToneClip
            : tone == NotificationTone.Normal ? normalToneClip : softToneClip;

        if (clip != null)
            uiAudioSource.PlayOneShot(clip, settings.SoundVolume);
    }

    private void DrawNotifications()
    {
        float now = Time.unscaledTime;
        for (int i = notifications.Count - 1; i >= 0; i--)
        {
            if (now - notifications[i].CreatedAt >= notifications[i].Duration)
                notifications.RemoveAt(i);
        }

        if (!settings.NotificationsEnabled || notifications.Count == 0)
            return;

        int visible = Mathf.Min(3, notifications.Count);
        float width = 340f;
        float x = (Screen.width - width) * 0.5f;
        float y = overlayOpen ? TopBarHeight + 12f : 14f;

        for (int i = 0; i < visible; i++)
        {
            UiNotification notification = notifications[notifications.Count - visible + i];
            Rect rect = new Rect(x, y + i * 70f, width, 60f);
            DrawPanelRect(rect, new Color(0.055f, 0.068f, 0.088f, 0.96f), notification.Accent);
            GUI.Label(new Rect(rect.x + 12f, rect.y + 7f, rect.width - 24f, 18f), notification.Title, cardHeadingStyle);
            GUI.Label(new Rect(rect.x + 12f, rect.y + 29f, rect.width - 24f, 24f), notification.Message, emptyStateStyle);
        }
    }

'''
once('    private void DrawToolDock(Rect dock)\n', support_methods + '    private void DrawToolDock(Rect dock)\n', 'support methods insert')

once(
'''        if (constraintMaskTexture != null)
        {
            UnityEngine.Object.Destroy(constraintMaskTexture);
            constraintMaskTexture = null;
        }
''',
'''        if (constraintMaskTexture != null)
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
''',
'audio destroy')

types = r'''    private enum NotificationTone
    {
        Soft,
        Normal,
        Important
    }

    public sealed class LocalSettings
    {
        public int PointsPerMinute { get; set; } = 1;
        public float QuestionCooldownSeconds { get; set; } = 300f;
        public int CenterlineMaxUses { get; set; } = 1;
        public int NearestTowerCost { get; set; } = 5;
        public int TowerRadius500Cost { get; set; } = 4;
        public int TowerRadius400Cost { get; set; } = 5;
        public int TowerRadius300Cost { get; set; } = 7;
        public int TowerRadius250Cost { get; set; } = 9;
        public float MissionTargetDistance { get; set; } = 200f;
        public bool MiniMapEnabled { get; set; } = true;
        public bool NavHudEnabled { get; set; } = true;
        public bool MissionHudEnabled { get; set; } = true;
        public bool NotificationsEnabled { get; set; } = true;
        public bool SoundsEnabled { get; set; } = true;
        public bool NotificationSoundsEnabled { get; set; } = true;
        public float SoundVolume { get; set; } = 0.7f;

        public void Clamp()
        {
            PointsPerMinute = Mathf.Clamp(PointsPerMinute, 0, 10);
            QuestionCooldownSeconds = Mathf.Clamp(QuestionCooldownSeconds, 0f, 900f);
            CenterlineMaxUses = Mathf.Clamp(CenterlineMaxUses, 0, 5);
            NearestTowerCost = Mathf.Clamp(NearestTowerCost, 0, 30);
            TowerRadius500Cost = Mathf.Clamp(TowerRadius500Cost, 0, 30);
            TowerRadius400Cost = Mathf.Clamp(TowerRadius400Cost, 0, 30);
            TowerRadius300Cost = Mathf.Clamp(TowerRadius300Cost, 0, 30);
            TowerRadius250Cost = Mathf.Clamp(TowerRadius250Cost, 0, 30);
            MissionTargetDistance = Mathf.Clamp(MissionTargetDistance, 25f, 1000f);
            SoundVolume = Mathf.Clamp01(SoundVolume);
        }
    }

    private sealed class UiNotification
    {
        public readonly string Title;
        public readonly string Message;
        public readonly Color Accent;
        public readonly float CreatedAt;
        public readonly float Duration;

        public UiNotification(string title, string message, Color accent, float createdAt, float duration)
        {
            Title = title;
            Message = message;
            Accent = accent;
            CreatedAt = createdAt;
            Duration = duration;
        }
    }

'''
once('    private sealed class MapFeature\n', types + '    private sealed class MapFeature\n', 'support types')

core_path.write_text(s, encoding='utf-8')
proj_path.write_text(p, encoding='utf-8')

print('Applied Core 0.0.19 role-aware settings/HUD/audio foundation batch.')
