$ErrorActionPreference = "Stop"

function RGB($hex) {
    $hex = $hex.TrimStart("#")
    $r = [Convert]::ToInt32($hex.Substring(0,2), 16)
    $g = [Convert]::ToInt32($hex.Substring(2,2), 16)
    $b = [Convert]::ToInt32($hex.Substring(4,2), 16)
    return $r + ($g * 256) + ($b * 65536)
}

function Add-Text($slide, [string]$text, [double]$x, [double]$y, [double]$w, [double]$h, [int]$size, [string]$color, [bool]$bold=$false, [int]$align=1) {
    $box = $slide.Shapes.AddTextbox(1, $x, $y, $w, $h)
    $box.TextFrame2.TextRange.Text = $text
    $box.TextFrame2.TextRange.Font.NameFarEast = "Microsoft YaHei"
    $box.TextFrame2.TextRange.Font.Name = "Microsoft YaHei"
    $box.TextFrame2.TextRange.Font.Size = $size
    $box.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = RGB $color
    if ($bold) { $box.TextFrame2.TextRange.Font.Bold = -1 }
    $box.TextFrame2.TextRange.ParagraphFormat.Alignment = $align
    $box.TextFrame2.MarginLeft = 0
    $box.TextFrame2.MarginRight = 0
    $box.TextFrame2.MarginTop = 0
    $box.TextFrame2.MarginBottom = 0
    return $box
}

function Add-Line($slide, [double]$x1, [double]$y1, [double]$x2, [double]$y2, [string]$color, [double]$width=1) {
    $ln = $slide.Shapes.AddLine($x1, $y1, $x2, $y2)
    $ln.Line.ForeColor.RGB = RGB $color
    $ln.Line.Weight = $width
    return $ln
}

function Add-Rect($slide, [double]$x, [double]$y, [double]$w, [double]$h, [string]$fill, [string]$line, [double]$alpha=0, [int]$type=1) {
    $sh = $slide.Shapes.AddShape($type, $x, $y, $w, $h)
    $sh.Fill.ForeColor.RGB = RGB $fill
    $sh.Fill.Transparency = $alpha
    $sh.Line.ForeColor.RGB = RGB $line
    $sh.Line.Weight = 1
    return $sh
}

function Add-Marker($slide, [double]$x, [double]$y, [string]$color, [string]$label) {
    $dot = $slide.Shapes.AddShape(9, $x-5, $y-5, 10, 10)
    $dot.Fill.ForeColor.RGB = RGB $color
    $dot.Line.ForeColor.RGB = RGB "07111F"
    $dot.Line.Weight = 1.4
    Add-Text $slide $label ($x-18) ($y-24) 36 10 6 $color $true 2 | Out-Null
}

$out = Join-Path (Resolve-Path ".").Path "明鉴_单页_发展规划_高级图表版.pptx"
$desktopOut = "C:\Users\hh\Desktop\明鉴_单页_发展规划_高级图表版.pptx"

$ppt = New-Object -ComObject PowerPoint.Application
$ppt.Visible = -1
$pres = $ppt.Presentations.Add()
$pres.PageSetup.SlideWidth = 960
$pres.PageSetup.SlideHeight = 540
$slide = $pres.Slides.Add(1, 12)

$bg = $slide.Background.Fill
$bg.ForeColor.RGB = RGB "07111F"
Add-Rect $slide 0 0 960 540 "07111F" "07111F" | Out-Null

for ($x=0; $x -le 960; $x += 60) { Add-Line $slide $x 0 $x 540 "0D253A" 0.5 | Out-Null }
for ($y=0; $y -le 540; $y += 60) { Add-Line $slide 0 $y 960 $y "0D253A" 0.5 | Out-Null }
Add-Line $slide 0 120 960 120 "12304A" 0.8 | Out-Null
Add-Line $slide 0 420 960 420 "12304A" 0.8 | Out-Null
Add-Line $slide 44 507 820 507 "2A4A68" 0.8 | Out-Null

Add-Rect $slide 44 39 8 8 "38D9F7" "38D9F7" | Out-Null
Add-Text $slide "PLAN" 62 36 45 10 7 "AABBD0" $true 1 | Out-Null
Add-Text $slide "发展规划以产品能力、试点规模与商业化验证三条曲线同步推进" 44 73 680 34 26 "F4F8FF" $true 1 | Out-Null
Add-Text $slide "05 发展规划" 745 57 170 34 28 "B8D8F8" $true 3 | Out-Null
$smallDot = $slide.Shapes.AddShape(9, 45, 112, 7, 7)
$smallDot.Fill.ForeColor.RGB = RGB "F4F8FF"
$smallDot.Line.ForeColor.RGB = RGB "F4F8FF"

