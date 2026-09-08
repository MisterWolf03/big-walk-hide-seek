using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using BepInEx.Logging;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using UnityEngine;

namespace BigWalkHideSeek.Core;

public static class CoreEntry
{
    internal static ManualLogSource Logger;

    public static void Configure(ManualLogSource logger)
    {
        Logger = logger;
        Logger?.LogInfo("Big Walk Hide + Seek Core 0.0.15 configured.");
    }
}

public class HideSeekOverlay : MonoBehaviour
{
    private const string MapResourceName = "BigWalkHideSeek.Core.big-walk-map.bgra";
    private const float InvSqrt2 = 0.70710678118f;
    private const float TopBarHeight = 58f;
    private const float UiMargin = 14f;
    private const float SidePanelWidth = 390f;

    private const double MapA = 1.01872096;
    private const double MapB = 0.00000814424539;
    private const double MapC = -934.160388;
    private const double MapD = -0.00223877926;
    private const double MapE = 1.01939961;
    private const double MapF = -3130.54945;

    private static readonly Color PageBackground = new Color(14f / 255f, 17f / 255f, 22f / 255f, 1f);
    private static readonly Color TopBarBackground = new Color(17f / 255f, 21f / 255f, 27f / 255f, 0.99f);
    private static readonly Color PanelBackground = new Color(24f / 255f, 29f / 255f, 36f / 255f, 0.98f);
    private static readonly Color CardBackground = new Color(34f / 255f, 41f / 255f, 52f / 255f, 0.98f);
    private static readonly Color BorderColor = new Color(48f / 255f, 57f / 255f, 71f / 255f, 1f);
    private static readonly Color MutedText = new Color(170f / 255f, 179f / 255f, 192f / 255f, 1f);
    private static readonly Color AccentYellow = new Color(242f / 255f, 201f / 255f, 76f / 255f, 1f);
    private static readonly Color AccentGreen = new Color(117f / 255f, 224f / 255f, 163f / 255f, 1f);
    private static readonly Color AccentCyan = new Color(0.24f, 0.86f, 1f, 1f);

    private static readonly MapFeature[] Towers = new[]
    {
        new MapFeature("Red", 1405f, 3669f, new Color(228f / 255f, 90f / 255f, 84f / 255f)),
        new MapFeature("Yellow", 1571f, 3306f, new Color(242f / 255f, 189f / 255f, 46f / 255f)),
        new MapFeature("Green", 1908f, 3937f, new Color(55f / 255f, 180f / 255f, 135f / 255f)),
        new MapFeature("Black", 1676f, 3482f, new Color(32f / 255f, 32f / 255f, 36f / 255f)),
        new MapFeature("Blue", 1853f, 3542f, new Color(38f / 255f, 143f / 255f, 208f / 255f))
    };

    private static readonly MapFeature[] Landmarks = new[]
    {
        new MapFeature("Purple Tunnel", 1897f, 4286f, new Color(155f / 255f, 93f / 255f, 229f / 255f)),
        new MapFeature("Microphone", 1235f, 3408f, new Color(1f, 79f / 255f, 163f / 255f))
    };

    private bool overlayOpen;
    private bool previousCursorVisible;
    private CursorLockMode previousCursorLock;

    private Texture2D mapTexture;
    private bool mapLoadAttempted;
    private string mapLoadError = string.Empty;

    private Rigidbody playerRb;
    private float nextPlayerSearchAt;
    private bool hasPlayerPosition;
    private float gameX;
    private float gameY;

    private float zoom = 1f;
    private Vector2 pan = Vector2.zero;
    private bool showGrid = true;
    private bool showTowers = true;
    private bool showLandmarks = true;

    private MapTool activeTool = MapTool.Pan;
    private readonly List<UserMarker> userMarkers = new List<UserMarker>();
    private int nextMarkerId = 1;
    private int activeMarkerId = -1;

    private bool hasRulerA;
    private bool hasRulerB;
    private Vector2 rulerA;
    private Vector2 rulerB;

    private GUIStyle brandStyle;
    private GUIStyle versionStyle;
    private GUIStyle statusStyle;
    private GUIStyle hintStyle;
    private GUIStyle dockLabelStyle;
    private GUIStyle compactButtonStyle;
    private GUIStyle panelHeadingStyle;
    private GUIStyle panelSubtitleStyle;
    private GUIStyle cardHeadingStyle;
    private GUIStyle liveCardHeadingStyle;
    private GUIStyle markerCardHeadingStyle;
    private GUIStyle metricLabelStyle;
    private GUIStyle metricValueStyle;
    private GUIStyle emptyStateStyle;
    private GUIStyle mapMessageStyle;
    private GUIStyle gridLabelStyle;
    private GUIStyle featureOutlineStyle;
    private GUIStyle featureGlyphStyle;
    private GUIStyle featureLabelStyle;
    private GUIStyle coordinateStyle;
    private GUIStyle userMarkerOutlineStyle;
    private GUIStyle userMarkerStyle;
    private GUIStyle userMarkerLabelStyle;
    private GUIStyle markerShadowStyle;
    private GUIStyle markerOuterStyle;
    private GUIStyle markerStyle;
    private GUIStyle markerCoreStyle;
    private GUIStyle youLabelStyle;
    private GUIStyle rulerPointOutlineStyle;
    private GUIStyle rulerPointStyle;
    private GUIStyle rulerLabelStyle;

