using System;
using BepInEx;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using UnityEngine;

[BepInPlugin("com.bigwalkhideseek.ingame", "Big Walk Hide + Seek", "0.0.4")]
public class Plugin : BasePlugin
{
    internal static ManualLogSource Logger;

    public override void Load()
    {
        Logger = Log;
        Logger.LogInfo("Big Walk Hide + Seek 0.0.4 loaded.");
        Logger.LogInfo("Press F7 to toggle the prototype overlay.");
        AddComponent<HideSeekOverlay>();
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
            // Big Walk normally owns the cursor. Keep our UI cursor available
            // while the Hide + Seek screen is open in case another game system
            // tries to relock it.
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

            EnterBigWalkUiMode();

            Cursor.visible = true;
            Cursor.lockState = CursorLockMode.None;
            Plugin.Logger.LogInfo("Hide + Seek overlay opened; Big Walk UI mode enabled.");
        }
        else
        {
            ExitBigWalkUiMode();

            // Keep the old cursor state as a fallback. Big Walk's own
            // SetToGameMode/SetLocked calls should normally own this.
            Cursor.visible = previousCursorVisible;
            Cursor.lockState = previousCursorLock;
            Plugin.Logger.LogInfo("Hide + Seek overlay closed; Big Walk game mode restored.");
        }
    }

    private static void EnterBigWalkUiMode()
    {
        // These are Big Walk's own menu/input switches discovered in its
        // generated Assembly-CSharp interop. Using them should disable player
        // look/movement the same way the game's native menus do.
        try
        {
            WorldManager.SetToUIMode();
        }
        catch (Exception ex)
        {
            Plugin.Logger.LogWarning($"WorldManager.SetToUIMode failed: {ex.Message}");
        }

        try
        {
            ControlsManager.SetMenuMode(true);
        }
        catch (Exception ex)
        {
            Plugin.Logger.LogWarning($"ControlsManager.SetMenuMode(true) failed: {ex.Message}");
        }

        try
        {
            CursorManager.SetFree();
        }
        catch (Exception ex)
        {
            Plugin.Logger.LogWarning($"CursorManager.SetFree failed: {ex.Message}");
        }
    }

    private static void ExitBigWalkUiMode()
    {
        try
        {
            ControlsManager.SetMenuMode(false);
        }
        catch (Exception ex)
        {
            Plugin.Logger.LogWarning($"ControlsManager.SetMenuMode(false) failed: {ex.Message}");
        }

        try
        {
            WorldManager.SetToGameMode();
        }
        catch (Exception ex)
        {
            Plugin.Logger.LogWarning($"WorldManager.SetToGameMode failed: {ex.Message}");
        }

        try
        {
            CursorManager.SetLocked();
        }
        catch (Exception ex)
        {
            Plugin.Logger.LogWarning($"CursorManager.SetLocked failed: {ex.Message}");
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
        GUILayout.Label("IN-GAME MOD PROTOTYPE", subtitleStyle);
        GUILayout.Space(32f);

        GUILayout.Label("Overlay foundation is working.", bodyStyle);
        GUILayout.Space(12f);
        GUILayout.Label(
            "This build now uses Big Walk's own UI mode while the overlay is open. The camera and player controls should stop reacting until the overlay closes.",
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
