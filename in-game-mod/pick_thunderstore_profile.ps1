Add-Type -AssemblyName System.Windows.Forms

$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = "Choose your Thunderstore Big Walk PROFILE folder (the folder that contains BepInEx)"
$dialog.ShowNewFolderButton = $false

$result = $dialog.ShowDialog()
if ($result -ne [System.Windows.Forms.DialogResult]::OK) {
    exit 1
}

$profile = $dialog.SelectedPath
$bep = Join-Path $profile "BepInEx"
$core = Join-Path $bep "core"
$interop = Join-Path $bep "interop"

if (-not (Test-Path (Join-Path $core "BepInEx.Unity.IL2CPP.dll"))) {
    [System.Windows.Forms.MessageBox]::Show(
        "That folder does not look like the active Thunderstore profile.`n`nChoose the PROFILE folder that directly contains the BepInEx folder.",
        "Big Walk Hide + Seek",
        "OK",
        "Error"
    ) | Out-Null
    exit 2
}

if (-not (Test-Path $interop)) {
    [System.Windows.Forms.MessageBox]::Show(
        "BepInEx was found, but BepInEx\interop is missing.`n`nLaunch Big Walk once with this Thunderstore profile so BepInEx can generate its interop files, then try again.",
        "Big Walk Hide + Seek",
        "OK",
        "Warning"
    ) | Out-Null
    exit 3
}

Write-Output $profile
