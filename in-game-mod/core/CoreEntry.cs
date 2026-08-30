using System;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using BepInEx.Logging;
using Il2CppInterop.Runtime;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using UnityEngine;

namespace BigWalkHideSeek.Core;

public static class CoreEntry
{
    internal static ManualLogSource Logger;

    public static void Configure(ManualLogSource logger)
    {
        Logger = logger;
        Logger?.LogInfo("Big Walk Hide + Seek Core 0.0.9 configured.");
    }
}

public class HideSeekOverlay : MonoBehaviour
{
    private const string MapResourceName = "BigWalkHideSeek.Core.big-walk-map.png";
    private const float InvSqrt2 = 0.70710678118f;

    // Same game-coordinate -> map-pixel calibration used by the web app.
    private const double MapA = 1.01872096;
    private const double MapB = 0.00000814424539;
    private const double MapC = -934.160388;
    private const double MapD = -0.00223877926;
    private const double MapE = 1.01939961;
    private const double MapF = -3130.54945;

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

    private GUIStyle titleStyle;
    private GUIStyle subtitleStyle;
    private GUIStyle statusStyle;
    private GUIStyle hintStyle;
    private GUIStyle markerStyle;
    private GUIStyle markerShadowStyle;
    private GUIStyle mapMessageStyle;

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    [return: MarshalAs(UnmanagedType.I1)]
    private delegate bool LoadImageIcall(
        IntPtr texture,
        IntPtr data,
        [MarshalAs(UnmanagedType.I1)] bool markNonReadable
    );

    private static LoadImageIcall loadImageIcall;

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
                throw new FileNotFoundException($"Embedded map resource '{MapResourceName}' was not found.");

            using var memory = new MemoryStream();
            stream.CopyTo(memory);
            byte[] pngBytes = memory.ToArray();

            CoreEntry.Logger?.LogInfo($"Embedded map resource read: {pngBytes.Length} bytes.");

            mapTexture = new Texture2D(2, 2);
            Il2CppStructArray<byte> il2cppBytes = ToIl2CppByteArray(pngBytes);

            // Do NOT call ImageConversion.LoadImage here. On this Unity 6 / BepInEx
            // interop combination its generated wrapper references
            // Il2CppSystem.ReadOnlySpan<T>.GetPinnableReference(), which is missing at
            // runtime. Invoke Unity's native ImageConversion icall directly instead.
            if (!LoadImageDirect(mapTexture, il2cppBytes, false))
                throw new InvalidDataException("Unity could not decode the embedded map PNG.");

            mapTexture.wrapMode = TextureWrapMode.Clamp;
            mapTexture.filterMode = FilterMode.Bilinear;
            CoreEntry.Logger?.LogInfo($"Embedded Big Walk map loaded: {mapTexture.width}x{mapTexture.height}.");
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

    private static bool LoadImageDirect(Texture2D texture, Il2CppStructArray<byte> data, bool markNonReadable)
    {
        if (loadImageIcall == null)
        {
            const string fullSignature = "UnityEngine.ImageConversion::LoadImage(UnityEngine.Texture2D,System.Byte[],System.Boolean)";
            IntPtr icallPointer = IL2CPP.il2cpp_resolve_icall(fullSignature);

            if (icallPointer == IntPtr.Zero)
            {
                const string shortSignature = "UnityEngine.ImageConversion::LoadImage";
                icallPointer = IL2CPP.il2cpp_resolve_icall(shortSignature);
            }

            if (icallPointer == IntPtr.Zero)
                throw new MissingMethodException("Could not resolve UnityEngine.ImageConversion::LoadImage native icall.");

            loadImageIcall = Marshal.GetDelegateForFunctionPointer<LoadImageIcall>(icallPointer);
            CoreEntry.Logger?.LogInfo("Resolved direct native ImageConversion::LoadImage icall.");
        }

        return loadImageIcall(texture.Pointer, data.Pointer, markNonReadable);
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
        GUI.Label(new Rect(20f, 37f, 420f, 18f), "IN-GAME MAP · CORE v0.0.9", subtitleStyle);

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

        Rect controlRectGlobal = new Rect(viewport.x + 12f, viewport.y + 12f, 348f, 40f);
        HandleMapInput(viewport, controlRectGlobal);

        GUI.BeginGroup(viewport);

        Rect mapRect = GetMapRect(viewport.width, viewport.height);
        GUI.DrawTexture(mapRect, mapTexture, ScaleMode.StretchToFill, false);

        if (hasPlayerPosition)
            DrawPlayerMarker(mapRect);

        GUI.backgroundColor = new Color(0.08f, 0.095f, 0.12f, 0.96f);
        GUI.Box(new Rect(10f, 10f, 350f, 42f), GUIContent.none);
        GUI.backgroundColor = Color.white;

        if (GUI.Button(new Rect(16f, 15f, 62f, 32f), "FIT"))
            FitMap();

        GUI.enabled = hasPlayerPosition;
        if (GUI.Button(new Rect(84f, 15f, 102f, 32f), "CENTER ME"))
            CenterOnPlayer(viewport.width, viewport.height);
        GUI.enabled = true;

        if (GUI.Button(new Rect(192f, 15f, 42f, 32f), "−"))
            ZoomAt(viewport.width, viewport.height, new Vector2(viewport.width * 0.5f, viewport.height * 0.5f), 1f / 1.25f);

        if (GUI.Button(new Rect(240f, 15f, 42f, 32f), "+"))
            ZoomAt(viewport.width, viewport.height, new Vector2(viewport.width * 0.5f, viewport.height * 0.5f), 1.25f);

        GUI.Label(new Rect(291f, 19f, 60f, 24f), $"{zoom:0.0}×", hintStyle);
        GUI.Label(new Rect(12f, viewport.height - 28f, 520f, 20f), "Drag to pan  ·  Mouse wheel to zoom  ·  F7/Esc close", hintStyle);

        GUI.EndGroup();
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
}
