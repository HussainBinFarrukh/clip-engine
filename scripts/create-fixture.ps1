param(
    [string]$Output = "tests\fixtures\speech_45s.mp4"
)

$ErrorActionPreference = "Stop"

$ffmpegCandidates = @(@(
    (Get-Command ffmpeg -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    "$env:LOCALAPPDATA\Programs\Stremio\ffmpeg.exe"
) | Where-Object { $_ -and (Test-Path $_) })

if (-not $ffmpegCandidates) {
    throw "ffmpeg.exe was not found. Install ffmpeg or update this script with its path."
}

$ffmpeg = $ffmpegCandidates[0]
$outputPath = Join-Path (Get-Location) $Output
$outputDir = Split-Path -Parent $outputPath
$wavPath = [System.IO.Path]::ChangeExtension($outputPath, ".wav")

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = -1
$synth.SetOutputToWaveFile($wavPath)
$text = "Clip Engine test fixture. This authorized sample video contains spoken words for pipeline smoke tests. "
$synth.Speak(($text * 8))
$synth.Dispose()

& $ffmpeg -hide_banner -loglevel error -y `
    -f lavfi -i "color=c=#1a1f1c:s=1280x720:r=30" `
    -i $wavPath `
    -t 45 `
    -c:v libx264 `
    -pix_fmt yuv420p `
    -c:a aac `
    -movflags +faststart `
    $outputPath

Remove-Item -LiteralPath $wavPath -Force
Write-Host "Created fixture: $outputPath"