$cx = 68; $cy = 150; $cw = 550; $ch = 245
Add-Line $slide $cx ($cy+$ch) ($cx+$cw) ($cy+$ch) "2A4A68" 1.1 | Out-Null
Add-Line $slide $cx $cy $cx ($cy+$ch) "2A4A68" 1.1 | Out-Null
for ($i=1; $i -le 4; $i++) { Add-Line $slide $cx ($cy+$ch-($ch*$i/5)) ($cx+$cw) ($cy+$ch-($ch*$i/5)) "12304A" 0.5 | Out-Null }

$phaseColors = @("20D1B5","38D9F7","E4BF57")
$phaseLabels = @("2026`n验证期","2027`n复制期","2028`n规模期")
for ($i=0; $i -lt 3; $i++) {
    $bx = $cx + 12 + $i*185
    Add-Rect $slide $bx ($cy+7) 150 ($ch-14) $phaseColors[$i] $phaseColors[$i] 0.88 | Out-Null
    $px = $cx + 75 + $i*200
    Add-Line $slide $px $cy $px ($cy+$ch) "2A4A68" 0.6 | Out-Null
    Add-Text $slide $phaseLabels[$i] ($px-35) ($cy+$ch+12) 70 30 8 "F4F8FF" $true 2 | Out-Null
}
Add-Text $slide "能力成熟度" ($cx-5) ($cy-22) 85 12 8 "8FA3B8" $true 1 | Out-Null

$series = @(
    @{name="产品能力"; color="38D9F7"; pts=@(@(90,315),@(285,250),@(490,170)); vals=@("MVP","机构版","平台化")},
    @{name="试点场景"; color="E4BF57"; pts=@(@(90,338),@(285,285),@(490,218)); vals=@("5+","30+","100+")},
    @{name="用户规模"; color="20D1B5"; pts=@(@(90,360),@(285,306),@(490,250)); vals=@("3k+","10w+","50w+")},
    @{name="商业化"; color="7EA6FF"; pts=@(@(90,380),@(285,340),@(490,292)); vals=@("试点","订阅","API")}
)
foreach ($s in $series) {
    for ($i=0; $i -lt 2; $i++) {
        Add-Line $slide ($cx+$s.pts[$i][0]) ($cy+$s.pts[$i][1]-140) ($cx+$s.pts[$i+1][0]) ($cy+$s.pts[$i+1][1]-140) $s.color 2.2 | Out-Null
    }
    for ($i=0; $i -lt 3; $i++) {
        Add-Marker $slide ($cx+$s.pts[$i][0]) ($cy+$s.pts[$i][1]-140) $s.color $s.vals[$i]
    }
}
for ($i=0; $i -lt $series.Count; $i++) {
    $lx = $cx + 18 + $i*102
    Add-Line $slide $lx ($cy+$ch+52) ($lx+26) ($cy+$ch+52) $series[$i].color 2 | Out-Null
    Add-Text $slide $series[$i].name ($lx+32) ($cy+$ch+45) 60 12 7 "8FA3B8" $true 1 | Out-Null
}

$cards = @(
    @{t="阶段一｜产品验证"; v="六大模块稳定上线`n完成种子用户闭环"; c="20D1B5"; n="01"},
    @{t="阶段二｜试点复制"; v="高校/基层场景协作`n形成标准化交付包"; c="38D9F7"; n="02"},
    @{t="阶段三｜规模拓展"; v="机构版与 API 服务`n沉淀行业数据资产"; c="E4BF57"; n="03"}
)
for ($i=0; $i -lt 3; $i++) {
    $x = 642; $y = 146 + $i*88
    Add-Line $slide $x $y ($x+242) $y $cards[$i].c 1.7 | Out-Null
    Add-Text $slide $cards[$i].t $x ($y+16) 190 18 13 "F4F8FF" $true 1 | Out-Null
    Add-Text $slide $cards[$i].v $x ($y+42) 220 32 9 "8FA3B8" $false 1 | Out-Null
    Add-Text $slide $cards[$i].n ($x+211) ($y+14) 32 16 12 $cards[$i].c $true 3 | Out-Null
}

$proof = @(
    @{k="3 条"; v="主增长曲线"; c="38D9F7"},
    @{k="5+→100+"; v="试点场景"; c="E4BF57"},
    @{k="3k → 50w"; v="服务人次"; c="20D1B5"},
    @{k="API"; v="规模化接口"; c="7EA6FF"}
)
for ($i=0; $i -lt 4; $i++) {
    $x = 64 + $i*155
    Add-Text $slide $proof[$i].k $x 445 120 22 17 $proof[$i].c $true 1 | Out-Null
    Add-Text $slide $proof[$i].v $x 474 120 12 8 "8FA3B8" $false 1 | Out-Null
}
Add-Text $slide "明鉴 AI法律文书智能助手" 44 515 170 10 6 "5D7085" $false 1 | Out-Null
Add-Text $slide "11" 904 510 24 14 9 "E4BF57" $true 3 | Out-Null

$pres.SaveAs($out)
$pres.SaveAs($desktopOut)
$pres.Close()
$ppt.Quit()

Get-Item -LiteralPath $desktopOut | Select-Object FullName,Length,LastWriteTime
