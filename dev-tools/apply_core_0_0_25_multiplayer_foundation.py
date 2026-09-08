from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "in-game-mod" / "core" / "CoreEntry.cs"
CSPROJ = ROOT / "in-game-mod" / "core" / "BigWalkHideSeek.Core.csproj"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


text = CORE.read_text(encoding="utf-8")

# Version bump for all user-visible/runtime 0.0.24 strings in the monolithic Core file.
if "0.0.24" not in text:
    raise RuntimeError("CoreEntry.cs does not contain expected 0.0.24 version strings")
text = text.replace("0.0.24", "0.0.25")

text = replace_once(
    text,
    """    private bool missionActive;\n    private bool missionCompleted;\n    private bool missionReady;\n    private Vector2 missionStart;\n    private float missionDistance;\n""",
    """    private bool missionActive;\n    private bool missionCompleted;\n    private bool missionReady;\n    private Vector2 missionStart;\n    private float missionDistance;\n\n    private FirebaseRoomClient roomClient;\n    private string roomDisplayName = \"Player\";\n    private string roomJoinCode = string.Empty;\n    private bool roomTextEditing;\n""",
    "multiplayer fields",
)

text = replace_once(
    text,
    """        EnsureInitialized();\n        UpdateMatchTimer();\n""",
    """        EnsureInitialized();\n        UpdateMultiplayer();\n        UpdateMatchTimer();\n""",
    "Update multiplayer hook",
)

text = replace_once(
    text,
    """        if (Input.GetKeyDown(KeyCode.M) || Input.GetKeyDown(KeyCode.F7))\n""",
    """        if ((!roomTextEditing && Input.GetKeyDown(KeyCode.M)) || Input.GetKeyDown(KeyCode.F7))\n""",
    "M hotkey text-entry guard",
)

multiplayer_methods = r'''
    private void UpdateMultiplayer()
    {
        if (roomClient == null)
            return;

        roomClient.Tick();
        if (!roomClient.IsConnected)
            return;

        PlayerRole syncedRole = string.Equals(roomClient.LocalRole, "hider", StringComparison.OrdinalIgnoreCase)
            ? PlayerRole.Hider
            : PlayerRole.Seeker;
        if (selectedRole != syncedRole)
            ApplySyncedRole(syncedRole);

        if (!roomClient.IsHost)
        {
            FirebaseRoomClient.RoomSnapshot room = roomClient.Snapshot;
            if (room != null)
            {
                matchRunning = room.MatchRunning;
                matchElapsedSeconds = (float)roomClient.GetSyncedMatchSeconds();
                matchLastTick = Time.unscaledTime;
            }
        }
    }

    private void PushMultiplayerMatchState()
    {
        if (roomClient != null && roomClient.IsConnected && roomClient.IsHost)
            roomClient.BeginPushMatchState(matchRunning, matchElapsedSeconds);
    }

    private void ApplySyncedRole(PlayerRole role)
    {
        selectedRole = role;
        if (selectedRole == PlayerRole.Hider && activeTab == UiTab.Questions)
            activeTab = UiTab.Game;

        previousCanAffordNearest = false;
        previousCanAffordRadius = false;
    }

'''
text = replace_once(
    text,
    """    private void UpdateMatchTimer()\n    {\n        float now = Time.unscaledTime;\n""",
    multiplayer_methods + """    private void UpdateMatchTimer()\n    {\n        if (roomClient != null && roomClient.IsConnected && !roomClient.IsHost)\n        {\n            matchLastTick = Time.unscaledTime;\n            return;\n        }\n\n        float now = Time.unscaledTime;\n""",
    "multiplayer methods + client timer authority",
)

text = replace_once(
    text,
    """    private void StartOrResumeMatch()\n    {\n        bool resuming = matchElapsedSeconds > 0.01f;\n""",
    """    private void StartOrResumeMatch()\n    {\n        if (roomClient != null && roomClient.IsConnected && !roomClient.IsHost)\n        {\n            Notify(\"HOST CONTROLS TIMER\", \"Only the room host can start or resume the shared match timer.\", AccentYellow, NotificationTone.Soft);\n            return;\n        }\n\n        bool resuming = matchElapsedSeconds > 0.01f;\n""",
    "host start guard",
)

