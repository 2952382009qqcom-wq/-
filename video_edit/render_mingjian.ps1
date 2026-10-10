$ErrorActionPreference = 'Stop'

$ffmpeg = 'C:\Users\hh\AppData\Local\Temp\codex-mingjian-video-tools\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe'
$source = 'C:\Users\hh\Documents\Tencent Files\2952382009\nt_qq\nt_data\Video\2026-09\Ori\40a2cd7f99937606073bd76b610d8bfc.mp4'
$filter = 'C:\Users\hh\Desktop\ChatLaw-main\video_edit\mingjian_filter.txt'
$output = 'C:\Users\hh\Desktop\ChatLaw-main\outputs\明鉴_产品演示_30秒.mp4'

& $ffmpeg -y -hide_banner `
    -i $source `
    -filter_complex_script $filter `
    -map '[vout]' -map '[aout]' `
    -c:v libx264 -preset fast -crf 19 -profile:v high -level 4.1 `
    -c:a aac -b:a 160k -ar 48000 `
    -movflags +faststart `
    $output

if ($LASTEXITCODE -ne 0) {
    throw "FFmpeg rendering failed with exit code $LASTEXITCODE"
}

Get-Item -LiteralPath $output | Select-Object FullName, Length, LastWriteTime
