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
        Logger?.LogInfo("Big Walk Hide + Seek Core 0.0.14 configured.");
    }
}

public class HideSeekOverlay : MonoBehaviour
{
    private const string MapResourceName = "BigWalkHideSeek.Core.big-walk-map.bgra";
    private const float InvSqrt2 = 0.70710678118f;

    private const double MapA = 1.01872096;
    private const double MapB = 0.00000814424539;
    private const double MapC = -934.160388;
    private const double MapD = -0.00223877926;
    private const double MapE = 1.01939961;
    private const double MapF = -3130.54945;

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

    private GUIStyle titleStyle;
    private GUIStyle subtitleStyle;
    private GUIStyle statusStyle;
    private GUIStyle hintStyle;
    private GUIStyle markerShadowStyle;
    private GUIStyle markerOuterStyle;
    private GUIStyle markerStyle;
    private GUIStyle markerCoreStyle;
    private GUIStyle youLabelStyle;
    private GUIStyle mapMessageStyle;
    private GUIStyle gridLabelStyle;
    private GUIStyle featureOutlineStyle;
    private GUIStyle featureGlyphStyle;
    private GUIStyle featureLabelStyle;
    private GUIStyle coordinateStyle;
    private GUIStyle userMarkerOutlineStyle;
    private GUIStyle userMarkerStyle;
    private GUIStyle userMarkerLabelStyle;
    private GUIStyle markerPanelTitleStyle;
    private GUIStyle markerPanelValueStyle;
    private GUIStyle livePanelTitleStyle;
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

        GUI.color = new Color(0.035f, 0.043f, 0.055f, 0.985f);
        GUI.Box(new Rect(0f, 0f, Screen.width, Screen.height), GUIContent.none);
        GUI.color = Color.white;

        DrawTopBar();
        Rect viewport = new Rect(14f, 66f, Mathf.Max(100f, Screen.width - 28f), Mathf.Max(100f, Screen.height - 90f));
        DrawMap(viewport);

        GUI.color = oldColor;
        GUI.backgroundColor = oldBackground;

