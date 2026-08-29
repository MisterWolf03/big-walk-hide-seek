using System;
using BepInEx.Logging;
using UnityEngine;

namespace BigWalkHideSeek.Core;

public static class CoreEntry
{
    internal static ManualLogSource Logger;

    public static void Configure(ManualLogSource logger)
    {
        Logger = logger;
        Logger?.LogInfo("Big Walk Hide + Seek Core 0.0.6 configured.");
    }
}

public class HideSeekOverlay : MonoBehaviour
{
    private bool overlayOpen;
    private bool previousCursorVisible;
    private CursorLockMode previousCursorLock;

    private GUIStyle titleStyle;
    private GUIStyle subtitleStyle;
    private GUIStyle bodyStyle;
    private GUIStyle hintStyle;
    private GUIStyle closeButtonStyle;

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

        if (overlayOpen)
        {
            Cursor.visible = true;
            Cursor.lockState = CursorLockMode.None;
        }
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
            CoreEntry.Logger?.LogInfo("Hide + Seek overlay opened; ControlsManager menu mode enabled.");
        }
        else
        {
            ExitOverlayInputMode();

            Cursor.visible = previousCursorVisible;
            Cursor.lockState = previousCursorLock;
            CoreEntry.Logger?.LogInfo("Hide + Seek overlay closed; ControlsManager menu mode released.");
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

    public void OnGUI()
    {
        if (!overlayOpen)
            return;

        EnsureStyles();

        GUI.depth = -10000;

        Color oldColor = GUI.color;
        Color oldBackground = GUI.backgroundColor;

        GUI.color = new Color(1f, 1f, 1f, 0.98f);
        GUI.backgroundColor = new Color(0.055f, 0.067f, 0.086f, 0.98f);
        GUI.Box(new Rect(0f, 0f, Screen.width, Screen.height), GUIContent.none);

        float panelWidth = Mathf.Min(920f, Screen.width - 80f);
        float panelHeight = Mathf.Min(560f, Screen.height - 80f);
        float left = (Screen.width - panelWidth) * 0.5f;
        float top = (Screen.height - panelHeight) * 0.5f;
        Rect panel = new Rect(left, top, panelWidth, panelHeight);

        GUI.backgroundColor = new Color(0.10f, 0.12f, 0.15f, 1f);
        GUI.Box(panel, GUIContent.none);

        GUILayout.BeginArea(new Rect(panel.x + 34f, panel.y + 28f, panel.width - 68f, panel.height - 56f));

        GUILayout.Label("BIG WALK HIDE + SEEK", titleStyle);
        GUILayout.Space(6f);
        GUILayout.Label("AUTO-UPDATE CORE TEST · v0.0.6", subtitleStyle);
        GUILayout.Space(32f);

        GUILayout.Label("Loader → Core architecture is running.", bodyStyle);
        GUILayout.Space(12f);
        GUILayout.Label(
            "If this screen behaves exactly like the previous working build, the permanent Loader successfully loaded the separately updateable Core. Future map and game features will live in Core.",
            bodyStyle
        );

        GUILayout.FlexibleSpace();

        GUILayout.Label("F7  Toggle overlay     •     Esc  Close", hintStyle);
        GUILayout.Space(18f);

        if (GUILayout.Button("CLOSE OVERLAY", closeButtonStyle, GUILayout.Height(46f)))
            SetOverlayOpen(false);

        GUILayout.EndArea();

        GUI.color = oldColor;
        GUI.backgroundColor = oldBackground;

        Event evt = Event.current;
        if (evt != null && (evt.isMouse || evt.type == EventType.ScrollWheel))
            evt.Use();
    }

    private void EnsureStyles()
    {
        if (titleStyle != null)
            return;

        titleStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 34,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter,
            normal = { textColor = new Color(0.95f, 0.79f, 0.30f) }
        };

        subtitleStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 13,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter,
            normal = { textColor = new Color(0.68f, 0.72f, 0.78f) }
        };

        bodyStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 18,
            wordWrap = true,
            alignment = TextAnchor.UpperCenter,
            normal = { textColor = new Color(0.94f, 0.96f, 0.98f) }
        };

        hintStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 14,
            alignment = TextAnchor.MiddleCenter,
            normal = { textColor = new Color(0.68f, 0.72f, 0.78f) }
        };

        closeButtonStyle = new GUIStyle(GUI.skin.button)
        {
            fontSize = 15,
            fontStyle = FontStyle.Bold
        };
    }

    public void OnDestroy()
    {
        if (overlayOpen)
            SetOverlayOpen(false);
    }
}
