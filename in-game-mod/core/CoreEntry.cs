using System;
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
        Logger?.LogInfo("Big Walk Hide + Seek Core 0.0.11 configured.");
    }
}

public class HideSeekOverlay : MonoBehaviour
{
    private const string MapResourceName = "BigWalkHideSeek.Core.big-walk-map.bgra";
    private const float InvSqrt2 = 0.70710678118f;

    // Same game-coordinate -> map-pixel calibration used by the web app.
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

    private GUIStyle titleStyle;
    private GUIStyle subtitleStyle;
    private GUIStyle statusStyle;
    private GUIStyle hintStyle;
    private GUIStyle markerStyle;
    private GUIStyle markerShadowStyle;
    private GUIStyle mapMessageStyle;
    private GUIStyle gridLabelStyle;
    private GUIStyle featureOutlineStyle;
    private GUIStyle featureGlyphStyle;
    private GUIStyle featureLabelStyle;
    private GUIStyle coordinateStyle;

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
        try
        {
            ControlsManager.SetMenuMode(true);
        }
        catch (Exception ex)
        {
            CoreEntry.Logger?.LogWarning($"ControlsManager.SetMenuMode(true) failed: {ex.Message}");
        }

        try
        {
            CursorManager.SetFree();
        }
        catch (Exception ex)
        {
            CoreEntry.Logger?.LogWarning($"CursorManager.SetFree failed: {ex.Message}");
        }
    }

    private static void ExitOverlayInputMode()
    {
        try
        {
            ControlsManager.SetMenuMode(false);
        }
        catch (Exception ex)
        {
            CoreEntry.Logger?.LogWarning($"ControlsManager.SetMenuMode(false) failed: {ex.Message}");
        }

        try
        {
            CursorManager.SetLocked();
        }
        catch (Exception ex)
        {
            CoreEntry.Logger?.LogWarning($"CursorManager.SetLocked failed: {ex.Message}");
        }
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

            CoreEntry.Logger?.LogInfo($"Embedded raw map read: {width}x{height}, {pixelBytes.Length} BGRA bytes.");

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
        float px = (float)(MapA * x + MapB * y + MapC);
        float py = (float)(MapD * x + MapE * y + MapF);
        return new Vector2(px, py);
    }

    private static Vector2 MapPixelToGame(float px, float py)
    {
        double det = MapA * MapE - MapB * MapD;
        double shiftedX = px - MapC;
        double shiftedY = py - MapF;
        float x = (float)((MapE * shiftedX - MapB * shiftedY) / det);
        float y = (float)((-MapD * shiftedX + MapA * shiftedY) / det);
        return new Vector2(x, y);
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
        GUI.Label(new Rect(20f, 37f, 420f, 18f), "IN-GAME MAP · CORE v0.0.11", subtitleStyle);

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

        const float controlWidth = 586f;
        Rect controlRectGlobal = new Rect(viewport.x + 10f, viewport.y + 10f, controlWidth, 42f);
        HandleMapInput(viewport, controlRectGlobal);

        Event evt = Event.current;
        Vector2 globalMouse = evt != null ? evt.mousePosition : new Vector2(-1000f, -1000f);
        bool canShowCoordinateTip = viewport.Contains(globalMouse) && !controlRectGlobal.Contains(globalMouse);
        Vector2 localMouse = new Vector2(globalMouse.x - viewport.x, globalMouse.y - viewport.y);

        GUI.BeginGroup(viewport);

        Rect mapRect = GetMapRect(viewport.width, viewport.height);
        GUI.DrawTexture(mapRect, mapTexture, ScaleMode.StretchToFill, false);

        if (showGrid)
            DrawGrid(mapRect);
        if (showTowers)
            DrawFeatures(mapRect, Towers, false);
        if (showLandmarks)
            DrawFeatures(mapRect, Landmarks, true);
        if (hasPlayerPosition)
            DrawPlayerMarker(mapRect);

        GUI.backgroundColor = new Color(0.08f, 0.095f, 0.12f, 0.96f);
        GUI.Box(new Rect(10f, 10f, controlWidth, 42f), GUIContent.none);
        GUI.backgroundColor = Color.white;

        float x = 16f;
        if (GUI.Button(new Rect(x, 15f, 54f, 32f), "FIT"))
            FitMap();
        x += 60f;

        GUI.enabled = hasPlayerPosition;
        if (GUI.Button(new Rect(x, 15f, 96f, 32f), "CENTER ME"))
            CenterOnPlayer(viewport.width, viewport.height);
        GUI.enabled = true;
        x += 102f;

        if (GUI.Button(new Rect(x, 15f, 36f, 32f), "−"))
            ZoomAt(viewport.width, viewport.height, new Vector2(viewport.width * 0.5f, viewport.height * 0.5f), 1f / 1.25f);
        x += 42f;

        if (GUI.Button(new Rect(x, 15f, 36f, 32f), "+"))
            ZoomAt(viewport.width, viewport.height, new Vector2(viewport.width * 0.5f, viewport.height * 0.5f), 1.25f);
        x += 42f;

        GUI.Label(new Rect(x, 19f, 52f, 24f), $"{zoom:0.0}×", hintStyle);
        x += 64f;

        showGrid = DrawToggleButton(new Rect(x, 15f, 64f, 32f), "GRID", showGrid);
        x += 70f;
        showTowers = DrawToggleButton(new Rect(x, 15f, 80f, 32f), "TOWERS", showTowers);
        x += 86f;
        showLandmarks = DrawToggleButton(new Rect(x, 15f, 104f, 32f), "LANDMARKS", showLandmarks);

        if (canShowCoordinateTip)
            DrawCoordinateTip(localMouse, mapRect, viewport.width, viewport.height);

        GUI.Label(new Rect(12f, viewport.height - 28f, 700f, 20f), "Drag to pan  ·  Mouse wheel to zoom  ·  Hover for Y/X coordinates  ·  F7/Esc close", hintStyle);

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

    private Rect GetMapRect(float viewportWidth, float viewportHeight)
    {
        float baseScale = Mathf.Min(viewportWidth / mapTexture.width, viewportHeight / mapTexture.height);
        float scale = baseScale * zoom;
        float width = mapTexture.width * scale;
        float height = mapTexture.height * scale;
        float x = (viewportWidth - width) * 0.5f + pan.x;
        float y = (viewportHeight - height) * 0.5f + pan.y;
        return new Rect(x, y, width, height);
    }

    private Vector2 GameToOverlayPoint(Rect mapRect, float x, float y)
    {
        Vector2 pixel = GameToMapPixel(x, y);
        return new Vector2(
            mapRect.x + (pixel.x / mapTexture.width) * mapRect.width,
            mapRect.y + (pixel.y / mapTexture.height) * mapRect.height
        );
    }

    private void DrawGrid(Rect mapRect)
    {
        Color lineColor = new Color(1f, 1f, 1f, 0.62f);

        for (int x = 1000; x <= 2400; x += 100)
        {
            Vector2 a = GameToOverlayPoint(mapRect, x, 3000f);
            Vector2 b = GameToOverlayPoint(mapRect, x, 4600f);
            DrawLine(a, b, lineColor, 1f);

            Vector2 label = GameToOverlayPoint(mapRect, x, 3110f);
            GUI.Label(new Rect(label.x + 3f, label.y - 9f, 34f, 18f), (x / 100).ToString(), gridLabelStyle);
        }

        for (int y = 3100; y <= 4500; y += 100)
        {
            Vector2 a = GameToOverlayPoint(mapRect, 900f, y);
            Vector2 b = GameToOverlayPoint(mapRect, 2500f, y);
            DrawLine(a, b, lineColor, 1f);

            Vector2 label = GameToOverlayPoint(mapRect, 1005f, y);
            GUI.Label(new Rect(label.x + 3f, label.y - 16f, 34f, 18f), (y / 100).ToString(), gridLabelStyle);
        }
    }

    private void DrawFeatures(Rect mapRect, MapFeature[] features, bool diamond)
    {
        string glyph = diamond ? "◆" : "●";

        foreach (MapFeature feature in features)
        {
            Vector2 point = GameToOverlayPoint(mapRect, feature.X, feature.Y);
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

    private void DrawCoordinateTip(Vector2 localMouse, Rect mapRect, float viewportWidth, float viewportHeight)
    {
        if (!mapRect.Contains(localMouse))
            return;

        float px = ((localMouse.x - mapRect.x) / mapRect.width) * mapTexture.width;
        float py = ((localMouse.y - mapRect.y) / mapRect.height) * mapTexture.height;
        Vector2 game = MapPixelToGame(px, py);

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

    private static void DrawLine(Vector2 start, Vector2 end, Color color, float width)
    {
        Vector2 delta = end - start;
        float length = delta.magnitude;
        if (length < 0.01f)
            return;

        Matrix4x4 oldMatrix = GUI.matrix;
        Color oldColor = GUI.color;
        float angle = Mathf.Atan2(delta.y, delta.x) * Mathf.Rad2Deg;

        GUIUtility.RotateAroundPivot(angle, start);
        GUI.color = color;
        GUI.DrawTexture(new Rect(start.x, start.y - width * 0.5f, length, width), Texture2D.whiteTexture);
        GUI.matrix = oldMatrix;
        GUI.color = oldColor;
    }

    private void DrawPlayerMarker(Rect mapRect)
    {
        Vector2 pixel = GameToMapPixel(gameX, gameY);
        float sx = mapRect.x + (pixel.x / mapTexture.width) * mapRect.width;
        float sy = mapRect.y + (pixel.y / mapTexture.height) * mapRect.height;

        if (sx < -30f || sy < -30f || sx > mapRect.xMax + 30f || sy > mapRect.yMax + 30f)
            return;

        Rect shadow = new Rect(sx - 16f, sy - 19f, 32f, 32f);
        GUI.Label(new Rect(shadow.x - 1f, shadow.y, shadow.width, shadow.height), "●", markerShadowStyle);
        GUI.Label(new Rect(shadow.x + 1f, shadow.y, shadow.width, shadow.height), "●", markerShadowStyle);
        GUI.Label(new Rect(shadow.x, shadow.y - 1f, shadow.width, shadow.height), "●", markerShadowStyle);
        GUI.Label(new Rect(shadow.x, shadow.y + 1f, shadow.width, shadow.height), "●", markerShadowStyle);
        GUI.Label(shadow, "●", markerStyle);
    }

    private void HandleMapInput(Rect viewport, Rect controlRectGlobal)
    {
        Event evt = Event.current;
        if (evt == null || evt.type == EventType.Used)
            return;

        Vector2 mouse = evt.mousePosition;
        if (!viewport.Contains(mouse) || controlRectGlobal.Contains(mouse))
            return;

        Vector2 localMouse = new Vector2(mouse.x - viewport.x, mouse.y - viewport.y);

        if (evt.type == EventType.ScrollWheel)
        {
            float factor = evt.delta.y > 0f ? 1f / 1.18f : 1.18f;
            ZoomAt(viewport.width, viewport.height, localMouse, factor);
            evt.Use();
            return;
        }

        if (evt.type == EventType.MouseDrag && evt.button == 0)
        {
            pan += evt.delta;
            evt.Use();
        }
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
            fontSize = 27,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter,
            normal = { textColor = new Color(0.02f, 0.03f, 0.04f, 0.95f) }
        };

        markerStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 27,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter,
            normal = { textColor = new Color(0.24f, 0.82f, 1f) }
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
}
