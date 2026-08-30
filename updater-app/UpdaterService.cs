using System.Diagnostics;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace BigWalkHideSeek.Updater;

internal sealed class UpdaterService
{
    public const string UpdaterManifestUrl =
        "https://raw.githubusercontent.com/MisterWolf03/big-walk-hide-seek/bw-hs-feed-7c41e9/feed/9f6d2a/updater.json";

    public const string CoreManifestUrl =
        "https://raw.githubusercontent.com/MisterWolf03/big-walk-hide-seek/bw-hs-feed-7c41e9/feed/9f6d2a/latest.json";

    private readonly HttpClient _http;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true
    };

    public UpdaterService()
    {
        _http = new HttpClient
        {
            Timeout = TimeSpan.FromSeconds(90)
        };
        _http.DefaultRequestHeaders.UserAgent.ParseAdd("BigWalkHideSeek-Updater/0.1.0");
    }

    public string NormalizeProfilePath(string selectedPath)
    {
        string path = Path.GetFullPath(selectedPath.Trim().Trim('"'))
            .TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);

        if (string.Equals(Path.GetFileName(path), "BepInEx", StringComparison.OrdinalIgnoreCase))
        {
            DirectoryInfo? parent = Directory.GetParent(path);
            if (parent is not null)
                path = parent.FullName;
        }

        return path;
    }

    public bool ValidateProfile(string profilePath, out string reason)
    {
        reason = string.Empty;

        if (string.IsNullOrWhiteSpace(profilePath) || !Directory.Exists(profilePath))
        {
            reason = "Select a Thunderstore Big Walk profile folder.";
            return false;
        }

        string bepinex = Path.Combine(profilePath, "BepInEx");
        if (!Directory.Exists(bepinex))
        {
            reason = "That folder does not contain BepInEx. Select the Thunderstore profile root.";
            return false;
        }

        string il2cpp = Path.Combine(bepinex, "core", "BepInEx.Unity.IL2CPP.dll");
        if (!File.Exists(il2cpp))
        {
            reason = "BepInEx 6 IL2CPP was not found in this profile. Make sure this is a Big Walk Thunderstore profile.";
            return false;
        }

        return true;
    }

    public InstalledState GetInstalledState(string profilePath)
    {
        string loaderPath = GetLoaderPath(profilePath);
        string corePath = GetCorePath(profilePath);

        bool loaderExists = File.Exists(loaderPath);
        bool coreExists = File.Exists(corePath);

        return new InstalledState(
            loaderExists,
            GetAssemblyVersion(loaderPath),
            coreExists,
            GetAssemblyVersion(corePath));
    }

    public async Task<UpdaterManifest> FetchManifestAsync(CancellationToken cancellationToken = default)
    {
        string url = $"{UpdaterManifestUrl}?t={DateTimeOffset.UtcNow.ToUnixTimeSeconds()}";
        using HttpResponseMessage response = await _http.GetAsync(url, cancellationToken);
        response.EnsureSuccessStatusCode();

        string json = await response.Content.ReadAsStringAsync(cancellationToken);
        UpdaterManifest? manifest = JsonSerializer.Deserialize<UpdaterManifest>(json, JsonOptions);

        ValidateManifest(manifest);
        return manifest!;
    }

    public bool HasUpdates(InstalledState installed, UpdaterManifest manifest)
    {
        Version loaderLatest = VersionTools.Parse(manifest.Loader.Version);
        Version coreLatest = VersionTools.Parse(manifest.Core.Version);

        return !installed.LoaderExists
               || !installed.CoreExists
               || loaderLatest > installed.LoaderVersion
               || coreLatest > installed.CoreVersion;
    }

    public async Task InstallOrUpdateAsync(
        string profilePath,
        UpdaterManifest manifest,
        bool forceRepair,
        IProgress<UpdateProgress>? progress = null,
        CancellationToken cancellationToken = default)
    {
        if (!ValidateProfile(profilePath, out string reason))
            throw new InvalidOperationException(reason);

        if (IsBigWalkRunning())
            throw new InvalidOperationException("Big Walk appears to be running. Close the game before installing or updating the mod.");

        InstalledState installed = GetInstalledState(profilePath);

        bool updateLoader = forceRepair
                            || !installed.LoaderExists
                            || VersionTools.Parse(manifest.Loader.Version) > installed.LoaderVersion;

        bool updateCore = forceRepair
                          || !installed.CoreExists
                          || VersionTools.Parse(manifest.Core.Version) > installed.CoreVersion;

        int total = (updateLoader ? 1 : 0) + (updateCore ? 1 : 0);
        int completed = 0;

        if (total == 0)
        {
            progress?.Report(new UpdateProgress(100, "Already up to date."));
            EnsureLoaderConfig(profilePath);
            return;
        }

        if (updateLoader)
        {
            progress?.Report(new UpdateProgress(5, $"Downloading Loader {manifest.Loader.Version}..."));
            byte[] loaderBytes = await DownloadAndVerifyAsync(manifest.Loader, cancellationToken);
            InstallComponent(profilePath, "Loader", loaderBytes);
            completed++;
            progress?.Report(new UpdateProgress(
                Math.Min(90, completed * 90 / total),
                $"Loader {manifest.Loader.Version} installed."));
        }

        if (updateCore)
        {
            progress?.Report(new UpdateProgress(
                Math.Max(10, completed * 90 / total),
                $"Downloading Core {manifest.Core.Version}..."));
            byte[] coreBytes = await DownloadAndVerifyAsync(manifest.Core, cancellationToken);
            InstallComponent(profilePath, "Core", coreBytes);
            completed++;
            progress?.Report(new UpdateProgress(
                Math.Min(95, completed * 90 / total),
                $"Core {manifest.Core.Version} installed."));
        }

        RemoveLegacyPrototype(profilePath);
        EnsureLoaderConfig(profilePath);

        progress?.Report(new UpdateProgress(100, "Installation complete. Launch Big Walk modded through Thunderstore."));
    }

    public string GetModFolder(string profilePath) =>
        Path.Combine(profilePath, "BepInEx", "BigWalkHideSeek");

    private async Task<byte[]> DownloadAndVerifyAsync(ComponentRelease release, CancellationToken cancellationToken)
    {
        ValidateRelease(release);

        string encoding = (release.Encoding ?? "raw").Trim().ToLowerInvariant();
        byte[] bytes;

        if (encoding == "raw")
        {
            bytes = await _http.GetByteArrayAsync(release.Url.Trim(), cancellationToken);
        }
        else
        {
            string payload = await _http.GetStringAsync(release.Url.Trim(), cancellationToken);
            byte[] encoded = Convert.FromBase64String(payload);

            if (encoding == "base64")
            {
                bytes = encoded;
            }
            else if (encoding == "gzip-base64")
            {
                using var compressed = new MemoryStream(encoded, writable: false);
                using var gzip = new GZipStream(compressed, CompressionMode.Decompress);
                using var output = new MemoryStream();
                await gzip.CopyToAsync(output, cancellationToken);
                bytes = output.ToArray();
            }
            else
            {
                throw new InvalidDataException($"Unsupported package encoding: {release.Encoding}");
            }
        }

        if (bytes.Length == 0 || bytes.Length > 128 * 1024 * 1024)
            throw new InvalidDataException("Downloaded package size is invalid.");

        string actualHash = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
        string expectedHash = NormalizeHash(release.Sha256);

        if (!string.Equals(actualHash, expectedHash, StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidDataException(
                $"Downloaded package failed SHA-256 verification. Expected {expectedHash}, got {actualHash}.");
        }

        return bytes;
    }

    private static void InstallComponent(string profilePath, string component, byte[] bytes)
    {
        string destination = component switch
        {
            "Loader" => GetLoaderPath(profilePath),
            "Core" => GetCorePath(profilePath),
            _ => throw new ArgumentOutOfRangeException(nameof(component))
        };

        string directory = Path.GetDirectoryName(destination)!;
        Directory.CreateDirectory(directory);

        string tempPath = destination + ".download";
        string backupPath = destination.Replace(".dll", ".backup.dll", StringComparison.OrdinalIgnoreCase);

        try
        {
            File.WriteAllBytes(tempPath, bytes);

            if (File.Exists(destination))
                File.Copy(destination, backupPath, true);

            File.Move(tempPath, destination, true);
        }
        catch (IOException ex)
        {
            TryDelete(tempPath);
            throw new IOException(
                $"Could not replace {component}. Big Walk may still be running or the file may be locked.", ex);
        }
        catch
        {
            TryDelete(tempPath);
            throw;
        }
    }

    private static void EnsureLoaderConfig(string profilePath)
    {
        string runtimeDir = Path.Combine(profilePath, "BepInEx", "BigWalkHideSeek");
        Directory.CreateDirectory(runtimeDir);

        string configPath = Path.Combine(runtimeDir, "updater-config.json");
        if (File.Exists(configPath))
            return;

        string json = $$"""
        {
          "enabled": true,
          "manifestUrl": "{{CoreManifestUrl}}",
          "bearerToken": "",
          "timeoutSeconds": 8
        }
        """;

        File.WriteAllText(configPath, json + Environment.NewLine, Encoding.UTF8);
    }

    private static void RemoveLegacyPrototype(string profilePath)
    {
        string oldPath = Path.Combine(profilePath, "BepInEx", "plugins", "BigWalkHideSeek", "BigWalkHideSeek.dll");
        TryDelete(oldPath);
    }

    private static string GetLoaderPath(string profilePath) =>
        Path.Combine(profilePath, "BepInEx", "plugins", "BigWalkHideSeek", "BigWalkHideSeek.Loader.dll");

    private static string GetCorePath(string profilePath) =>
        Path.Combine(profilePath, "BepInEx", "BigWalkHideSeek", "BigWalkHideSeek.Core.dll");

    private static Version GetAssemblyVersion(string path)
    {
        if (!File.Exists(path))
            return new Version(0, 0, 0, 0);

        try
        {
            return VersionTools.Normalize(
                AssemblyName.GetAssemblyName(path).Version ?? new Version(0, 0, 0, 0));
        }
        catch
        {
            try
            {
                string? fileVersion = FileVersionInfo.GetVersionInfo(path).FileVersion;
                return VersionTools.Parse(fileVersion ?? "0.0.0");
            }
            catch
            {
                return new Version(0, 0, 0, 0);
            }
        }
    }

    private static bool IsBigWalkRunning()
    {
        foreach (Process process in Process.GetProcesses())
        {
            try
            {
                string normalized = process.ProcessName
                    .Replace(" ", string.Empty)
                    .Replace("_", string.Empty)
                    .Replace("-", string.Empty);

                if (string.Equals(normalized, "BIGWALK", StringComparison.OrdinalIgnoreCase))
                    return true;
            }
            catch
            {
                // Ignore processes we cannot inspect.
            }
            finally
            {
                process.Dispose();
            }
        }

        return false;
    }

    private static void ValidateManifest(UpdaterManifest? manifest)
    {
        if (manifest is null)
            throw new InvalidDataException("Updater manifest was empty.");

        if (manifest.SchemaVersion != 1)
            throw new InvalidDataException($"Unsupported updater manifest schema: {manifest.SchemaVersion}");

        ValidateRelease(manifest.Loader);
        ValidateRelease(manifest.Core);
    }

    private static void ValidateRelease(ComponentRelease release)
    {
        _ = VersionTools.Parse(release.Version);

        if (!Uri.TryCreate(release.Url, UriKind.Absolute, out Uri? uri) || uri.Scheme != Uri.UriSchemeHttps)
            throw new InvalidDataException("Package URL must be HTTPS.");

        string hash = NormalizeHash(release.Sha256);
        if (hash.Length != 64 || hash.Any(c => !Uri.IsHexDigit(c)))
            throw new InvalidDataException("Package SHA-256 is invalid.");
    }

    private static string NormalizeHash(string hash) =>
        (hash ?? string.Empty).Trim().Replace("-", string.Empty).ToLowerInvariant();

    private static void TryDelete(string path)
    {
        try
        {
            if (File.Exists(path))
                File.Delete(path);
        }
        catch
        {
            // Best effort cleanup only.
        }
    }
}
