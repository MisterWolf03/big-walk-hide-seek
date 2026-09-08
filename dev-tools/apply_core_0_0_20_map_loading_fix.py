from pathlib import Path

core_path = Path('in-game-mod/core/CoreEntry.cs')
proj_path = Path('in-game-mod/core/BigWalkHideSeek.Core.csproj')
s = core_path.read_text(encoding='utf-8')
p = proj_path.read_text(encoding='utf-8')


def once(old, new, label):
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly 1 match, found {count}')
    s = s.replace(old, new, 1)

# Version bump.
s = s.replace('0.0.19', '0.0.20')
p = p.replace('<Version>0.0.19</Version>', '<Version>0.0.20</Version>')
p = p.replace('<AssemblyVersion>0.0.19.0</AssemblyVersion>', '<AssemblyVersion>0.0.20.0</AssemblyVersion>')
p = p.replace('<FileVersion>0.0.19.0</FileVersion>', '<FileVersion>0.0.20.0</FileVersion>')

once(
'''    private bool mapLoadAttempted;
    private string mapLoadError = string.Empty;
''',
'''    private bool mapLoadAttempted;
    private string mapLoadError = string.Empty;
    private float nextMapLoadAttemptAt;
''',
'map retry field')

once(
'''        EnsureInitialized();
        UpdateMatchTimer();

        bool needsPosition = overlayOpen
''',
'''        EnsureInitialized();
        UpdateMatchTimer();

        // Texture creation/loading belongs in the normal Unity update loop.
        // 0.0.19 attempted this from OnGUI for the passive mini-map, which can
        // leave the one-shot loader stuck before the texture becomes usable.
        if (overlayOpen || settings.MiniMapEnabled)
            EnsureMapTexture();

        bool needsPosition = overlayOpen
''',
'update map loading')

old_loader = '''    private void EnsureMapTexture()
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
'''

new_loader = '''    private void EnsureMapTexture()
    {
        if (mapTexture != null)
            return;

        float now = Time.unscaledTime;
        if (now < nextMapLoadAttemptAt)
            return;

        // Never permanently poison map loading after one transient failure.
        // Retry every few seconds until the embedded texture is available.
        nextMapLoadAttemptAt = now + 3f;
        mapLoadAttempted = true;
        mapLoadError = string.Empty;

        try
        {
            Assembly assembly = typeof(HideSeekOverlay).Assembly;
            string resolvedResourceName = MapResourceName;
            Stream stream = assembly.GetManifestResourceStream(resolvedResourceName);

            if (stream == null)
            {
                foreach (string resourceName in assembly.GetManifestResourceNames())
                {
                    if (!resourceName.EndsWith("big-walk-map.bgra", StringComparison.OrdinalIgnoreCase))
                        continue;

                    resolvedResourceName = resourceName;
                    stream = assembly.GetManifestResourceStream(resourceName);
                    if (stream != null)
                        break;
                }
            }

            if (stream == null)
                throw new FileNotFoundException($"Embedded raw map resource '{MapResourceName}' was not found in Core 0.0.20.");

            using (stream)
            using (var memory = new MemoryStream())
            {
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
            }

            mapLoadError = string.Empty;
            nextMapLoadAttemptAt = float.PositiveInfinity;
            CoreEntry.Logger?.LogInfo($"Embedded Big Walk map loaded from '{resolvedResourceName}': {mapTexture.width}x{mapTexture.height}.");
        }
        catch (Exception ex)
        {
            mapLoadError = ex.Message;
            CoreEntry.Logger?.LogError($"Could not load embedded Big Walk map; retrying in 3 seconds: {ex}");
            if (mapTexture != null)
            {
                UnityEngine.Object.Destroy(mapTexture);
                mapTexture = null;
            }
        }
    }
'''

once(old_loader, new_loader, 'map loader')

once(
'''        if (!overlayOpen)
        {
            if (settings.MiniMapEnabled || settings.NavHudEnabled || (settings.MissionHudEnabled && missionActive))
            {
                if (settings.MiniMapEnabled)
                    EnsureMapTexture();
                DrawPassiveHud();
            }

            DrawNotifications();
''',
'''        if (!overlayOpen)
        {
            if (settings.MiniMapEnabled || settings.NavHudEnabled || (settings.MissionHudEnabled && missionActive))
                DrawPassiveHud();

            DrawNotifications();
''',
'passive OnGUI load removal')

once(
'''        EnsureMapTexture();

        GUI.color = PageBackground;
''',
'''        GUI.color = PageBackground;
''',
'overlay OnGUI load removal')

once(
'''        if (settings.MiniMapEnabled && mapTexture != null)
            DrawMiniMap(miniMapRect);

        if (settings.NavHudEnabled)
''',
'''        if (settings.MiniMapEnabled)
        {
            if (mapTexture != null)
                DrawMiniMap(miniMapRect);
            else
                DrawMiniMapPlaceholder(miniMapRect);
        }

        if (settings.NavHudEnabled)
''',
'minimap placeholder hook')

placeholder = '''    private void DrawMiniMapPlaceholder(Rect rect)
    {
        DrawPanelRect(rect, new Color(0.045f, 0.055f, 0.07f, 0.94f), BorderColor);
        string title = mapLoadAttempted ? "MAP RETRYING…" : "MAP LOADING…";
        GUI.Label(new Rect(rect.x + 8f, rect.y + 49f, rect.width - 16f, 24f), title, statusStyle);

        if (!string.IsNullOrEmpty(mapLoadError))
        {
            GUI.Label(new Rect(rect.x + 10f, rect.y + 78f, rect.width - 20f, 58f),
                mapLoadError, emptyStateStyle);
        }
    }

'''
once('    private void DrawMiniMap(Rect rect)\n', placeholder + '    private void DrawMiniMap(Rect rect)\n', 'minimap placeholder method')

once(
'''            string message = string.IsNullOrEmpty(mapLoadError)
                ? "Loading Big Walk map…"
                : $"Map failed to load\\n{mapLoadError}";
''',
'''            string message = string.IsNullOrEmpty(mapLoadError)
                ? "Loading Big Walk map…"
                : $"Map load retrying…\\n{mapLoadError}";
''',
'fullscreen retry message')

core_path.write_text(s, encoding='utf-8')
proj_path.write_text(p, encoding='utf-8')
print('Applied Core 0.0.20 map loading/minimap recovery fix.')