text = replace_once(
    text,
    """        CoreEntry.Logger?.LogInfo(resuming ? \"Hide + Seek match resumed.\" : \"Hide + Seek match started.\");\n    }\n\n    private void PauseMatch()\n""",
    """        CoreEntry.Logger?.LogInfo(resuming ? \"Hide + Seek match resumed.\" : \"Hide + Seek match started.\");\n        PushMultiplayerMatchState();\n    }\n\n    private void PauseMatch()\n""",
    "start match sync push",
)

text = replace_once(
    text,
    """    private void PauseMatch()\n    {\n        if (!matchRunning)\n            return;\n""",
    """    private void PauseMatch()\n    {\n        if (roomClient != null && roomClient.IsConnected && !roomClient.IsHost)\n        {\n            Notify(\"HOST CONTROLS TIMER\", \"Only the room host can pause the shared match timer.\", AccentYellow, NotificationTone.Soft);\n            return;\n        }\n\n        if (!matchRunning)\n            return;\n""",
    "host pause guard",
)

text = replace_once(
    text,
    """        CoreEntry.Logger?.LogInfo(\"Hide + Seek match paused.\");\n    }\n\n    private void ResetMatchState()\n""",
    """        CoreEntry.Logger?.LogInfo(\"Hide + Seek match paused.\");\n        PushMultiplayerMatchState();\n    }\n\n    private void ResetMatchState()\n""",
    "pause match sync push",
)

text = replace_once(
    text,
    """    private void ResetMatchState()\n    {\n        matchRunning = false;\n""",
    """    private void ResetMatchState()\n    {\n        if (roomClient != null && roomClient.IsConnected && !roomClient.IsHost)\n        {\n            Notify(\"HOST CONTROLS TIMER\", \"Only the room host can reset the shared match.\", AccentYellow, NotificationTone.Soft);\n            return;\n        }\n\n        matchRunning = false;\n""",
    "host reset guard",
)

text = replace_once(
    text,
    """        CoreEntry.Logger?.LogInfo(\"Hide + Seek gameplay state reset.\");\n    }\n\n    private void SetOverlayOpen(bool open)\n""",
    """        CoreEntry.Logger?.LogInfo(\"Hide + Seek gameplay state reset.\");\n        PushMultiplayerMatchState();\n    }\n\n    private void SetOverlayOpen(bool open)\n""",
    "reset match sync push",
)

text = replace_once(
    text,
    """        EnsureInitialized();\n        EnsureStyles();\n        GUI.depth = -10000;\n""",
    """        EnsureInitialized();\n        EnsureStyles();\n        roomTextEditing = false;\n        GUI.depth = -10000;\n""",
    "room text focus reset",
)

text = replace_once(
    text,
    """        float tabX = 150f;\n        DrawTopTab(ref tabX, \"GAME\", UiTab.Game, 64f);\n        if (selectedRole == PlayerRole.Seeker)\n""",
    """        float tabX = 150f;\n        DrawTopTab(ref tabX, \"GAME\", UiTab.Game, 64f);\n        DrawTopTab(ref tabX, \"ROOM\", UiTab.Room, 64f);\n        if (selectedRole == PlayerRole.Seeker)\n""",
    "ROOM top tab",
)

