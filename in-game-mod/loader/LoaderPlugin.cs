using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Net.Http;
using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json;
using BepInEx;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;

namespace BigWalkHideSeek.Loader;

[BepInPlugin("com.bigwalkhideseek.loader", "Big Walk Hide + Seek Loader", "0.1.1")]
public sealed class LoaderPlugin : BasePlugin
{
    internal static ManualLogSource Logger;

    public override void Load()
    {
        Logger = Log;
        Logger.LogInfo("Big Walk Hide + Seek Loader 0.1.1 starting.");

        try
        {
            string runtimeDir = GetRuntimeDirectory();
            Directory.CreateDirectory(runtimeDir);

            string corePath = Path.Combine(runtimeDir, "BigWalkHideSeek.Core.dll");
            string backupPath = Path.Combine(runtimeDir, "BigWalkHideSeek.Core.backup.dll");
            string configPath = Path.Combine(runtimeDir, "updater-config.json");

            EnsureDefaultConfig(configPath);
            TryUpdateCore(corePath, backupPath, configPath);
            LoadCore(corePath, backupPath);
        }
        catch (Exception ex)
        {
            Logger.LogError($"Loader failed: {ex}");
        }
    }

    private static string GetRuntimeDirectory()
    {
        string pluginDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location)!;
        DirectoryInfo pluginsDir = Directory.GetParent(pluginDir)!;
        DirectoryInfo bepinexDir = pluginsDir.Parent!;
        return Path.Combine(bepinexDir.FullName, "BigWalkHideSeek");
    }

    private static void EnsureDefaultConfig(string configPath)
    {
        if (File.Exists(configPath))
            return;

        var config = new UpdaterConfig();
        string json = JsonSerializer.Serialize(config, JsonOptionsIndented);
        File.WriteAllText(configPath, json);
        Logger.LogInfo($"Created updater config at {configPath}");
    }

    private static void TryUpdateCore(string corePath, string backupPath, string configPath)
    {
        UpdaterConfig? config;
        try
        {
            config = JsonSerializer.Deserialize<UpdaterConfig>(File.ReadAllText(configPath), JsonOptions);
        }
        catch (Exception ex)
        {
            Logger.LogWarning($"Could not read updater config; using installed Core. {ex.Message}");
            return;
        }

        if (config == null || !config.Enabled || string.IsNullOrWhiteSpace(config.ManifestUrl))
        {
            Logger.LogInfo("Automatic Core update check skipped: no manifest URL configured.");
            return;
        }

        try
        {
            using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(Math.Clamp(config.TimeoutSeconds, 1, 15)) };
            if (!string.IsNullOrWhiteSpace(config.BearerToken))
                client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", config.BearerToken.Trim());

            Logger.LogInfo("Checking for Hide + Seek Core updates...");
            string manifestJson = client.GetStringAsync(config.ManifestUrl.Trim()).GetAwaiter().GetResult();
            UpdateManifest? manifest = JsonSerializer.Deserialize<UpdateManifest>(manifestJson, JsonOptions);

            if (manifest == null || string.IsNullOrWhiteSpace(manifest.Version) || string.IsNullOrWhiteSpace(manifest.Url) || string.IsNullOrWhiteSpace(manifest.Sha256))
                throw new InvalidDataException("Update manifest is missing version, url, or sha256.");

            Version remoteVersion = ParseVersion(manifest.Version);
            Version installedVersion = GetInstalledCoreVersion(corePath);

            if (remoteVersion <= installedVersion)
            {
                Logger.LogInfo($"Core {installedVersion} is up to date.");
                return;
            }

            Logger.LogInfo($"Updating Core {installedVersion} -> {remoteVersion}...");
            byte[] bytes = DownloadCoreBytes(client, manifest);
            string actualHash = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
            string expectedHash = manifest.Sha256.Trim().Replace("-", string.Empty).ToLowerInvariant();

            if (!string.Equals(actualHash, expectedHash, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException($"Downloaded Core hash mismatch. Expected {expectedHash}, got {actualHash}.");

            string tempPath = corePath + ".download";
            File.WriteAllBytes(tempPath, bytes);

            if (File.Exists(corePath))
                File.Copy(corePath, backupPath, true);

            File.Copy(tempPath, corePath, true);
            File.Delete(tempPath);

            Logger.LogInfo($"Core updated successfully to {remoteVersion}.");
        }
        catch (Exception ex)
        {
            Logger.LogWarning($"Update check failed; continuing with installed Core. {ex.Message}");
        }
    }

    private static byte[] DownloadCoreBytes(HttpClient client, UpdateManifest manifest)
    {
        string encoding = (manifest.Encoding ?? string.Empty).Trim().ToLowerInvariant();

        if (string.IsNullOrEmpty(encoding) || encoding == "raw")
            return client.GetByteArrayAsync(manifest.Url.Trim()).GetAwaiter().GetResult();

        string payload = client.GetStringAsync(manifest.Url.Trim()).GetAwaiter().GetResult();
        byte[] encodedBytes = Convert.FromBase64String(payload);

        if (encoding == "base64")
            return encodedBytes;

        if (encoding == "gzip-base64")
        {
            using var compressed = new MemoryStream(encodedBytes, writable: false);
            using var gzip = new GZipStream(compressed, CompressionMode.Decompress);
            using var output = new MemoryStream();
            gzip.CopyTo(output);
            return output.ToArray();
        }

        throw new InvalidDataException($"Unsupported Core encoding: {manifest.Encoding}");
    }

    private void LoadCore(string corePath, string backupPath)
    {
        if (!File.Exists(corePath))
        {
            Logger.LogError($"Core DLL not found: {corePath}");
            return;
        }

        try
        {
            LoadCoreAssembly(corePath);
        }
        catch (Exception ex)
        {
            Logger.LogError($"Core failed to load: {ex}");

            if (!File.Exists(backupPath))
                return;

            try
            {
                Logger.LogWarning("Restoring previous Core backup for the next launch.");
                File.Copy(backupPath, corePath, true);
            }
            catch (Exception restoreEx)
            {
                Logger.LogError($"Could not restore Core backup: {restoreEx}");
            }
        }
    }

    private void LoadCoreAssembly(string corePath)
    {
        Assembly coreAssembly = Assembly.LoadFrom(corePath);
        Type? entryType = coreAssembly.GetType("BigWalkHideSeek.Core.CoreEntry", throwOnError: false);
        Type? overlayType = coreAssembly.GetType("BigWalkHideSeek.Core.HideSeekOverlay", throwOnError: false);

        if (entryType == null || overlayType == null)
            throw new TypeLoadException("CoreEntry or HideSeekOverlay was not found in Core DLL.");

        MethodInfo? configure = entryType.GetMethod("Configure", BindingFlags.Public | BindingFlags.Static);
        configure?.Invoke(null, new object[] { Logger });

        MethodInfo? addComponent = null;
        foreach (MethodInfo method in typeof(BasePlugin).GetMethods(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
        {
            if (method.Name == "AddComponent" && method.IsGenericMethodDefinition && method.GetParameters().Length == 0)
            {
                addComponent = method;
                break;
            }
        }

        if (addComponent == null)
            throw new MissingMethodException("BepInEx BasePlugin.AddComponent<T>() was not found.");

        addComponent.MakeGenericMethod(overlayType).Invoke(this, null);
        Logger.LogInfo($"Hide + Seek Core {GetInstalledCoreVersion(corePath)} loaded.");
    }

    private static Version GetInstalledCoreVersion(string corePath)
    {
        if (!File.Exists(corePath))
            return new Version(0, 0, 0, 0);

        try
        {
            return NormalizeVersion(AssemblyName.GetAssemblyName(corePath).Version ?? new Version(0, 0, 0, 0));
        }
        catch
        {
            try
            {
                string? fileVersion = FileVersionInfo.GetVersionInfo(corePath).FileVersion;
                return ParseVersion(fileVersion ?? "0.0.0");
            }
            catch
            {
                return new Version(0, 0, 0, 0);
            }
        }
    }

    private static Version ParseVersion(string value)
    {
        if (!Version.TryParse(value.Trim(), out Version? parsed) || parsed == null)
            throw new FormatException($"Invalid version: {value}");
        return NormalizeVersion(parsed);
    }

    private static Version NormalizeVersion(Version v) =>
        new(v.Major, v.Minor, Math.Max(v.Build, 0), Math.Max(v.Revision, 0));

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true
    };

    private static readonly JsonSerializerOptions JsonOptionsIndented = new()
    {
        WriteIndented = true
    };

    private sealed class UpdaterConfig
    {
        public bool Enabled { get; set; } = true;
        public string ManifestUrl { get; set; } = string.Empty;
        public string BearerToken { get; set; } = string.Empty;
        public int TimeoutSeconds { get; set; } = 4;
    }

    private sealed class UpdateManifest
    {
        public string Version { get; set; } = string.Empty;
        public string Url { get; set; } = string.Empty;
        public string Sha256 { get; set; } = string.Empty;
        public string Encoding { get; set; } = "raw";
    }
}
