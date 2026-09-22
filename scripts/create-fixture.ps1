param(
    [string]$Output = "tests\fixtures\speech_45s.mp4",
    [int]$DurationSeconds = 45
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
$ffprobe = Join-Path (Split-Path -Parent $ffmpeg) "ffprobe.exe"
if (-not (Test-Path $ffprobe)) {
    throw "ffprobe.exe was not found next to ffmpeg.exe ($ffmpeg)."
}
$outputPath = Join-Path (Get-Location) $Output
$outputDir = Split-Path -Parent $outputPath
$wavPath = [System.IO.Path]::ChangeExtension($outputPath, ".wav")
$wordsPath = [System.IO.Path]::ChangeExtension($outputPath, ".words.json")

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

Add-Type -AssemblyName System.Speech

Add-Type -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Speech.Synthesis;

public class WordTiming
{
    public string Word;
    public int StartMs;
}

public class FixtureRecorder
{
    public List<WordTiming> Words = new List<WordTiming>();

    public void Attach(SpeechSynthesizer synth)
    {
        synth.SpeakProgress += OnSpeakProgress;
    }

    private void OnSpeakProgress(object sender, SpeakProgressEventArgs e)
    {
        var w = e.Text.Trim();
        if (w.Length > 0)
        {
            Words.Add(new WordTiming { Word = w, StartMs = (int)e.AudioPosition.TotalMilliseconds });
        }
    }
}
"@ -ReferencedAssemblies System.Speech

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SetOutputToWaveFile($wavPath)

$recorder = New-Object FixtureRecorder
$recorder.Attach($synth)

# Distinct sentences, not a repeated phrase: word-for-word repetition is a
# known failure mode for Whisper's timestamp alignment (it can lose track of
# which repetition it's in and drift), which would make this fixture
# adversarial rather than representative for the T05 accuracy check.
$sentences = @(
    "Clip Engine turns long recordings into short clips.",
    "This authorized sample video contains spoken words for pipeline testing.",
    "Each sentence here is different from the last one.",
    "The transcriber should find word boundaries and timestamps accurately.",
    "Pipeline smoke tests rely on this fixture running end to end.",
    "Audio extraction converts the original track to sixteen kilohertz mono.",
    "Word level timestamps let the transcript panel seek the video player.",
    "This is the final sentence in the fixture recording."
)
$synth.Speak(($sentences -join " "))
$synth.Dispose()

# SAPI's SpeakProgress.AudioPosition events can run ahead of the WAV file
# actually written to disk (observed: events reporting word positions past
# 40s for a WAV that measures ~37s once saved) — a synthesis-engine quirk,
# not a rounding error. Trust the real, measured file duration instead of
# the event timestamps or the requested video length.
$wavDurationOutput = & $ffprobe -v error -show_entries format=duration -of csv=p=0 $wavPath
$wavDurationMs = [int]([double]$wavDurationOutput * 1000)
Write-Host "Measured synthesized WAV duration: ${wavDurationMs}ms"

# Keep a safety margin below the real audio duration so no word is cut off
# mid-utterance by trailing silence/encoder rounding.
$safeCutoffMs = [Math]::Min($wavDurationMs - 300, ($DurationSeconds * 1000) - 2000)
$allWords = $recorder.Words | ForEach-Object {
    [pscustomobject]@{ word = $_.Word; start_ms = $_.StartMs }
}
$script:words = $allWords | Where-Object { $_.start_ms -lt $safeCutoffMs }
$droppedCount = $allWords.Count - $words.Count
if ($droppedCount -gt 0) {
    Write-Warning "Dropped $droppedCount word(s) spoken past the ${safeCutoffMs}ms safe cutoff."
}

$json = $words | ConvertTo-Json -Depth 3
[System.IO.File]::WriteAllText($wordsPath, $json, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Wrote ground-truth word timestamps: $wordsPath ($($words.Count) words)"

& $ffmpeg -hide_banner -loglevel error -y `
    -f lavfi -i "color=c=#1a1f1c:s=1280x720:r=30" `
    -i $wavPath `
    -t $DurationSeconds `
    -c:v libx264 `
    -pix_fmt yuv420p `
    -c:a aac `
    -movflags +faststart `
    $outputPath

Remove-Item -LiteralPath $wavPath -Force
Write-Host "Created fixture: $outputPath"