old_top_controls = r'''    private void DrawTopMatchControls(float rightEdge)
    {
        string time = FormatTime(matchElapsedSeconds);
        Rect timerRect = new Rect(rightEdge - 236f, 5f, 74f, 27f);
        GUI.Label(timerRect, time, bigNumberStyle);
        GUI.Label(new Rect(timerRect.x - 12f, 29f, 86f, 22f), matchRunning ? "RUNNING" : (matchElapsedSeconds > 0f ? "PAUSED" : "NOT STARTED"), timerStatusStyle);

        float x = rightEdge - 154f;
        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = new Color(0.42f, 0.34f, 0.12f, 1f);
        if (!matchRunning && GUI.Button(new Rect(x, 13f, 54f, 30f), matchElapsedSeconds > 0f ? "RESUME" : "START", compactButtonStyle))
            StartOrResumeMatch();
        if (matchRunning)
        {
            GUI.backgroundColor = new Color(0.16f, 0.19f, 0.23f, 1f);
            if (GUI.Button(new Rect(x, 13f, 54f, 30f), "PAUSE", compactButtonStyle))
                PauseMatch();
        }
        GUI.backgroundColor = new Color(0.28f, 0.13f, 0.15f, 1f);
        if (GUI.Button(new Rect(x + 60f, 13f, 56f, 30f), "RESET", compactButtonStyle))
            ResetMatchState();
        GUI.backgroundColor = oldBackground;
    }
'''
new_top_controls = r'''    private void DrawTopMatchControls(float rightEdge)
    {
        string time = FormatTime(matchElapsedSeconds);
        Rect timerRect = new Rect(rightEdge - 236f, 5f, 74f, 27f);
        GUI.Label(timerRect, time, bigNumberStyle);
        GUI.Label(new Rect(timerRect.x - 12f, 29f, 86f, 22f), matchRunning ? "RUNNING" : (matchElapsedSeconds > 0f ? "PAUSED" : "NOT STARTED"), timerStatusStyle);

        bool previousEnabled = GUI.enabled;
        bool canControlMatch = roomClient == null || !roomClient.IsConnected || roomClient.IsHost;
        GUI.enabled = previousEnabled && canControlMatch;

        float x = rightEdge - 154f;
        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = new Color(0.42f, 0.34f, 0.12f, 1f);
        if (!matchRunning && GUI.Button(new Rect(x, 13f, 54f, 30f), matchElapsedSeconds > 0f ? "RESUME" : "START", compactButtonStyle))
            StartOrResumeMatch();
        if (matchRunning)
        {
            GUI.backgroundColor = new Color(0.16f, 0.19f, 0.23f, 1f);
            if (GUI.Button(new Rect(x, 13f, 54f, 30f), "PAUSE", compactButtonStyle))
                PauseMatch();
        }
        GUI.backgroundColor = new Color(0.28f, 0.13f, 0.15f, 1f);
        if (GUI.Button(new Rect(x + 60f, 13f, 56f, 30f), "RESET", compactButtonStyle))
            ResetMatchState();
        GUI.backgroundColor = oldBackground;
        GUI.enabled = previousEnabled;
    }
'''
text = replace_once(text, old_top_controls, new_top_controls, "host-only top timer controls")

text = replace_once(
    text,
    """            case UiTab.Questions:\n                DrawQuestionsPanel(panel);\n                break;\n            case UiTab.Map:\n""",
    """            case UiTab.Questions:\n                DrawQuestionsPanel(panel);\n                break;\n            case UiTab.Room:\n                DrawRoomPanel(panel);\n                break;\n            case UiTab.Map:\n""",
    "ROOM sidebar switch",
)

old_set_role = r'''    private void SetRole(PlayerRole role)
    {
        if (selectedRole == role)
            return;

        selectedRole = role;
        if (selectedRole == PlayerRole.Hider && activeTab == UiTab.Questions)
            activeTab = UiTab.Game;

        previousCanAffordNearest = false;
        previousCanAffordRadius = false;
    }
'''
new_set_role = r'''    private void SetRole(PlayerRole role)
    {
        if (selectedRole == role)
            return;

        ApplySyncedRole(role);
        if (roomClient != null && roomClient.IsConnected)
            roomClient.BeginChangeRole(role == PlayerRole.Hider ? "hider" : "seeker");
    }
'''
text = replace_once(text, old_set_role, new_set_role, "role sync hook")

