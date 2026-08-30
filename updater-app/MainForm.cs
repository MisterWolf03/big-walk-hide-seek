using System.Diagnostics;
using System.Drawing;

namespace BigWalkHideSeek.Updater;

internal sealed class MainForm : Form
{
    private readonly UpdaterService _updater = new();
    private readonly AppSettings _settings = SettingsStore.Load();

    private readonly TextBox _profilePath = new();
    private readonly Button _changeProfile = new();

    private readonly Label _loaderVersion = new();
    private readonly Label _loaderLatest = new();
    private readonly Label _coreVersion = new();
    private readonly Label _coreLatest = new();

    private readonly Label _status = new();
    private readonly ProgressBar _progress = new();

    private readonly Button _primary = new();
    private readonly Button _repair = new();
    private readonly Button _openFolder = new();

    private bool _busy;

    private static readonly Color Background = Color.FromArgb(18, 22, 28);
    private static readonly Color PanelColor = Color.FromArgb(28, 34, 43);
    private static readonly Color CardColor = Color.FromArgb(35, 42, 52);
    private static readonly Color Accent = Color.FromArgb(240, 162, 31);
    private static readonly Color TextPrimary = Color.FromArgb(239, 243, 248);
    private static readonly Color TextSecondary = Color.FromArgb(158, 170, 185);
    private static readonly Color Success = Color.FromArgb(99, 205, 145);

    public MainForm()
    {
        Text = "Big Walk Hide + Seek Updater";
        ClientSize = new Size(760, 540);
        MinimumSize = MaximumSize = Size;
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Background;
        ForeColor = TextPrimary;
        Font = new Font("Segoe UI", 10F);
        FormBorderStyle = FormBorderStyle.FixedSingle;
        MaximizeBox = false;

        BuildUi();

        _profilePath.Text = _settings.ProfilePath;
        _changeProfile.Click += (_, _) => ChooseProfile();
        _primary.Click += async (_, _) => await PrimaryActionAsync();
        _repair.Click += async (_, _) => await RepairAsync();
        _openFolder.Click += (_, _) => OpenModFolder();

        Shown += (_, _) => RefreshInstalledState();
    }

    private void BuildUi()
    {
        Controls.Add(MakeLabel("BIG WALK HIDE + SEEK", 28, 22, 500, 34, 23F, FontStyle.Bold, Accent));
        Controls.Add(MakeLabel(
            "Install and update the mod here. Launch Big Walk modded through Thunderstore like normal.",
            30, 57, 690, 24, 9.5F, FontStyle.Regular, TextSecondary));

        Panel profilePanel = MakePanel(28, 94, 704, 100, PanelColor);
        profilePanel.Controls.Add(MakeLabel("THUNDERSTORE PROFILE", 18, 14, 250, 20, 9F, FontStyle.Bold, TextSecondary));

        _profilePath.SetBounds(18, 43, 550, 32);
        _profilePath.ReadOnly = true;
        _profilePath.BackColor = CardColor;
        _profilePath.ForeColor = TextPrimary;
        _profilePath.BorderStyle = BorderStyle.FixedSingle;
        profilePanel.Controls.Add(_profilePath);

        StyleSecondaryButton(_changeProfile, "CHANGE");
        _changeProfile.SetBounds(578, 41, 106, 36);
        profilePanel.Controls.Add(_changeProfile);
        Controls.Add(profilePanel);

        Panel versionsPanel = MakePanel(28, 210, 704, 150, PanelColor);
        versionsPanel.Controls.Add(MakeLabel("INSTALLED MOD", 18, 13, 250, 20, 9F, FontStyle.Bold, TextSecondary));

        Panel loaderCard = MakePanel(18, 42, 323, 91, CardColor);
        loaderCard.Controls.Add(MakeLabel("LOADER", 14, 10, 100, 20, 9F, FontStyle.Bold, TextSecondary));
        _loaderVersion.SetBounds(14, 33, 140, 28);
        _loaderVersion.Font = new Font("Segoe UI", 16F, FontStyle.Bold);
        _loaderVersion.ForeColor = TextPrimary;
        loaderCard.Controls.Add(_loaderVersion);
        _loaderLatest.SetBounds(14, 65, 290, 18);
        _loaderLatest.ForeColor = TextSecondary;
        _loaderLatest.Font = new Font("Segoe UI", 8.5F);
        loaderCard.Controls.Add(_loaderLatest);

        Panel coreCard = MakePanel(363, 42, 323, 91, CardColor);
        coreCard.Controls.Add(MakeLabel("CORE", 14, 10, 100, 20, 9F, FontStyle.Bold, TextSecondary));
        _coreVersion.SetBounds(14, 33, 140, 28);
        _coreVersion.Font = new Font("Segoe UI", 16F, FontStyle.Bold);
        _coreVersion.ForeColor = TextPrimary;
        coreCard.Controls.Add(_coreVersion);
        _coreLatest.SetBounds(14, 65, 290, 18);
        _coreLatest.ForeColor = TextSecondary;
        _coreLatest.Font = new Font("Segoe UI", 8.5F);
        coreCard.Controls.Add(_coreLatest);

        versionsPanel.Controls.Add(loaderCard);
        versionsPanel.Controls.Add(coreCard);
        Controls.Add(versionsPanel);

        _status.SetBounds(30, 377, 700, 23);
        _status.ForeColor = TextSecondary;
        Controls.Add(_status);

        _progress.SetBounds(30, 405, 700, 8);
        _progress.Minimum = 0;
        _progress.Maximum = 100;
        _progress.Style = ProgressBarStyle.Continuous;
        Controls.Add(_progress);

        StylePrimaryButton(_primary, "INSTALL MOD");
        _primary.SetBounds(30, 435, 390, 54);
        Controls.Add(_primary);

        StyleSecondaryButton(_repair, "REPAIR");
        _repair.SetBounds(432, 435, 140, 54);
        Controls.Add(_repair);

        StyleSecondaryButton(_openFolder, "OPEN FOLDER");
        _openFolder.SetBounds(584, 435, 146, 54);
        Controls.Add(_openFolder);

        Controls.Add(MakeLabel("UPDATER v0.1.0", 30, 505, 160, 18, 8F, FontStyle.Bold, TextSecondary));
    }

