param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"

$inputFull = [System.IO.Path]::GetFullPath($InputPath)
$outputFull = [System.IO.Path]::GetFullPath($OutputPath)
$outputDir = [System.IO.Path]::GetDirectoryName($outputFull)

if (-not (Test-Path -LiteralPath $inputFull)) {
    throw "Map image was not found: $inputFull"
}

if (-not (Test-Path -LiteralPath $outputDir)) {
    [System.IO.Directory]::CreateDirectory($outputDir) | Out-Null
}

Add-Type -AssemblyName System.Drawing

$source = $null
$bitmap = $null
$graphics = $null
$locked = $null

try {
    $source = [System.Drawing.Image]::FromFile($inputFull)
    $width = $source.Width
    $height = $source.Height

    if ($width -le 0 -or $height -le 0) {
        throw "Map image has invalid dimensions: ${width}x${height}"
    }

    $bitmap = New-Object System.Drawing.Bitmap $width, $height, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.DrawImage($source, 0, 0, $width, $height)
    $graphics.Dispose()
    $graphics = $null

    $rect = New-Object System.Drawing.Rectangle 0, 0, $width, $height
    $locked = $bitmap.LockBits(
        $rect,
        [System.Drawing.Imaging.ImageLockMode]::ReadOnly,
        [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
    )

    $rowBytes = $width * 4
    $pixelBytes = New-Object byte[] ($rowBytes * $height)
    $rowBuffer = New-Object byte[] $rowBytes

    # System.Drawing exposes the image top-to-bottom. Unity raw Texture2D data
    # starts at the bottom row, so write rows in reverse order. Format32bppArgb
    # is stored in memory as BGRA, matching Unity TextureFormat.BGRA32.
    for ($sourceY = 0; $sourceY -lt $height; $sourceY++) {
        if ($locked.Stride -ge 0) {
            $sourceRow = [System.IntPtr]::Add($locked.Scan0, $sourceY * $locked.Stride)
        }
        else {
            $sourceRow = [System.IntPtr]::Add($locked.Scan0, ($height - 1 - $sourceY) * (-$locked.Stride))
        }

        [System.Runtime.InteropServices.Marshal]::Copy($sourceRow, $rowBuffer, 0, $rowBytes)
        $destinationY = $height - 1 - $sourceY
        [System.Buffer]::BlockCopy($rowBuffer, 0, $pixelBytes, $destinationY * $rowBytes, $rowBytes)
    }

    $bitmap.UnlockBits($locked)
    $locked = $null

    $stream = [System.IO.File]::Open($outputFull, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    try {
        $writer = New-Object System.IO.BinaryWriter $stream
        try {
            # Tiny custom header: little-endian width + height, then BGRA32 pixels.
            $writer.Write([int]$width)
            $writer.Write([int]$height)
            $writer.Write($pixelBytes)
            $writer.Flush()
        }
        finally {
            $writer.Dispose()
        }
    }
    finally {
        if ($stream) { $stream.Dispose() }
    }

    Write-Host "Prepared raw map asset: ${width}x${height}, $($pixelBytes.Length) pixel bytes"
    Write-Host "  $outputFull"
}
finally {
    if ($locked -and $bitmap) {
        try { $bitmap.UnlockBits($locked) } catch { }
    }
    if ($graphics) { $graphics.Dispose() }
    if ($bitmap) { $bitmap.Dispose() }
    if ($source) { $source.Dispose() }
}