room_panel = r'''
    private void DrawRoomPanel(Rect panel)
    {
        GUI.Label(new Rect(panel.x + 14f, panel.y + 10f, panel.width - 28f, 21f), "MULTIPLAYER", panelHeadingStyle);
        GUI.Label(new Rect(panel.x + 14f, panel.y + 29f, panel.width - 28f, 18f), "Native Hide + Seek room synchronization", panelSubtitleStyle);

        float cardX = panel.x + 12f;
        float cardWidth = panel.width - 24f;
        float y = panel.y + 57f;

        if (roomClient == null)
        {
            Rect unavailable = new Rect(cardX, y, cardWidth, 110f);
            DrawPanelRect(unavailable, CardBackground, BorderColor);
            GUI.Label(new Rect(unavailable.x + 12f, unavailable.y + 9f, unavailable.width - 24f, 20f), "ROOM SERVICE", cardHeadingStyle);
            GUI.Label(new Rect(unavailable.x + 12f, unavailable.y + 38f, unavailable.width - 24f, 54f), "Room service is still initializing.", emptyStateStyle);
            return;
        }

        if (!roomClient.IsConnected)
        {
            Rect connect = new Rect(cardX, y, cardWidth, 268f);
            DrawPanelRect(connect, CardBackground, BorderColor);
            GUI.Label(new Rect(connect.x + 12f, connect.y + 8f, connect.width - 24f, 20f), "CREATE OR JOIN", cardHeadingStyle);
            GUI.Label(new Rect(connect.x + 12f, connect.y + 30f, connect.width - 24f, 32f),
                "Everyone uses the same six-character H+S room code. The room host controls the shared timer.", emptyStateStyle);

            GUI.Label(new Rect(connect.x + 12f, connect.y + 70f, 90f, 19f), "DISPLAY NAME", metricLabelStyle);
            GUI.SetNextControlName("BWHS_ROOM_NAME");
            roomDisplayName = GUI.TextField(new Rect(connect.x + 118f, connect.y + 67f, connect.width - 130f, 25f), roomDisplayName ?? string.Empty, 28);

            GUI.Label(new Rect(connect.x + 12f, connect.y + 103f, 90f, 19f), "YOUR ROLE", metricLabelStyle);
            if (DrawRoleButton(new Rect(connect.x + 118f, connect.y + 99f, 94f, 29f), "SEEKER", PlayerRole.Seeker))
                SetRole(PlayerRole.Seeker);
            if (DrawRoleButton(new Rect(connect.x + 218f, connect.y + 99f, 94f, 29f), "HIDER", PlayerRole.Hider))
                SetRole(PlayerRole.Hider);

            bool oldEnabled = GUI.enabled;
            GUI.enabled = oldEnabled && !roomClient.IsBusy;
            Color oldBackground = GUI.backgroundColor;
            GUI.backgroundColor = new Color(0.20f, 0.43f, 0.29f, 1f);
            if (GUI.Button(new Rect(connect.x + 12f, connect.y + 140f, connect.width - 24f, 34f), "CREATE ROOM", compactButtonStyle))
            {
                roomDisplayName = FirebaseRoomClient.SanitizeName(roomDisplayName);
                settings.MultiplayerName = roomDisplayName;
                SaveSettings();
                roomClient.BeginCreate(roomDisplayName, selectedRole == PlayerRole.Hider ? "hider" : "seeker");
            }

            GUI.Label(new Rect(connect.x + 12f, connect.y + 187f, 90f, 19f), "ROOM CODE", metricLabelStyle);
            GUI.SetNextControlName("BWHS_ROOM_CODE");
            roomJoinCode = FirebaseRoomClient.NormalizeCode(GUI.TextField(new Rect(connect.x + 118f, connect.y + 184f, 92f, 25f), roomJoinCode ?? string.Empty, 6));
            GUI.backgroundColor = new Color(0.18f, 0.24f, 0.34f, 1f);
            GUI.enabled = oldEnabled && !roomClient.IsBusy && roomJoinCode.Length == 6;
            if (GUI.Button(new Rect(connect.x + 218f, connect.y + 182f, connect.width - 230f, 29f), "JOIN", compactButtonStyle))
            {
                roomDisplayName = FirebaseRoomClient.SanitizeName(roomDisplayName);
                settings.MultiplayerName = roomDisplayName;
                SaveSettings();
                roomClient.BeginJoin(roomJoinCode, roomDisplayName, selectedRole == PlayerRole.Hider ? "hider" : "seeker");
            }
            GUI.enabled = oldEnabled;
            GUI.backgroundColor = oldBackground;

            GUI.Label(new Rect(connect.x + 12f, connect.y + 224f, connect.width - 24f, 34f), roomClient.Status, emptyStateStyle);

            string focused = GUI.GetNameOfFocusedControl();
            roomTextEditing = focused == "BWHS_ROOM_NAME" || focused == "BWHS_ROOM_CODE";
            return;
        }

        FirebaseRoomClient.RoomSnapshot snapshot = roomClient.Snapshot;
        int memberCount = snapshot?.Members?.Count ?? 0;

        Rect roomCard = new Rect(cardX, y, cardWidth, 132f);
        DrawPanelRect(roomCard, new Color(0.09f, 0.13f, 0.16f, 0.98f), roomClient.IsHost ? AccentGreen : AccentCyan);
        GUI.Label(new Rect(roomCard.x + 12f, roomCard.y + 8f, roomCard.width - 24f, 20f), "CONNECTED ROOM", cardHeadingStyle);
        GUI.Label(new Rect(roomCard.x + 12f, roomCard.y + 31f, roomCard.width - 24f, 34f), roomClient.RoomCode, objectiveTitleStyle);
        DrawMetricRow(roomCard, roomCard.y + 72f, "Authority", roomClient.IsHost ? "HOST" : "CLIENT");
        DrawMetricRow(roomCard, roomCard.y + 94f, "Players", memberCount.ToString());
        y += roomCard.height + 8f;

        Rect roleCard = new Rect(cardX, y, cardWidth, 104f);
        DrawPanelRect(roleCard, CardBackground, BorderColor);
        GUI.Label(new Rect(roleCard.x + 12f, roleCard.y + 7f, roleCard.width - 24f, 20f), "YOUR ROLE", cardHeadingStyle);
        GUI.Label(new Rect(roleCard.x + 12f, roleCard.y + 29f, roleCard.width - 24f, 18f), "Role changes sync to everyone in the H+S room", panelSubtitleStyle);
        bool roleEnabled = GUI.enabled;
        GUI.enabled = roleEnabled && !roomClient.IsBusy;
        if (DrawRoleButton(new Rect(roleCard.x + 12f, roleCard.y + 55f, (roleCard.width - 30f) * 0.5f, 37f), "SEEKER", PlayerRole.Seeker))
            SetRole(PlayerRole.Seeker);
        if (DrawRoleButton(new Rect(roleCard.x + 18f + (roleCard.width - 30f) * 0.5f, roleCard.y + 55f, (roleCard.width - 30f) * 0.5f, 37f), "HIDER", PlayerRole.Hider))
            SetRole(PlayerRole.Hider);
        GUI.enabled = roleEnabled;
        y += roleCard.height + 8f;

        Rect members = new Rect(cardX, y, cardWidth, 250f);
        DrawPanelRect(members, CardBackground, BorderColor);
        GUI.Label(new Rect(members.x + 12f, members.y + 7f, members.width - 24f, 20f), "PLAYERS", cardHeadingStyle);

        if (snapshot == null || snapshot.Members.Count == 0)
        {
            GUI.Label(new Rect(members.x + 12f, members.y + 37f, members.width - 24f, 42f), "Waiting for room member data…", emptyStateStyle);
        }
        else
        {
            int visible = Mathf.Min(8, snapshot.Members.Count);
            for (int i = 0; i < visible; i++)
            {
                FirebaseRoomClient.RoomMemberSnapshot member = snapshot.Members[i];
                bool memberHost = string.Equals(member.Uid, snapshot.HostUid, StringComparison.Ordinal);
                string role = string.Equals(member.Role, "hider", StringComparison.Ordinal) ? "HIDER" : "SEEKER";
                string suffix = memberHost ? " · HOST" : string.Empty;
                GUI.Label(new Rect(members.x + 12f, members.y + 32f + i * 22f, members.width * 0.57f, 20f), member.Name, metricLabelStyle);
                GUI.Label(new Rect(members.x + members.width * 0.54f, members.y + 32f + i * 22f, members.width * 0.42f - 12f, 20f), role + suffix, metricValueStyle);
            }
        }

        GUI.Label(new Rect(members.x + 12f, members.y + 207f, members.width - 118f, 34f), roomClient.Status, emptyStateStyle);
        Color leaveBg = GUI.backgroundColor;
        bool leaveEnabled = GUI.enabled;
        GUI.enabled = leaveEnabled && !roomClient.IsBusy;
        GUI.backgroundColor = new Color(0.28f, 0.13f, 0.15f, 1f);
        if (GUI.Button(new Rect(members.xMax - 102f, members.y + 210f, 90f, 28f), roomClient.IsHost ? "CLOSE ROOM" : "LEAVE", compactButtonStyle))
            roomClient.BeginLeave();
        GUI.enabled = leaveEnabled;
        GUI.backgroundColor = leaveBg;
    }

'''
text = replace_once(
    text,
    """    private void DrawMorePanel(Rect panel)\n""",
    room_panel + """    private void DrawMorePanel(Rect panel)\n""",
    "room panel insertion",
)