    private void ChooseProfile()
    {
        using var dialog = new FolderBrowserDialog
        {
            Description = "Select the Thunderstore Big Walk profile folder (the folder that contains BepInEx).",
            UseDescriptionForTitle = true,
            ShowNewFolderButton = false
        };

        if (!string.IsNullOrWhiteSpace(_settings.ProfilePath) && Directory.Exists(_settings.ProfilePath))
            dialog.SelectedPath = _settings.ProfilePath;

        if (dialog.ShowDialog(this) != DialogResult.OK)
            return;

        string selected = _updater.NormalizeProfilePath(dialog.SelectedPath);

        if (!_updater.ValidateProfile(selected, out string reason))
        {
            MessageBox.Show(this, reason, "Invalid Thunderstore profile", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        _settings.ProfilePath = selected;
        SettingsStore.Save(_settings);
        _profilePath.Text = selected;

        _loaderLatest.Text = "Latest: —";
        _coreLatest.Text = "Latest: —";
        _progress.Value = 0;
        RefreshInstalledState();
    }

    private void RefreshInstalledState()
    {
        if (!_updater.ValidateProfile(_settings.ProfilePath, out string reason))
        {
            _loaderVersion.Text = "—";
            _coreVersion.Text = "—";
            _loaderLatest.Text = "Latest: —";
            _coreLatest.Text = "Latest: —";
            _status.Text = reason;
            _primary.Text = "SELECT THUNDERSTORE PROFILE";
            _primary.Enabled = !_busy;
            _repair.Enabled = false;
            _openFolder.Enabled = false;
            return;
        }

        InstalledState installed = _updater.GetInstalledState(_settings.ProfilePath);

        _loaderVersion.Text = installed.LoaderExists ? VersionTools.Display(installed.LoaderVersion) : "Not installed";
        _coreVersion.Text = installed.CoreExists ? VersionTools.Display(installed.CoreVersion) : "Not installed";

        if (installed.FullyInstalled)
        {
            _status.Text = "Mod installed. Check GitHub for a newer release before launching.";
            _primary.Text = "CHECK FOR UPDATES";
        }
        else
        {
            _status.Text = "Mod is not fully installed in this profile.";
            _primary.Text = "INSTALL MOD";
        }

        _primary.Enabled = !_busy;
        _repair.Enabled = !_busy && installed.FullyInstalled;
        _openFolder.Enabled = !_busy;
    }

    private async Task PrimaryActionAsync()
    {
        if (_busy)
            return;

        if (!_updater.ValidateProfile(_settings.ProfilePath, out _))
        {
            ChooseProfile();
            return;
        }

        InstalledState installed = _updater.GetInstalledState(_settings.ProfilePath);

        if (installed.FullyInstalled)
            await CheckAndInstallUpdatesAsync();
        else
            await InstallFreshAsync();
    }

    private async Task InstallFreshAsync()
    {
        await RunOperationAsync(async progress =>
        {
            _status.Text = "Checking the current release...";
            UpdaterManifest manifest = await _updater.FetchManifestAsync();
            ShowLatest(manifest);

            await _updater.InstallOrUpdateAsync(_settings.ProfilePath, manifest, false, progress);
            RefreshInstalledState();
            _status.ForeColor = Success;
            _status.Text = "Installed successfully. Open Thunderstore and launch modded.";
        });
    }

    private async Task CheckAndInstallUpdatesAsync()
    {
        await RunOperationAsync(async progress =>
        {
            _status.Text = "Checking GitHub for updates...";
            progress.Report(new UpdateProgress(5, "Checking GitHub for updates..."));

            UpdaterManifest manifest = await _updater.FetchManifestAsync();
            ShowLatest(manifest);

            InstalledState installed = _updater.GetInstalledState(_settings.ProfilePath);
            if (!_updater.HasUpdates(installed, manifest))
            {
                _progress.Value = 100;
                _status.ForeColor = Success;
                _status.Text = "You're up to date. Launch modded through Thunderstore.";
                return;
            }

            await _updater.InstallOrUpdateAsync(_settings.ProfilePath, manifest, false, progress);
            RefreshInstalledState();
            _status.ForeColor = Success;
            _status.Text = "Update installed. Launch modded through Thunderstore.";
        });
    }

    private async Task RepairAsync()
    {
        if (_busy || !_updater.ValidateProfile(_settings.ProfilePath, out _))
            return;

        DialogResult choice = MessageBox.Show(
            this,
            "Repair will redownload and replace both Big Walk Hide + Seek components. Continue?",
            "Repair installation",
            MessageBoxButtons.YesNo,
            MessageBoxIcon.Question);

        if (choice != DialogResult.Yes)
            return;

        await RunOperationAsync(async progress =>
        {
            _status.Text = "Preparing repair...";
            UpdaterManifest manifest = await _updater.FetchManifestAsync();
            ShowLatest(manifest);

            await _updater.InstallOrUpdateAsync(_settings.ProfilePath, manifest, true, progress);
            RefreshInstalledState();
            _status.ForeColor = Success;
            _status.Text = "Repair complete. Launch modded through Thunderstore.";
        });
    }

    private async Task RunOperationAsync(Func<IProgress<UpdateProgress>, Task> operation)
    {
        SetBusy(true);
        _status.ForeColor = TextSecondary;
        _progress.Value = 0;

        var progress = new Progress<UpdateProgress>(value =>
        {
            _progress.Value = Math.Clamp(value.Percent, 0, 100);
            _status.Text = value.Message;
        });

        try
        {
            await operation(progress);
        }
        catch (HttpRequestException ex)
        {
            ShowFailure($"Could not reach the update feed.\n\n{ex.Message}");
        }
        catch (Exception ex)
        {
            ShowFailure(ex.Message);
        }
        finally
        {
            SetBusy(false);
            RefreshInstalledStateKeepingStatus();
        }
    }

    private void ShowLatest(UpdaterManifest manifest)
    {
        _loaderLatest.Text = $"Latest: {VersionTools.Display(VersionTools.Parse(manifest.Loader.Version))}";
        _coreLatest.Text = $"Latest: {VersionTools.Display(VersionTools.Parse(manifest.Core.Version))}";
    }

    private void ShowFailure(string message)
    {
        _status.ForeColor = Color.FromArgb(235, 108, 108);
        _status.Text = "Operation failed. See the message for details.";
        MessageBox.Show(this, message, "Big Walk Hide + Seek Updater", MessageBoxButtons.OK, MessageBoxIcon.Error);
    }

    private void SetBusy(bool busy)
    {
        _busy = busy;
        UseWaitCursor = busy;
        _changeProfile.Enabled = !busy;
        _primary.Enabled = !busy;
        _repair.Enabled = !busy;
        _openFolder.Enabled = !busy;
    }

    private void RefreshInstalledStateKeepingStatus()
    {
        string status = _status.Text;
        Color statusColor = _status.ForeColor;
        string loaderLatest = _loaderLatest.Text;
        string coreLatest = _coreLatest.Text;

        RefreshInstalledState();

        _status.Text = status;
        _status.ForeColor = statusColor;
        _loaderLatest.Text = loaderLatest;
        _coreLatest.Text = coreLatest;
    }

    private void OpenModFolder()
    {
        if (!_updater.ValidateProfile(_settings.ProfilePath, out _))
            return;

        string path = _updater.GetModFolder(_settings.ProfilePath);
        Directory.CreateDirectory(path);

        Process.Start(new ProcessStartInfo
        {
            FileName = "explorer.exe",
            Arguments = $"\"{path}\"",
            UseShellExecute = true
        });
    }

    private static Panel MakePanel(int x, int y, int width, int height, Color color) =>
        new()
        {
            Bounds = new Rectangle(x, y, width, height),
            BackColor = color
        };

    private static Label MakeLabel(
        string text,
        int x,
        int y,
        int width,
        int height,
        float fontSize,
        FontStyle style,
        Color color) =>
        new()
        {
            Text = text,
            Bounds = new Rectangle(x, y, width, height),
            Font = new Font("Segoe UI", fontSize, style),
            ForeColor = color,
            BackColor = Color.Transparent
        };

    private static void StylePrimaryButton(Button button, string text)
    {
        button.Text = text;
        button.FlatStyle = FlatStyle.Flat;
        button.FlatAppearance.BorderSize = 0;
        button.BackColor = Accent;
        button.ForeColor = Color.FromArgb(30, 30, 30);
        button.Font = new Font("Segoe UI", 10.5F, FontStyle.Bold);
        button.Cursor = Cursors.Hand;
    }

    private static void StyleSecondaryButton(Button button, string text)
    {
        button.Text = text;
        button.FlatStyle = FlatStyle.Flat;
        button.FlatAppearance.BorderColor = Color.FromArgb(69, 79, 92);
        button.FlatAppearance.BorderSize = 1;
        button.BackColor = CardColor;
        button.ForeColor = TextPrimary;
        button.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
        button.Cursor = Cursors.Hand;
    }
}