    public void Update()
    {
        if (Input.GetKeyDown(KeyCode.F7))
        {
            SetOverlayOpen(!overlayOpen);
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
        UpdatePlayerPosition();
    }

    private void SetOverlayOpen(bool open)
    {
        if (overlayOpen == open)
            return;

        overlayOpen = open;

        if (overlayOpen)
        {
            previousCursorVisible = Cursor.visible;
            previousCursorLock = Cursor.lockState;
            EnterOverlayInputMode();
            Cursor.visible = true;
            Cursor.lockState = CursorLockMode.None;
            CoreEntry.Logger?.LogInfo("Hide + Seek map opened; ControlsManager menu mode enabled.");
        }
        else
        {
            ExitOverlayInputMode();
            Cursor.visible = previousCursorVisible;
            Cursor.lockState = previousCursorLock;
            CoreEntry.Logger?.LogInfo("Hide + Seek map closed; ControlsManager menu mode released.");
        }
    }

    private static void EnterOverlayInputMode()
    {
        try { ControlsManager.SetMenuMode(true); }
        catch (Exception ex) { CoreEntry.Logger?.LogWarning($"ControlsManager.SetMenuMode(true) failed: {ex.Message}"); }

        try { CursorManager.SetFree(); }
        catch (Exception ex) { CoreEntry.Logger?.LogWarning($"CursorManager.SetFree failed: {ex.Message}"); }
    }

    private static void ExitOverlayInputMode()
    {
        try { ControlsManager.SetMenuMode(false); }
        catch (Exception ex) { CoreEntry.Logger?.LogWarning($"ControlsManager.SetMenuMode(false) failed: {ex.Message}"); }

        try { CursorManager.SetLocked(); }
        catch (Exception ex) { CoreEntry.Logger?.LogWarning($"CursorManager.SetLocked failed: {ex.Message}"); }
    }

    private void EnsureMapTexture()
    {
        if (mapTexture != null || mapLoadAttempted)
            return;

        mapLoadAttempted = true;

        try
        {
            Assembly assembly = Assembly.GetExecutingAssembly();
            using Stream stream = assembly.GetManifestResourceStream(MapResourceName);
            if (stream == null)
                throw new FileNotFoundException($"Embedded raw map resource '{MapResourceName}' was not found.");

            using var memory = new MemoryStream();
            stream.CopyTo(memory);
            byte[] packed = memory.ToArray();

            if (packed.Length < 8)
                throw new InvalidDataException("Embedded raw map resource is too short.");

            int width = BitConverter.ToInt32(packed, 0);
            int height = BitConverter.ToInt32(packed, 4);
            if (width <= 0 || height <= 0)
                throw new InvalidDataException($"Embedded raw map has invalid dimensions: {width}x{height}.");

            long expectedPixelBytes = (long)width * height * 4L;
            if (expectedPixelBytes > int.MaxValue || packed.Length != 8 + expectedPixelBytes)
                throw new InvalidDataException($"Embedded raw map size mismatch. Expected {expectedPixelBytes} pixel bytes, got {packed.Length - 8}.");

            byte[] pixelBytes = new byte[(int)expectedPixelBytes];
            Buffer.BlockCopy(packed, 8, pixelBytes, 0, pixelBytes.Length);

            mapTexture = new Texture2D(width, height, TextureFormat.BGRA32, false);
            Il2CppStructArray<byte> il2cppBytes = ToIl2CppByteArray(pixelBytes);
            mapTexture.LoadRawTextureData(il2cppBytes);
            mapTexture.Apply(false, true);
            mapTexture.wrapMode = TextureWrapMode.Clamp;
            mapTexture.filterMode = FilterMode.Bilinear;

            CoreEntry.Logger?.LogInfo($"Embedded Big Walk map loaded from raw BGRA: {mapTexture.width}x{mapTexture.height}.");
        }
        catch (Exception ex)
        {
            mapLoadError = ex.Message;
            CoreEntry.Logger?.LogError($"Could not load embedded Big Walk map: {ex}");
            if (mapTexture != null)
            {
                UnityEngine.Object.Destroy(mapTexture);
                mapTexture = null;
            }
        }
    }

    private static Il2CppStructArray<byte> ToIl2CppByteArray(byte[] managedBytes)
    {
        var result = new Il2CppStructArray<byte>(managedBytes.Length);
        for (int i = 0; i < managedBytes.Length; i++)
            result[i] = managedBytes[i];
        return result;
    }

    private void UpdatePlayerPosition()
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
            hasPlayerPosition = true;
        }
        catch
        {
            playerRb = null;
            hasPlayerPosition = false;
        }
    }

    private void FindPlayerRigidbody()
    {
        try
        {
            Rigidbody[] bodies = FindObjectsOfType<Rigidbody>();
            foreach (Rigidbody rb in bodies)
            {
                if (rb == null || rb.gameObject == null)
                    continue;
                if (!rb.gameObject.name.StartsWith("PlayerCharacter ", StringComparison.Ordinal))
                    continue;

                playerRb = rb;
                CoreEntry.Logger?.LogInfo($"Map player found: '{rb.gameObject.name}'.");
                return;
            }
        }
        catch (Exception ex)
        {
            CoreEntry.Logger?.LogWarning($"Player search failed: {ex.Message}");
        }
    }

    private static void UnityToBigWalk(float unityX, float unityZ, out float outX, out float outY)
    {
        outX = (unityX + unityZ) * InvSqrt2 + 1900f;
        outY = (unityX - unityZ) * InvSqrt2 + 3300f;
    }

    private static Vector2 GameToMapPixel(float x, float y)
    {
        return new Vector2(
            (float)(MapA * x + MapB * y + MapC),
            (float)(MapD * x + MapE * y + MapF)
        );
    }

    private static Vector2 MapPixelToGame(float px, float py)
    {
        double det = MapA * MapE - MapB * MapD;
        double shiftedX = px - MapC;
        double shiftedY = py - MapF;
        return new Vector2(
            (float)((MapE * shiftedX - MapB * shiftedY) / det),
            (float)((-MapD * shiftedX + MapA * shiftedY) / det)
        );
    }

    public void OnGUI()
    {
        if (!overlayOpen)
            return;

        EnsureStyles();
        EnsureMapTexture();
        GUI.depth = -10000;

        Color oldColor = GUI.color;
        Color oldBackground = GUI.backgroundColor;

        GUI.color = PageBackground;
        GUI.DrawTexture(new Rect(0f, 0f, Screen.width, Screen.height), Texture2D.whiteTexture);
        GUI.color = Color.white;

        DrawTopBar();
        Rect viewport = new Rect(0f, TopBarHeight, Screen.width, Mathf.Max(100f, Screen.height - TopBarHeight));
        DrawMap(viewport);

        GUI.color = oldColor;
        GUI.backgroundColor = oldBackground;

        Event evt = Event.current;
        if (evt != null && (evt.isMouse || evt.type == EventType.ScrollWheel))
            evt.Use();
    }

    private void DrawTopBar()
    {
        DrawSolidRect(new Rect(0f, 0f, Screen.width, TopBarHeight), TopBarBackground);
        DrawSolidRect(new Rect(0f, TopBarHeight - 1f, Screen.width, 1f), BorderColor);

        GUI.Label(new Rect(16f, 6f, 360f, 27f), "BIG WALK HIDE + SEEK", brandStyle);
        GUI.Label(new Rect(18f, 31f, 320f, 18f), "CORE v0.0.15 · MAP", versionStyle);

        string status = hasPlayerPosition
            ? $"LIVE · Y {gameY:0}, X {gameX:0}"
            : "SEARCHING FOR PLAYER…";
        GUI.Label(new Rect(Mathf.Max(420f, Screen.width - 525f), 13f, 390f, 30f), status, statusStyle);

        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = new Color(0.16f, 0.19f, 0.23f, 1f);
        if (GUI.Button(new Rect(Screen.width - 104f, 11f, 88f, 36f), "CLOSE", compactButtonStyle))
            SetOverlayOpen(false);
        GUI.backgroundColor = oldBackground;
    }

    private void DrawMap(Rect viewport)
    {
        if (mapTexture == null)
        {
            string message = string.IsNullOrEmpty(mapLoadError)
                ? "Loading Big Walk map…"
                : $"Map failed to load\n{mapLoadError}";
            GUI.Label(new Rect(0f, TopBarHeight, Screen.width, Screen.height - TopBarHeight), message, mapMessageStyle);
            return;
        }

        float sideWidth = Mathf.Min(SidePanelWidth, Mathf.Max(320f, viewport.width * 0.34f));
        Rect toolDock = new Rect(UiMargin, UiMargin, 226f, 50f);
        Rect displayDock = new Rect(toolDock.xMax + 8f, UiMargin, 282f, 50f);
        Rect actionDock = new Rect(UiMargin, 72f, 284f, 50f);
        Rect sidePanel = new Rect(viewport.width - sideWidth - UiMargin, UiMargin, sideWidth, Mathf.Min(584f, viewport.height - UiMargin * 2f));

        if (displayDock.xMax > sidePanel.x - 8f)
            displayDock = new Rect(UiMargin, 130f, 282f, 50f);

        Rect toolDockGlobal = OffsetRect(toolDock, viewport.x, viewport.y);
        Rect displayDockGlobal = OffsetRect(displayDock, viewport.x, viewport.y);
        Rect actionDockGlobal = OffsetRect(actionDock, viewport.x, viewport.y);
        Rect sidePanelGlobal = OffsetRect(sidePanel, viewport.x, viewport.y);

        Rect mapRect = GetMapRect(viewport.width, viewport.height);
        HandleMapInput(viewport, toolDockGlobal, displayDockGlobal, actionDockGlobal, sidePanelGlobal, mapRect);

        Event evt = Event.current;
        Vector2 globalMouse = evt != null ? evt.mousePosition : new Vector2(-1000f, -1000f);
        bool canShowCoordinateTip = viewport.Contains(globalMouse)
            && !toolDockGlobal.Contains(globalMouse)
            && !displayDockGlobal.Contains(globalMouse)
            && !actionDockGlobal.Contains(globalMouse)
            && !sidePanelGlobal.Contains(globalMouse);
        Vector2 localMouse = new Vector2(globalMouse.x - viewport.x, globalMouse.y - viewport.y);

        GUI.BeginGroup(viewport);

        GUI.DrawTexture(mapRect, mapTexture, ScaleMode.StretchToFill, false);

        if (showGrid)
            DrawGrid(mapRect);
        if (showTowers)
            DrawFeatures(mapRect, Towers, false);
        if (showLandmarks)
            DrawFeatures(mapRect, Landmarks, true);

        DrawRuler(mapRect);
        DrawUserMarkers(mapRect);
        if (hasPlayerPosition)
            DrawPlayerMarker(mapRect);

        DrawToolDock(toolDock);
        DrawDisplayDock(displayDock);
        DrawActionDock(actionDock, viewport.width, viewport.height);
        DrawNavigationPanel(sidePanel);

        if (canShowCoordinateTip)
            DrawCoordinateTip(localMouse, mapRect, viewport.width, viewport.height);

        DrawBottomHint(viewport.height);

        GUI.EndGroup();
    }

    private void DrawToolDock(Rect dock)
    {
        DrawDockBackground(dock);
        GUI.Label(new Rect(dock.x + 7f, dock.y + 2f, 48f, 14f), "TOOLS", dockLabelStyle);

        float y = dock.y + 15f;
        if (DrawToolButton(new Rect(dock.x + 7f, y, 62f, 29f), "PAN", activeTool == MapTool.Pan))
            activeTool = MapTool.Pan;
        if (DrawToolButton(new Rect(dock.x + 76f, y, 72f, 29f), "MARKER", activeTool == MapTool.Marker))
            activeTool = MapTool.Marker;
        if (DrawToolButton(new Rect(dock.x + 155f, y, 64f, 29f), "RULER", activeTool == MapTool.Ruler))
            activeTool = MapTool.Ruler;
    }

    private void DrawDisplayDock(Rect dock)
    {
        DrawDockBackground(dock);
        GUI.Label(new Rect(dock.x + 7f, dock.y + 2f, 70f, 14f), "DISPLAY", dockLabelStyle);

        float y = dock.y + 15f;
        showGrid = DrawToggleButton(new Rect(dock.x + 7f, y, 58f, 29f), "GRID", showGrid);
        showTowers = DrawToggleButton(new Rect(dock.x + 72f, y, 76f, 29f), "TOWERS", showTowers);
        showLandmarks = DrawToggleButton(new Rect(dock.x + 155f, y, 120f, 29f), "LANDMARKS", showLandmarks);
    }

    private void DrawActionDock(Rect dock, float viewportWidth, float viewportHeight)
    {
        DrawDockBackground(dock);
        GUI.Label(new Rect(dock.x + 7f, dock.y + 2f, 80f, 14f), "VIEW", dockLabelStyle);

        float y = dock.y + 15f;
        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = new Color(0.16f, 0.19f, 0.23f, 1f);

        if (GUI.Button(new Rect(dock.x + 7f, y, 46f, 29f), "FIT", compactButtonStyle))
            FitMap();

        GUI.enabled = hasPlayerPosition;
        if (GUI.Button(new Rect(dock.x + 60f, y, 76f, 29f), "CENTER", compactButtonStyle))
            CenterOnPlayer(viewportWidth, viewportHeight);
        GUI.enabled = true;

        if (GUI.Button(new Rect(dock.x + 143f, y, 31f, 29f), "−", compactButtonStyle))
            ZoomAt(viewportWidth, viewportHeight, new Vector2(viewportWidth * 0.5f, viewportHeight * 0.5f), 1f / 1.25f);
        if (GUI.Button(new Rect(dock.x + 181f, y, 31f, 29f), "+", compactButtonStyle))
            ZoomAt(viewportWidth, viewportHeight, new Vector2(viewportWidth * 0.5f, viewportHeight * 0.5f), 1.25f);

        GUI.backgroundColor = oldBackground;
        GUI.Label(new Rect(dock.x + 219f, y + 2f, 58f, 25f), $"{zoom:0.0}×", hintStyle);
    }

    private void DrawNavigationPanel(Rect panel)
    {
        DrawPanelRect(panel, PanelBackground, BorderColor);

        GUI.Label(new Rect(panel.x + 14f, panel.y + 10f, panel.width - 28f, 21f), "MAP", panelHeadingStyle);
        GUI.Label(new Rect(panel.x + 14f, panel.y + 29f, panel.width - 28f, 18f), "Navigation + map tools", panelSubtitleStyle);

        float cardX = panel.x + 12f;
        float cardWidth = panel.width - 24f;
        float y = panel.y + 57f;

        Rect playerCard = new Rect(cardX, y, cardWidth, 150f);
        DrawPlayerCard(playerCard);
        y += playerCard.height + 10f;

        Rect markerCard = new Rect(cardX, y, cardWidth, 185f);
        DrawMarkerCard(markerCard);
        y += markerCard.height + 10f;

        Rect rulerCard = new Rect(cardX, y, cardWidth, 165f);
        DrawRulerCard(rulerCard);
    }

    private void DrawPlayerCard(Rect card)
    {
        DrawPanelRect(card, CardBackground, BorderColor);
        GUI.Label(new Rect(card.x + 12f, card.y + 7f, card.width - 24f, 20f), "YOUR POSITION", liveCardHeadingStyle);

        if (!hasPlayerPosition)
        {
            GUI.Label(new Rect(card.x + 12f, card.y + 40f, card.width - 24f, 52f), "Searching for PlayerCharacter…", emptyStateStyle);
            return;
        }

        MapFeature nearest = NearestTowerAt(gameX, gameY, out float distance);
        BearingInfo(gameX, gameY, nearest.X, nearest.Y, out float degrees, out string direction);

        float y = card.y + 31f;
        DrawMetricRow(card, y, "Coordinates", $"Y {gameY:0}, X {gameX:0}"); y += 22f;
        DrawMetricRow(card, y, "Grid square", GridSquare(gameX, gameY)); y += 22f;
        DrawMetricRow(card, y, "Nearest tower", nearest.Name); y += 22f;
        DrawMetricRow(card, y, "Tower distance", $"{distance:0} units"); y += 22f;
        DrawMetricRow(card, y, "Tower direction", $"{direction} ({degrees:0}°)");
    }

    private void DrawMarkerCard(Rect card)
    {
        DrawPanelRect(card, CardBackground, BorderColor);
        GUI.Label(new Rect(card.x + 12f, card.y + 7f, card.width - 24f, 20f), $"ACTIVE MARKER · {userMarkers.Count} SAVED", markerCardHeadingStyle);

        UserMarker active = GetActiveMarker();
        if (active == null)
        {
            string message = userMarkers.Count == 0
                ? "Choose MARKER, then click the map to place one."
                : "Click a saved marker on the map to select it.";
            GUI.Label(new Rect(card.x + 12f, card.y + 40f, card.width - 24f, 54f), message, emptyStateStyle);
        }
        else
        {
            MapFeature nearest = NearestTowerAt(active.X, active.Y, out float distance);
            BearingInfo(active.X, active.Y, nearest.X, nearest.Y, out float degrees, out string direction);

            float y = card.y + 31f;
            DrawMetricRow(card, y, "Marker", $"M{active.Id}"); y += 22f;
            DrawMetricRow(card, y, "Coordinates", $"Y {active.Y:0}, X {active.X:0}"); y += 22f;
            DrawMetricRow(card, y, "Grid square", GridSquare(active.X, active.Y)); y += 22f;
            DrawMetricRow(card, y, "Nearest tower", nearest.Name); y += 22f;
            DrawMetricRow(card, y, "Tower", $"{distance:0} units · {direction} ({degrees:0}°)");
        }

        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = new Color(0.25f, 0.14f, 0.15f, 1f);
        GUI.enabled = active != null;
        if (GUI.Button(new Rect(card.x + 12f, card.y + 150f, 132f, 27f), "REMOVE ACTIVE", compactButtonStyle))
            RemoveActiveMarker();
        GUI.enabled = userMarkers.Count > 0;
        if (GUI.Button(new Rect(card.x + card.width - 120f, card.y + 150f, 108f, 27f), "CLEAR ALL", compactButtonStyle))
            ClearAllMarkers();
        GUI.enabled = true;
        GUI.backgroundColor = oldBackground;
    }

    private void DrawRulerCard(Rect card)
    {
        DrawPanelRect(card, CardBackground, BorderColor);
        GUI.Label(new Rect(card.x + 12f, card.y + 7f, card.width - 24f, 20f), "DISTANCE + BEARING", cardHeadingStyle);

        if (!hasRulerA)
        {
            GUI.Label(new Rect(card.x + 12f, card.y + 39f, card.width - 24f, 46f), "Choose RULER, then click point A and point B.", emptyStateStyle);
        }
        else if (!hasRulerB)
        {
            float y = card.y + 31f;
            DrawMetricRow(card, y, "Point A", $"Y {rulerA.y:0}, X {rulerA.x:0}"); y += 22f;
            DrawMetricRow(card, y, "Point B", "Click map to set");
        }
        else
        {
            float distance = Vector2.Distance(rulerA, rulerB);
            BearingInfo(rulerA.x, rulerA.y, rulerB.x, rulerB.y, out float degrees, out string direction);

            float y = card.y + 31f;
            DrawMetricRow(card, y, "Point A", $"Y {rulerA.y:0}, X {rulerA.x:0}"); y += 22f;
            DrawMetricRow(card, y, "Point B", $"Y {rulerB.y:0}, X {rulerB.x:0}"); y += 22f;
            DrawMetricRow(card, y, "Distance", $"{distance:0} units"); y += 22f;
            DrawMetricRow(card, y, "Bearing A → B", $"{direction} ({degrees:0}°)");
        }

        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = new Color(0.16f, 0.19f, 0.23f, 1f);
        GUI.enabled = hasRulerA;
        if (GUI.Button(new Rect(card.x + 12f, card.y + 130f, card.width - 24f, 27f), "CLEAR RULER", compactButtonStyle))
            ClearRuler();
        GUI.enabled = true;
        GUI.backgroundColor = oldBackground;
    }

    private void DrawMetricRow(Rect card, float y, string label, string value)
    {
        GUI.Label(new Rect(card.x + 12f, y, 132f, 20f), label, metricLabelStyle);
        GUI.Label(new Rect(card.x + 146f, y, card.width - 158f, 20f), value, metricValueStyle);
        DrawSolidRect(new Rect(card.x + 12f, y + 20f, card.width - 24f, 1f), new Color(1f, 1f, 1f, 0.07f));
    }

    private void DrawBottomHint(float viewportHeight)
    {
        string hint;
        if (activeTool == MapTool.Marker)
            hint = "MARKER · Click map to place · Click marker to select · Wheel to zoom · F7/Esc close";
        else if (activeTool == MapTool.Ruler)
            hint = "RULER · Click A, then B · Third click starts over · Wheel to zoom · F7/Esc close";
        else
            hint = "PAN · Drag map · Click marker to select · Wheel to zoom · F7/Esc close";

        Rect pill = new Rect(UiMargin, viewportHeight - 38f, 690f, 26f);
        DrawPanelRect(pill, new Color(17f / 255f, 21f / 255f, 27f / 255f, 0.94f), BorderColor);
        GUI.Label(new Rect(pill.x + 10f, pill.y + 2f, pill.width - 20f, 22f), hint, hintStyle);
    }

    private bool DrawToolButton(Rect rect, string label, bool active)
    {
        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = active
            ? new Color(0.30f, 0.25f, 0.10f, 1f)
            : new Color(0.16f, 0.19f, 0.23f, 1f);
        bool clicked = GUI.Button(rect, label, compactButtonStyle);
        if (active)
            DrawSolidRect(new Rect(rect.x, rect.y + rect.height - 2f, rect.width, 2f), AccentYellow);
        GUI.backgroundColor = oldBackground;
        return clicked;
    }

    private bool DrawToggleButton(Rect rect, string label, bool value)
    {
        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = value
            ? new Color(0.15f, 0.24f, 0.19f, 1f)
            : new Color(0.16f, 0.19f, 0.23f, 1f);
        bool clicked = GUI.Button(rect, label, compactButtonStyle);
        if (value)
            DrawSolidRect(new Rect(rect.x, rect.y + rect.height - 2f, rect.width, 2f), AccentGreen);
        GUI.backgroundColor = oldBackground;
        return clicked ? !value : value;
    }

    private static void DrawDockBackground(Rect rect)
    {
        DrawPanelRect(rect, new Color(17f / 255f, 21f / 255f, 27f / 255f, 0.96f), BorderColor);
    }

    private static void DrawPanelRect(Rect rect, Color fill, Color border)
    {
        DrawSolidRect(rect, border);
        if (rect.width > 2f && rect.height > 2f)
            DrawSolidRect(new Rect(rect.x + 1f, rect.y + 1f, rect.width - 2f, rect.height - 2f), fill);
    }

    private static void DrawSolidRect(Rect rect, Color color)
    {
        Color oldColor = GUI.color;
        GUI.color = color;
        GUI.DrawTexture(rect, Texture2D.whiteTexture);
        GUI.color = oldColor;
    }

    private static Rect OffsetRect(Rect rect, float x, float y)
    {
        return new Rect(rect.x + x, rect.y + y, rect.width, rect.height);
    }

    private Rect GetMapRect(float viewportWidth, float viewportHeight)
    {
        float baseScale = Mathf.Min(viewportWidth / mapTexture.width, viewportHeight / mapTexture.height);
        float scale = baseScale * zoom;
        float width = mapTexture.width * scale;
        float height = mapTexture.height * scale;
        return new Rect(
            (viewportWidth - width) * 0.5f + pan.x,
            (viewportHeight - height) * 0.5f + pan.y,
            width,
            height
        );
    }

    private Vector2 GameToOverlayPoint(Rect mapRect, float x, float y)
    {
        Vector2 pixel = GameToMapPixel(x, y);
        return new Vector2(
            mapRect.x + (pixel.x / mapTexture.width) * mapRect.width,
            mapRect.y + (pixel.y / mapTexture.height) * mapRect.height
        );
    }

    private Vector2 OverlayPointToGame(Rect mapRect, Vector2 localPoint)
    {
        float px = ((localPoint.x - mapRect.x) / mapRect.width) * mapTexture.width;
        float py = ((localPoint.y - mapRect.y) / mapRect.height) * mapTexture.height;
        return MapPixelToGame(px, py);
    }

    private void DrawGrid(Rect mapRect)
    {
        Color lineColor = new Color(1f, 1f, 1f, 0.62f);
        const float lineWidth = 1f;

        Color oldColor = GUI.color;
        GUI.color = lineColor;

        for (int x = 1000; x <= 2400; x += 100)
        {
            Vector2 a = GameToOverlayPoint(mapRect, x, 3000f);
            Vector2 b = GameToOverlayPoint(mapRect, x, 4600f);
            float lineX = (a.x + b.x) * 0.5f;
            float yMin = Mathf.Max(mapRect.yMin, Mathf.Min(a.y, b.y));
            float yMax = Mathf.Min(mapRect.yMax, Mathf.Max(a.y, b.y));

            if (lineX >= mapRect.xMin && lineX <= mapRect.xMax && yMax > yMin)
                GUI.DrawTexture(new Rect(lineX - lineWidth * 0.5f, yMin, lineWidth, yMax - yMin), Texture2D.whiteTexture);

            Vector2 label = GameToOverlayPoint(mapRect, x, 3110f);
            if (label.x >= mapRect.xMin && label.x <= mapRect.xMax && label.y >= mapRect.yMin && label.y <= mapRect.yMax)
                GUI.Label(new Rect(label.x + 3f, label.y - 9f, 34f, 18f), (x / 100).ToString(), gridLabelStyle);
        }

        for (int y = 3100; y <= 4500; y += 100)
        {
            Vector2 a = GameToOverlayPoint(mapRect, 900f, y);
            Vector2 b = GameToOverlayPoint(mapRect, 2500f, y);
            float lineY = (a.y + b.y) * 0.5f;
            float xMin = Mathf.Max(mapRect.xMin, Mathf.Min(a.x, b.x));
            float xMax = Mathf.Min(mapRect.xMax, Mathf.Max(a.x, b.x));

            if (lineY >= mapRect.yMin && lineY <= mapRect.yMax && xMax > xMin)
                GUI.DrawTexture(new Rect(xMin, lineY - lineWidth * 0.5f, xMax - xMin, lineWidth), Texture2D.whiteTexture);

            Vector2 label = GameToOverlayPoint(mapRect, 1005f, y);
            if (label.x >= mapRect.xMin && label.x <= mapRect.xMax && label.y >= mapRect.yMin && label.y <= mapRect.yMax)
                GUI.Label(new Rect(label.x + 3f, label.y - 16f, 34f, 18f), (y / 100).ToString(), gridLabelStyle);
        }

        GUI.color = oldColor;
    }

    private void DrawFeatures(Rect mapRect, MapFeature[] features, bool diamond)
    {
        string glyph = diamond ? "◆" : "●";

        foreach (MapFeature feature in features)
        {
            Vector2 point = GameToOverlayPoint(mapRect, feature.X, feature.Y);
            if (point.x < mapRect.xMin - 20f || point.x > mapRect.xMax + 20f || point.y < mapRect.yMin - 20f || point.y > mapRect.yMax + 20f)
                continue;

            Rect glyphRect = new Rect(point.x - 16f, point.y - 17f, 32f, 32f);
            Color oldColor = GUI.color;

            GUI.color = Color.white;
            GUI.Label(glyphRect, glyph, featureOutlineStyle);
            GUI.color = feature.Color;
            GUI.Label(glyphRect, glyph, featureGlyphStyle);

            Rect textRect = new Rect(point.x + 14f, point.y - 10f, 160f, 24f);
            GUI.color = new Color(0f, 0f, 0f, 0.9f);
            GUI.Label(new Rect(textRect.x - 1f, textRect.y, textRect.width, textRect.height), feature.Name, featureLabelStyle);
            GUI.Label(new Rect(textRect.x + 1f, textRect.y, textRect.width, textRect.height), feature.Name, featureLabelStyle);
            GUI.Label(new Rect(textRect.x, textRect.y - 1f, textRect.width, textRect.height), feature.Name, featureLabelStyle);
            GUI.Label(new Rect(textRect.x, textRect.y + 1f, textRect.width, textRect.height), feature.Name, featureLabelStyle);
            GUI.color = Color.white;
            GUI.Label(textRect, feature.Name, featureLabelStyle);
            GUI.color = oldColor;
        }
    }

    private void DrawUserMarkers(Rect mapRect)
    {
        foreach (UserMarker marker in userMarkers)
        {
            Vector2 point = GameToOverlayPoint(mapRect, marker.X, marker.Y);
            if (point.x < mapRect.xMin - 24f || point.x > mapRect.xMax + 24f || point.y < mapRect.yMin - 24f || point.y > mapRect.yMax + 24f)
                continue;

            Rect glyphRect = new Rect(point.x - 17f, point.y - 18f, 34f, 34f);
            bool active = marker.Id == activeMarkerId;

            Color oldColor = GUI.color;
            GUI.color = active ? Color.white : new Color(0.08f, 0.09f, 0.11f, 0.98f);
            GUI.Label(glyphRect, "◆", userMarkerOutlineStyle);
            GUI.color = AccentYellow;
            GUI.Label(glyphRect, "◆", userMarkerStyle);

            Rect labelRect = new Rect(point.x + 14f, point.y - 10f, 56f, 22f);
            GUI.color = new Color(0f, 0f, 0f, 0.92f);
            GUI.Label(new Rect(labelRect.x - 1f, labelRect.y, labelRect.width, labelRect.height), $"M{marker.Id}", userMarkerLabelStyle);
            GUI.Label(new Rect(labelRect.x + 1f, labelRect.y, labelRect.width, labelRect.height), $"M{marker.Id}", userMarkerLabelStyle);
            GUI.color = Color.white;
            GUI.Label(labelRect, $"M{marker.Id}", userMarkerLabelStyle);
            GUI.color = oldColor;
        }
    }

    private void DrawRuler(Rect mapRect)
    {
        if (!hasRulerA)
            return;

        Vector2 a = GameToOverlayPoint(mapRect, rulerA.x, rulerA.y);
        if (hasRulerB)
        {
            Vector2 b = GameToOverlayPoint(mapRect, rulerB.x, rulerB.y);
            DrawSafeSegmentedLine(a, b, new Color(1f, 0.86f, 0.35f, 0.95f), 3f);
            DrawRulerPoint(b, "B");
        }

        DrawRulerPoint(a, "A");
    }

    private void DrawRulerPoint(Vector2 point, string label)
    {
        Rect glyphRect = new Rect(point.x - 15f, point.y - 16f, 30f, 30f);
        Color oldColor = GUI.color;
        GUI.color = new Color(0.04f, 0.05f, 0.07f, 0.98f);
        GUI.Label(glyphRect, "●", rulerPointOutlineStyle);
        GUI.color = new Color(1f, 0.86f, 0.35f, 1f);
        GUI.Label(glyphRect, "●", rulerPointStyle);
        GUI.color = oldColor;

        GUI.Label(new Rect(point.x + 12f, point.y - 10f, 28f, 20f), label, rulerLabelStyle);
    }

    private static void DrawSafeSegmentedLine(Vector2 start, Vector2 end, Color color, float width)
    {
        Vector2 delta = end - start;
        float length = delta.magnitude;
        if (length < 0.01f)
            return;

        int steps = Mathf.Max(1, Mathf.CeilToInt(length / 4f));
        Color oldColor = GUI.color;
        GUI.color = color;

        for (int i = 0; i <= steps; i++)
        {
            float t = i / (float)steps;
            Vector2 p = start + delta * t;
            GUI.DrawTexture(new Rect(p.x - width * 0.5f, p.y - width * 0.5f, width, width), Texture2D.whiteTexture);
        }

        GUI.color = oldColor;
    }

    private void DrawCoordinateTip(Vector2 localMouse, Rect mapRect, float viewportWidth, float viewportHeight)
    {
        if (!mapRect.Contains(localMouse))
            return;

        Vector2 game = OverlayPointToGame(mapRect, localMouse);
        const float width = 154f;
        const float height = 28f;
        float tipX = Mathf.Clamp(localMouse.x + 14f, 4f, Mathf.Max(4f, viewportWidth - width - 4f));
        float tipY = Mathf.Clamp(localMouse.y + 14f, 4f, Mathf.Max(4f, viewportHeight - height - 4f));
        Rect tip = new Rect(tipX, tipY, width, height);

        DrawPanelRect(tip, new Color(0.03f, 0.04f, 0.055f, 0.96f), BorderColor);
        GUI.Label(tip, $"Y {game.y:0}, X {game.x:0}", coordinateStyle);
    }

    private void DrawPlayerMarker(Rect mapRect)
    {
        Vector2 pixel = GameToMapPixel(gameX, gameY);
        float sx = mapRect.x + (pixel.x / mapTexture.width) * mapRect.width;
        float sy = mapRect.y + (pixel.y / mapTexture.height) * mapRect.height;

        if (sx < mapRect.xMin - 42f || sy < mapRect.yMin - 42f || sx > mapRect.xMax + 42f || sy > mapRect.yMax + 42f)
            return;

        Rect markerRect = new Rect(sx - 24f, sy - 25f, 48f, 48f);
        GUI.Label(new Rect(markerRect.x - 2f, markerRect.y, markerRect.width, markerRect.height), "●", markerShadowStyle);
        GUI.Label(new Rect(markerRect.x + 2f, markerRect.y, markerRect.width, markerRect.height), "●", markerShadowStyle);
        GUI.Label(new Rect(markerRect.x, markerRect.y - 2f, markerRect.width, markerRect.height), "●", markerShadowStyle);
        GUI.Label(new Rect(markerRect.x, markerRect.y + 2f, markerRect.width, markerRect.height), "●", markerShadowStyle);
        GUI.Label(markerRect, "●", markerOuterStyle);
        GUI.Label(markerRect, "●", markerStyle);
        GUI.Label(markerRect, "●", markerCoreStyle);

        Rect labelRect = new Rect(sx + 18f, sy - 12f, 52f, 24f);
        Color oldColor = GUI.color;
        GUI.color = new Color(0f, 0f, 0f, 0.95f);
        GUI.Label(new Rect(labelRect.x - 1f, labelRect.y, labelRect.width, labelRect.height), "YOU", youLabelStyle);
        GUI.Label(new Rect(labelRect.x + 1f, labelRect.y, labelRect.width, labelRect.height), "YOU", youLabelStyle);
        GUI.Label(new Rect(labelRect.x, labelRect.y - 1f, labelRect.width, labelRect.height), "YOU", youLabelStyle);
        GUI.Label(new Rect(labelRect.x, labelRect.y + 1f, labelRect.width, labelRect.height), "YOU", youLabelStyle);
        GUI.color = Color.white;
        GUI.Label(labelRect, "YOU", youLabelStyle);
        GUI.color = oldColor;
    }

    private void HandleMapInput(Rect viewport, Rect toolDockGlobal, Rect displayDockGlobal, Rect actionDockGlobal, Rect sidePanelGlobal, Rect mapRect)
    {
        Event evt = Event.current;
        if (evt == null || evt.type == EventType.Used)
            return;

        Vector2 mouse = evt.mousePosition;
        if (!viewport.Contains(mouse)
            || toolDockGlobal.Contains(mouse)
            || displayDockGlobal.Contains(mouse)
            || actionDockGlobal.Contains(mouse)
            || sidePanelGlobal.Contains(mouse))
            return;

        Vector2 localMouse = new Vector2(mouse.x - viewport.x, mouse.y - viewport.y);

        if (evt.type == EventType.ScrollWheel)
        {
            float factor = evt.delta.y > 0f ? 1f / 1.18f : 1.18f;
            ZoomAt(viewport.width, viewport.height, localMouse, factor);
            evt.Use();
            return;
        }

        if (evt.type == EventType.MouseDown && evt.button == 0 && mapRect.Contains(localMouse))
        {
            if (activeTool != MapTool.Ruler)
            {
                int hitMarker = FindMarkerAt(localMouse, mapRect);
                if (hitMarker >= 0)
                {
                    activeMarkerId = hitMarker;
                    evt.Use();
                    return;
                }
            }

            if (activeTool == MapTool.Marker)
            {
                AddMarkerAt(localMouse, mapRect);
                evt.Use();
                return;
            }

            if (activeTool == MapTool.Ruler)
            {
                SetRulerPoint(localMouse, mapRect);
                evt.Use();
                return;
            }
        }

        if (activeTool == MapTool.Pan && evt.type == EventType.MouseDrag && evt.button == 0)
        {
            pan += evt.delta;
            evt.Use();
        }
    }

    private int FindMarkerAt(Vector2 localMouse, Rect mapRect)
    {
        const float hitRadius = 16f;
        float bestDistance = hitRadius;
        int bestId = -1;

        foreach (UserMarker marker in userMarkers)
        {
            Vector2 point = GameToOverlayPoint(mapRect, marker.X, marker.Y);
            float distance = Vector2.Distance(localMouse, point);
            if (distance <= bestDistance)
            {
                bestDistance = distance;
                bestId = marker.Id;
            }
        }

        return bestId;
    }

    private void AddMarkerAt(Vector2 localMouse, Rect mapRect)
    {
        Vector2 game = OverlayPointToGame(mapRect, localMouse);
        var marker = new UserMarker(nextMarkerId++, game.x, game.y);
        userMarkers.Add(marker);
        activeMarkerId = marker.Id;
        CoreEntry.Logger?.LogInfo($"Map marker M{marker.Id} placed at Y {marker.Y:0}, X {marker.X:0}.");
    }

    private UserMarker GetActiveMarker()
    {
        foreach (UserMarker marker in userMarkers)
        {
            if (marker.Id == activeMarkerId)
                return marker;
        }
        return null;
    }

    private void RemoveActiveMarker()
    {
        if (activeMarkerId < 0)
            return;

        for (int i = userMarkers.Count - 1; i >= 0; i--)
        {
            if (userMarkers[i].Id == activeMarkerId)
            {
                userMarkers.RemoveAt(i);
                break;
            }
        }

        activeMarkerId = userMarkers.Count > 0 ? userMarkers[userMarkers.Count - 1].Id : -1;
    }

    private void ClearAllMarkers()
    {
        userMarkers.Clear();
        activeMarkerId = -1;
        nextMarkerId = 1;
    }

    private void SetRulerPoint(Vector2 localMouse, Rect mapRect)
    {
        Vector2 game = OverlayPointToGame(mapRect, localMouse);

        if (!hasRulerA || hasRulerB)
        {
            rulerA = game;
            hasRulerA = true;
            hasRulerB = false;
            return;
        }

        rulerB = game;
        hasRulerB = true;
    }

    private void ClearRuler()
    {
        hasRulerA = false;
        hasRulerB = false;
        rulerA = Vector2.zero;
        rulerB = Vector2.zero;
    }

    private static string GridSquare(float x, float y)
    {
        return $"X {Mathf.FloorToInt(x / 100f)} / Y {Mathf.FloorToInt(y / 100f)}";
    }

    private static MapFeature NearestTowerAt(float x, float y, out float distance)
    {
        MapFeature best = Towers[0];
        float bestDistance = float.MaxValue;

        foreach (MapFeature tower in Towers)
        {
            float dx = tower.X - x;
            float dy = tower.Y - y;
            float d = Mathf.Sqrt(dx * dx + dy * dy);
            if (d < bestDistance)
            {
                bestDistance = d;
                best = tower;
            }
        }

        distance = bestDistance;
        return best;
    }

    private static void BearingInfo(float x1, float y1, float x2, float y2, out float degrees, out string direction)
    {
        float dx = x2 - x1;
        float dy = y2 - y1;
        degrees = (Mathf.Atan2(dx, -dy) * Mathf.Rad2Deg + 360f) % 360f;
        string[] directions = { "N", "NE", "E", "SE", "S", "SW", "W", "NW" };
        direction = directions[Mathf.RoundToInt(degrees / 45f) % 8];
    }

    private void ZoomAt(float viewportWidth, float viewportHeight, Vector2 localPoint, float factor)
    {
        if (mapTexture == null)
            return;

        Rect oldRect = GetMapRect(viewportWidth, viewportHeight);
        float oldScale = oldRect.width / mapTexture.width;
        Vector2 mapPixel = new Vector2(
            (localPoint.x - oldRect.x) / oldScale,
            (localPoint.y - oldRect.y) / oldScale
        );

        float newZoom = Mathf.Clamp(zoom * factor, 1f, 8f);
        if (Mathf.Abs(newZoom - zoom) < 0.0001f)
            return;

        zoom = newZoom;
        float baseScale = Mathf.Min(viewportWidth / mapTexture.width, viewportHeight / mapTexture.height);
        float newScale = baseScale * zoom;
        float centeredX = (viewportWidth - mapTexture.width * newScale) * 0.5f;
        float centeredY = (viewportHeight - mapTexture.height * newScale) * 0.5f;
        pan.x = localPoint.x - centeredX - mapPixel.x * newScale;
        pan.y = localPoint.y - centeredY - mapPixel.y * newScale;
    }

    private void FitMap()
    {
        zoom = 1f;
        pan = Vector2.zero;
    }

    private void CenterOnPlayer(float viewportWidth, float viewportHeight)
    {
        if (!hasPlayerPosition || mapTexture == null)
            return;

        if (zoom < 2f)
            zoom = 2f;

        Vector2 pixel = GameToMapPixel(gameX, gameY);
        float baseScale = Mathf.Min(viewportWidth / mapTexture.width, viewportHeight / mapTexture.height);
        float scale = baseScale * zoom;
        float centeredX = (viewportWidth - mapTexture.width * scale) * 0.5f;
        float centeredY = (viewportHeight - mapTexture.height * scale) * 0.5f;
        pan.x = viewportWidth * 0.5f - centeredX - pixel.x * scale;
        pan.y = viewportHeight * 0.5f - centeredY - pixel.y * scale;
    }

    private void EnsureStyles()
    {
        if (brandStyle != null)
            return;

        brandStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 18,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = Color.white }
        };

        versionStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 10,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = MutedText }
        };

        statusStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 13,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleRight,
            normal = { textColor = AccentCyan }
        };

        hintStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 11,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = MutedText }
        };

        dockLabelStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 9,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = new Color(0.62f, 0.67f, 0.73f, 1f) }
        };

        compactButtonStyle = new GUIStyle(GUI.skin.button)
        {
            fontSize = 10,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter
        };
        compactButtonStyle.normal.textColor = new Color(0.94f, 0.96f, 0.98f, 1f);
        compactButtonStyle.hover.textColor = Color.white;
        compactButtonStyle.active.textColor = Color.white;
        compactButtonStyle.focused.textColor = Color.white;

        panelHeadingStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 16,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = Color.white }
        };

        panelSubtitleStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 11,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = MutedText }
        };

        cardHeadingStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 12,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = AccentYellow }
        };

        liveCardHeadingStyle = new GUIStyle(cardHeadingStyle);
        liveCardHeadingStyle.normal.textColor = AccentCyan;

        markerCardHeadingStyle = new GUIStyle(cardHeadingStyle);
        markerCardHeadingStyle.normal.textColor = AccentYellow;

        metricLabelStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 11,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = new Color(0.82f, 0.85f, 0.89f, 1f) }
        };

        metricValueStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 11,
            alignment = TextAnchor.MiddleRight,
            normal = { textColor = new Color(0.93f, 0.95f, 0.97f, 1f) }
        };

        emptyStateStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 11,
            wordWrap = true,
            alignment = TextAnchor.UpperLeft,
            normal = { textColor = MutedText }
        };

        mapMessageStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 18,
            wordWrap = true,
            alignment = TextAnchor.MiddleCenter,
            normal = { textColor = new Color(0.9f, 0.93f, 0.97f) }
        };

        gridLabelStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 11,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = new Color(1f, 1f, 1f, 0.9f) }
        };

        featureOutlineStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 29,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter,
            normal = { textColor = Color.white }
        };

        featureGlyphStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 22,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter,
            normal = { textColor = Color.white }
        };

        featureLabelStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 12,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = Color.white }
        };

        coordinateStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 12,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter,
            normal = { textColor = Color.white }
        };

        userMarkerOutlineStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 31,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter,
            normal = { textColor = Color.white }
        };

        userMarkerStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 23,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter,
            normal = { textColor = Color.white }
        };

        userMarkerLabelStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 12,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = new Color(1f, 0.84f, 0.38f, 1f) }
        };

        markerShadowStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 39,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter,
            normal = { textColor = new Color(0.01f, 0.015f, 0.02f, 0.98f) }
        };

        markerOuterStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 36,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter,
            normal = { textColor = Color.white }
        };

        markerStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 29,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter,
            normal = { textColor = AccentCyan }
        };

        markerCoreStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 12,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter,
            normal = { textColor = Color.white }
        };

        youLabelStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 13,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = new Color(0.45f, 0.9f, 1f) }
        };

        rulerPointOutlineStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 28,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter,
            normal = { textColor = Color.white }
        };

        rulerPointStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 20,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter,
            normal = { textColor = Color.white }
        };

        rulerLabelStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 13,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = new Color(1f, 0.9f, 0.48f) }
        };
    }

    public void OnDestroy()
    {
        if (overlayOpen)
            SetOverlayOpen(false);

        if (mapTexture != null)
        {
            UnityEngine.Object.Destroy(mapTexture);
            mapTexture = null;
        }
    }

    private enum MapTool
    {
        Pan,
        Marker,
        Ruler
    }

    private sealed class MapFeature
    {
        public readonly string Name;
        public readonly float X;
        public readonly float Y;
        public readonly Color Color;

        public MapFeature(string name, float x, float y, Color color)
        {
            Name = name;
            X = x;
            Y = y;
            Color = color;
        }
    }

    private sealed class UserMarker
    {
        public readonly int Id;
        public readonly float X;
        public readonly float Y;

        public UserMarker(int id, float x, float y)
        {
            Id = id;
            X = x;
            Y = y;
        }
    }
}