text = replace_once(
    text,
    """        initialized = true;\n        LoadSettings();\n    }\n""",
    """        initialized = true;\n        LoadSettings();\n        roomDisplayName = FirebaseRoomClient.SanitizeName(settings.MultiplayerName);\n        roomClient = new FirebaseRoomClient();\n    }\n""",
    "room client initialization",
)

text = replace_once(
    text,
    """        if (importantToneClip != null)\n            UnityEngine.Object.Destroy(importantToneClip);\n    }\n""",
    """        if (importantToneClip != null)\n            UnityEngine.Object.Destroy(importantToneClip);\n\n        if (roomClient != null)\n        {\n            roomClient.Dispose();\n            roomClient = null;\n        }\n    }\n""",
    "room client disposal",
)

text = replace_once(
    text,
    """    private enum UiTab\n    {\n        Game,\n        Questions,\n        Map,\n        More\n    }\n""",
    """    private enum UiTab\n    {\n        Game,\n        Questions,\n        Room,\n        Map,\n        More\n    }\n""",
    "UiTab.Room enum",
)

text = replace_once(
    text,
    """        public float SoundVolume { get; set; } = 0.7f;\n\n        public void Clamp()\n""",
    """        public float SoundVolume { get; set; } = 0.7f;\n        public string MultiplayerName { get; set; } = \"Player\";\n\n        public void Clamp()\n""",
    "multiplayer display name setting",
)

text = replace_once(
    text,
    """            SoundVolume = Mathf.Clamp01(SoundVolume);\n        }\n""",
    """            SoundVolume = Mathf.Clamp01(SoundVolume);\n            MultiplayerName = FirebaseRoomClient.SanitizeName(MultiplayerName);\n        }\n""",
    "multiplayer name clamp",
)

CORE.write_text(text, encoding="utf-8")

project = CSPROJ.read_text(encoding="utf-8")
if "<Version>0.0.24</Version>" not in project:
    raise RuntimeError("csproj Version is not 0.0.24")
project = project.replace("<Version>0.0.24</Version>", "<Version>0.0.25</Version>", 1)
project = project.replace("<AssemblyVersion>0.0.24.0</AssemblyVersion>", "<AssemblyVersion>0.0.25.0</AssemblyVersion>", 1)
project = project.replace("<FileVersion>0.0.24.0</FileVersion>", "<FileVersion>0.0.25.0</FileVersion>", 1)
CSPROJ.write_text(project, encoding="utf-8")

print("Applied Core 0.0.25 multiplayer room foundation patch.")
