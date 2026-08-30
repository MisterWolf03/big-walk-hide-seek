namespace BigWalkHideSeek.Updater;

internal sealed class AppSettings
{
    public string ProfilePath { get; set; } = string.Empty;
}

internal sealed class UpdaterManifest
{
    public int SchemaVersion { get; set; } = 1;
    public ComponentRelease Loader { get; set; } = new();
    public ComponentRelease Core { get; set; } = new();
    public string ReleaseNotes { get; set; } = string.Empty;
}

internal sealed class ComponentRelease
{
    public string Version { get; set; } = string.Empty;
    public string Url { get; set; } = string.Empty;
    public string Sha256 { get; set; } = string.Empty;
    public string Encoding { get; set; } = "raw";
}

internal sealed record InstalledState(
    bool LoaderExists,
    Version LoaderVersion,
    bool CoreExists,
    Version CoreVersion)
{
    public bool FullyInstalled => LoaderExists && CoreExists;
}

internal sealed record UpdateProgress(int Percent, string Message);

internal static class VersionTools
{
    public static Version Parse(string value)
    {
        if (!Version.TryParse(value.Trim(), out Version? parsed) || parsed is null)
            throw new FormatException($"Invalid version: {value}");

        return Normalize(parsed);
    }

    public static Version Normalize(Version version) =>
        new(version.Major, version.Minor, Math.Max(version.Build, 0), Math.Max(version.Revision, 0));

    public static string Display(Version version)
    {
        Version normalized = Normalize(version);
        return normalized.Revision == 0
            ? $"{normalized.Major}.{normalized.Minor}.{normalized.Build}"
            : normalized.ToString();
    }
}