        Event evt = Event.current;
        if (evt != null && (evt.isMouse || evt.type == EventType.ScrollWheel))
            evt.Use();
    }

    private void DrawTopBar()
    {
        GUI.Label(new Rect(18f, 8f, 430f, 30f), "BIG WALK HIDE + SEEK", titleStyle);
        GUI.Label(new Rect(20f, 37f, 420f, 18f), "IN-GAME MAP · CORE v0.0.14", subtitleStyle);

        string status = hasPlayerPosition
            ? $"LIVE  ·  X {gameX:0}   Y {gameY:0}"
            : "SEARCHING FOR PLAYER…";
        GUI.Label(new Rect(Mathf.Max(460f, Screen.width - 500f), 15f, 360f, 28f), status, statusStyle);

        if (GUI.Button(new Rect(Screen.width - 116f, 12f, 96f, 38f), "CLOSE"))
            SetOverlayOpen(false);
    }

    private void DrawMap(Rect viewport)
    {
        GUI.backgroundColor = new Color(0.015f, 0.02f, 0.028f, 1f);
        GUI.Box(viewport, GUIContent.none);
        GUI.backgroundColor = Color.white;

        if (mapTexture == null)
        {
            string message = string.IsNullOrEmpty(mapLoadError)
                ? "Loading Big Walk map…"
                : $"Map failed to load\n{mapLoadError}";
            GUI.Label(viewport, message, mapMessageStyle);
            return;
        }

        const float controlWidth = 808f;
        const float sidePanelWidth = 276f;
        const float playerPanelY = 62f;
        const float playerPanelHeight = 142f;
        const float markerPanelY = 212f;
        const float markerPanelHeight = 172f;
        float rulerPanelY = userMarkers.Count > 0 ? 392f : 212f;
        const float rulerPanelHeight = 146f;

        Rect controlRectGlobal = new Rect(viewport.x + 10f, viewport.y + 10f, controlWidth, 42f);
        Rect playerPanelGlobal = new Rect(viewport.x + viewport.width - sidePanelWidth - 10f, viewport.y + playerPanelY, sidePanelWidth, playerPanelHeight);
        Rect markerPanelGlobal = userMarkers.Count > 0
            ? new Rect(viewport.x + viewport.width - sidePanelWidth - 10f, viewport.y + markerPanelY, sidePanelWidth, markerPanelHeight)
            : new Rect(-1000f, -1000f, 0f, 0f);
        Rect rulerPanelGlobal = (activeTool == MapTool.Ruler || hasRulerA)
            ? new Rect(viewport.x + viewport.width - sidePanelWidth - 10f, viewport.y + rulerPanelY, sidePanelWidth, rulerPanelHeight)
            : new Rect(-1000f, -1000f, 0f, 0f);

        Rect mapRect = GetMapRect(viewport.width, viewport.height);
        HandleMapInput(viewport, controlRectGlobal, playerPanelGlobal, markerPanelGlobal, rulerPanelGlobal, mapRect);

        Event evt = Event.current;
        Vector2 globalMouse = evt != null ? evt.mousePosition : new Vector2(-1000f, -1000f);
        bool canShowCoordinateTip = viewport.Contains(globalMouse)
            && !controlRectGlobal.Contains(globalMouse)
            && !playerPanelGlobal.Contains(globalMouse)
            && !markerPanelGlobal.Contains(globalMouse)
            && !rulerPanelGlobal.Contains(globalMouse);
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

        GUI.backgroundColor = new Color(0.08f, 0.095f, 0.12f, 0.96f);
        GUI.Box(new Rect(10f, 10f, controlWidth, 42f), GUIContent.none);
        GUI.backgroundColor = Color.white;

        float x = 16f;
        if (GUI.Button(new Rect(x, 15f, 54f, 32f), "FIT")) FitMap();
        x += 60f;

        GUI.enabled = hasPlayerPosition;
        if (GUI.Button(new Rect(x, 15f, 96f, 32f), "CENTER ME")) CenterOnPlayer(viewport.width, viewport.height);
        GUI.enabled = true;
        x += 102f;

        if (GUI.Button(new Rect(x, 15f, 36f, 32f), "−"))
            ZoomAt(viewport.width, viewport.height, new Vector2(viewport.width * 0.5f, viewport.height * 0.5f), 1f / 1.25f);
        x += 42f;

        if (GUI.Button(new Rect(x, 15f, 36f, 32f), "+"))
            ZoomAt(viewport.width, viewport.height, new Vector2(viewport.width * 0.5f, viewport.height * 0.5f), 1.25f);
        x += 42f;

        GUI.Label(new Rect(x, 19f, 48f, 24f), $"{zoom:0.0}×", hintStyle);
        x += 54f;

        if (DrawToolButton(new Rect(x, 15f, 54f, 32f), "PAN", activeTool == MapTool.Pan))
            activeTool = MapTool.Pan;
        x += 60f;
        if (DrawToolButton(new Rect(x, 15f, 76f, 32f), "MARKER", activeTool == MapTool.Marker))
            activeTool = MapTool.Marker;
        x += 82f;
        if (DrawToolButton(new Rect(x, 15f, 70f, 32f), "RULER", activeTool == MapTool.Ruler))
            activeTool = MapTool.Ruler;
        x += 76f;

        showGrid = DrawToggleButton(new Rect(x, 15f, 64f, 32f), "GRID", showGrid);
        x += 70f;
        showTowers = DrawToggleButton(new Rect(x, 15f, 80f, 32f), "TOWERS", showTowers);
        x += 86f;
        showLandmarks = DrawToggleButton(new Rect(x, 15f, 104f, 32f), "LANDMARKS", showLandmarks);

        DrawPlayerInfoPanel(viewport.width, sidePanelWidth, playerPanelY, playerPanelHeight);

        if (userMarkers.Count > 0)
            DrawMarkerPanel(viewport.width, sidePanelWidth, markerPanelY, markerPanelHeight);

        if (activeTool == MapTool.Ruler || hasRulerA)
            DrawRulerPanel(viewport.width, sidePanelWidth, rulerPanelY, rulerPanelHeight);

        if (canShowCoordinateTip)
            DrawCoordinateTip(localMouse, mapRect, viewport.width, viewport.height);

        string hint;
        if (activeTool == MapTool.Marker)
            hint = "MARKER mode · Click map to place · Click marker to select · Mouse wheel to zoom · F7/Esc close";
        else if (activeTool == MapTool.Ruler)
            hint = "RULER mode · Click A, then B · Third click starts a new ruler · Mouse wheel to zoom · F7/Esc close";
        else
            hint = "PAN mode · Drag to pan · Click marker to select · Mouse wheel to zoom · F7/Esc close";
        GUI.Label(new Rect(12f, viewport.height - 28f, 980f, 20f), hint, hintStyle);

        GUI.EndGroup();
    }

    private bool DrawToggleButton(Rect rect, string label, bool value)
    {
        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = value
            ? new Color(0.28f, 0.47f, 0.34f, 1f)
            : new Color(0.16f, 0.18f, 0.22f, 1f);
        bool clicked = GUI.Button(rect, label);
        GUI.backgroundColor = oldBackground;
        return clicked ? !value : value;
    }

    private bool DrawToolButton(Rect rect, string label, bool active)
    {
        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = active
            ? new Color(0.18f, 0.48f, 0.67f, 1f)
            : new Color(0.16f, 0.18f, 0.22f, 1f);
        bool clicked = GUI.Button(rect, label);
        GUI.backgroundColor = oldBackground;
        return clicked;
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
            GUI.color = new Color(1f, 0.76f, 0.18f, 1f);
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

    private void DrawPlayerInfoPanel(float viewportWidth, float panelWidth, float panelY, float panelHeight)
    {
        Rect panel = new Rect(viewportWidth - panelWidth - 10f, panelY, panelWidth, panelHeight);
        DrawInfoPanelBackground(panel);
        GUI.Label(new Rect(panel.x + 12f, panel.y + 8f, panel.width - 24f, 20f), "YOU · LIVE NAVIGATION", livePanelTitleStyle);

        if (!hasPlayerPosition)
        {
            GUI.Label(new Rect(panel.x + 12f, panel.y + 36f, panel.width - 24f, 40f), "Searching for PlayerCharacter…", markerPanelValueStyle);
            return;
        }

        MapFeature nearest = NearestTowerAt(gameX, gameY, out float distance);
        BearingInfo(gameX, gameY, nearest.X, nearest.Y, out float degrees, out string direction);

        GUI.Label(new Rect(panel.x + 12f, panel.y + 31f, panel.width - 24f, 18f), $"Coordinates: Y {gameY:0}, X {gameX:0}", markerPanelValueStyle);
        GUI.Label(new Rect(panel.x + 12f, panel.y + 50f, panel.width - 24f, 18f), $"Grid square: {GridSquare(gameX, gameY)}", markerPanelValueStyle);
        GUI.Label(new Rect(panel.x + 12f, panel.y + 69f, panel.width - 24f, 18f), $"Nearest tower: {nearest.Name}", markerPanelValueStyle);
        GUI.Label(new Rect(panel.x + 12f, panel.y + 88f, panel.width - 24f, 18f), $"Tower distance: {distance:0} units", markerPanelValueStyle);
        GUI.Label(new Rect(panel.x + 12f, panel.y + 107f, panel.width - 24f, 18f), $"Tower direction: {direction} ({degrees:0}°)", markerPanelValueStyle);
    }

    private void DrawMarkerPanel(float viewportWidth, float panelWidth, float panelY, float panelHeight)
    {
        Rect panel = new Rect(viewportWidth - panelWidth - 10f, panelY, panelWidth, panelHeight);
        DrawInfoPanelBackground(panel);

        UserMarker active = GetActiveMarker();
        GUI.Label(new Rect(panel.x + 12f, panel.y + 8f, panel.width - 24f, 20f), $"MARKERS · {userMarkers.Count}", markerPanelTitleStyle);

        if (active != null)
        {
            MapFeature nearest = NearestTowerAt(active.X, active.Y, out float distance);
            BearingInfo(active.X, active.Y, nearest.X, nearest.Y, out float degrees, out string direction);

            GUI.Label(new Rect(panel.x + 12f, panel.y + 29f, panel.width - 24f, 18f), $"Active: M{active.Id}", markerPanelValueStyle);
            GUI.Label(new Rect(panel.x + 12f, panel.y + 47f, panel.width - 24f, 18f), $"Coordinates: Y {active.Y:0}, X {active.X:0}", markerPanelValueStyle);
            GUI.Label(new Rect(panel.x + 12f, panel.y + 65f, panel.width - 24f, 18f), $"Grid square: {GridSquare(active.X, active.Y)}", markerPanelValueStyle);
            GUI.Label(new Rect(panel.x + 12f, panel.y + 83f, panel.width - 24f, 18f), $"Nearest tower: {nearest.Name}", markerPanelValueStyle);
            GUI.Label(new Rect(panel.x + 12f, panel.y + 101f, panel.width - 24f, 18f), $"Distance: {distance:0} units · {direction} ({degrees:0}°)", markerPanelValueStyle);
        }
        else
        {
            GUI.Label(new Rect(panel.x + 12f, panel.y + 42f, panel.width - 24f, 20f), "Click a marker to select it", markerPanelValueStyle);
        }

        GUI.enabled = active != null;
        if (GUI.Button(new Rect(panel.x + 12f, panel.y + 137f, 118f, 26f), "REMOVE ACTIVE"))
            RemoveActiveMarker();
        GUI.enabled = true;

        if (GUI.Button(new Rect(panel.x + 138f, panel.y + 137f, 126f, 26f), "CLEAR ALL"))
            ClearAllMarkers();
    }

    private static void DrawInfoPanelBackground(Rect panel)
    {
        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = new Color(0.055f, 0.065f, 0.085f, 0.97f);
        GUI.Box(panel, GUIContent.none);
        GUI.backgroundColor = oldBackground;
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

        Rect labelRect = new Rect(point.x + 12f, point.y - 10f, 28f, 20f);
        GUI.Label(labelRect, label, rulerLabelStyle);
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

    private void DrawRulerPanel(float viewportWidth, float panelWidth, float panelY, float panelHeight)
    {
        Rect panel = new Rect(viewportWidth - panelWidth - 10f, panelY, panelWidth, panelHeight);
        DrawInfoPanelBackground(panel);
        GUI.Label(new Rect(panel.x + 12f, panel.y + 8f, panel.width - 24f, 20f), "DISTANCE + BEARING", markerPanelTitleStyle);

        if (!hasRulerA)
        {
            GUI.Label(new Rect(panel.x + 12f, panel.y + 36f, panel.width - 24f, 38f), "RULER mode: click point A, then point B.", markerPanelValueStyle);
        }
        else if (!hasRulerB)
        {
            GUI.Label(new Rect(panel.x + 12f, panel.y + 32f, panel.width - 24f, 18f), $"Point A: Y {rulerA.y:0}, X {rulerA.x:0}", markerPanelValueStyle);
            GUI.Label(new Rect(panel.x + 12f, panel.y + 54f, panel.width - 24f, 18f), "Click point B to measure.", markerPanelValueStyle);
        }
        else
        {
            float distance = Vector2.Distance(rulerA, rulerB);
            BearingInfo(rulerA.x, rulerA.y, rulerB.x, rulerB.y, out float degrees, out string direction);
            GUI.Label(new Rect(panel.x + 12f, panel.y + 29f, panel.width - 24f, 18f), $"Point A: Y {rulerA.y:0}, X {rulerA.x:0}", markerPanelValueStyle);
            GUI.Label(new Rect(panel.x + 12f, panel.y + 47f, panel.width - 24f, 18f), $"Point B: Y {rulerB.y:0}, X {rulerB.x:0}", markerPanelValueStyle);
            GUI.Label(new Rect(panel.x + 12f, panel.y + 65f, panel.width - 24f, 18f), $"Distance: {distance:0} units", markerPanelValueStyle);
            GUI.Label(new Rect(panel.x + 12f, panel.y + 83f, panel.width - 24f, 18f), $"Bearing A → B: {direction} ({degrees:0}°)", markerPanelValueStyle);
        }

        GUI.enabled = hasRulerA;
        if (GUI.Button(new Rect(panel.x + 12f, panel.y + 111f, panel.width - 24f, 26f), "CLEAR RULER"))
            ClearRuler();
        GUI.enabled = true;
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

        Color oldBackground = GUI.backgroundColor;
        GUI.backgroundColor = new Color(0.03f, 0.04f, 0.055f, 0.96f);
        GUI.Box(tip, GUIContent.none);
        GUI.backgroundColor = oldBackground;
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

    private void HandleMapInput(Rect viewport, Rect controlRectGlobal, Rect playerPanelGlobal, Rect markerPanelGlobal, Rect rulerPanelGlobal, Rect mapRect)
    {
        Event evt = Event.current;
        if (evt == null || evt.type == EventType.Used)
            return;

        Vector2 mouse = evt.mousePosition;
        if (!viewport.Contains(mouse)
            || controlRectGlobal.Contains(mouse)
            || playerPanelGlobal.Contains(mouse)
            || markerPanelGlobal.Contains(mouse)
            || rulerPanelGlobal.Contains(mouse))
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
        if (titleStyle != null)
            return;

        titleStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 25,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = new Color(0.95f, 0.66f, 0.08f) }
        };

        subtitleStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 11,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = new Color(0.58f, 0.65f, 0.74f) }
        };

        statusStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 14,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleRight,
            normal = { textColor = new Color(0.74f, 0.92f, 1f) }
        };

        hintStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 12,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = new Color(0.72f, 0.77f, 0.84f) }
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
            normal = { textColor = new Color(0.14f, 0.82f, 1f) }
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

        markerPanelTitleStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 12,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = new Color(1f, 0.76f, 0.18f, 1f) }
        };

        markerPanelValueStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 12,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = new Color(0.9f, 0.93f, 0.97f) }
        };

        livePanelTitleStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 12,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleLeft,
            normal = { textColor = new Color(0.38f, 0.87f, 1f) }
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
