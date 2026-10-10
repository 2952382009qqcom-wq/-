param(
    [string]$Source = 'C:\Users\hh\Documents\Tencent Files\2952382009\nt_qq\nt_data\Video\2026-09\Ori\40a2cd7f99937606073bd76b610d8bfc.mp4',
    [string]$Output = 'C:\Users\hh\Desktop\ChatLaw-main\outputs\明鉴_产品演示_动效版_v2.mp4'
)

$ErrorActionPreference = 'Stop'

$ffmpeg = 'C:\Users\hh\AppData\Local\Temp\codex-mingjian-video-tools\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe'
$filter = Join-Path $PSScriptRoot 'mingjian_motion_filter.txt'
$audioDir = Join-Path $PSScriptRoot 'generated_audio'
$outputDir = Split-Path -Parent $Output

if (-not (Test-Path -LiteralPath $ffmpeg)) {
    throw "FFmpeg not found: $ffmpeg"
}
if (-not (Test-Path -LiteralPath $Source)) {
    throw "Source recording not found: $Source"
}

New-Item -ItemType Directory -Force -Path $audioDir, $outputDir | Out-Null

Add-Type -AssemblyName System.Speech

function New-Narration {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$Path
    )

    $speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
    try {
        $speaker.SelectVoice('Microsoft Huihui Desktop')
        $speaker.Rate = 1
        $speaker.Volume = 100
        $speaker.SetOutputToWaveFile($Path)
        $speaker.Speak($Text)
    }
    finally {
        $speaker.Dispose()
    }
}

$voice1 = Join-Path $audioDir 'voice_01.wav'
$voice2 = Join-Path $audioDir 'voice_02.wav'
$voice3 = Join-Path $audioDir 'voice_03.wav'
$voice4 = Join-Path $audioDir 'voice_04.wav'

New-Narration -Text '明鉴，面向真实法律场景的智能辅助平台。' -Path $voice1
New-Narration -Text '用自然语言描述问题，系统快速梳理争议焦点、法律依据与行动建议。' -Path $voice2
New-Narration -Text '从智能问答，到法律检索，再到文书和证据风险研判，复杂信息清晰呈现。' -Path $voice3
New-Narration -Text '让每一次判断更有依据。明鉴，以法为镜，明辨是非。' -Path $voice4

& $ffmpeg -y -hide_banner `
    -i $Source `
    -i $voice1 `
    -i $voice2 `
    -i $voice3 `
    -i $voice4 `
    -filter_complex_script $filter `
    -map '[vout]' -map '[aout]' `
    -c:v libx264 -preset medium -crf 18 -profile:v high -level 4.1 `
    -c:a aac -b:a 192k -ar 48000 `
    -movflags +faststart `
    $Output

if ($LASTEXITCODE -ne 0) {
    throw "FFmpeg rendering failed with exit code $LASTEXITCODE"
}

Get-Item -LiteralPath $Output | Select-Object FullName, Length, LastWriteTime
