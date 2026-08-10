# Cardia 방송 시작 스크립트 — 올바른 순서로 전부 켭니다.
#   사용법: 우클릭 → "PowerShell에서 실행" (또는: powershell -ExecutionPolicy Bypass -File start_stream.ps1)
#   -Live 스위치를 주면 녹화 대신 실제 방송 송출로 시작합니다:
#     powershell -ExecutionPolicy Bypass -File start_stream.ps1 -Live
#
# 순서가 중요한 이유: OBS는 CPU가 한가할 때 켜져야 QSV(하드웨어 인코더)를
# 잡습니다 (게임 켜진 뒤 OBS를 켜면 QSV 감지가 실패하는 것을 실측으로 확인).
param([switch]$Live, [switch]$TikTok, [switch]$YouTube)

# Pick the OBS profile (Twitch vs YouTube) before OBS starts — OBS reads the
# active profile from global.ini at launch, so switching here means the owner
# never has to touch OBS menus.
if ($Live -or $YouTube) {
    $wanted = if ($YouTube) { 'Cardia-YouTube' } else { 'Cardia' }
    # OBS 32 reads the active profile from user.ini; global.ini alone is
    # ignored (learned the hard way: a YouTube key landed in the Twitch
    # profile). Write BOTH so either OBS version picks it up.
    foreach ($f in @("$PSScriptRoot\tools\obs\config\obs-studio\user.ini",
                     "$PSScriptRoot\tools\obs\config\obs-studio\global.ini")) {
        if (Test-Path $f) {
            $fc = Get-Content $f -Raw
            $fc = $fc -replace '(?m)^Profile=.*', "Profile=$wanted"
            $fc = $fc -replace '(?m)^ProfileDir=.*', "ProfileDir=$wanted"
            # Balatro streams switch the scene collection; switch it back so a
            # Slay the Spire stream never runs with the Balatro scenes.
            $fc = $fc -replace '(?m)^SceneCollection=.*', 'SceneCollection=Cardia'
            $fc = $fc -replace '(?m)^SceneCollectionFile=.*\.json\s*$', 'SceneCollectionFile=Cardia.json'
            $fc = $fc -replace '(?m)^SceneCollectionFile=(?!Cardia\b)[^\r\n]*$', 'SceneCollectionFile=Cardia'
            [System.IO.File]::WriteAllText($f, $fc, (New-Object System.Text.UTF8Encoding $false))
        }
    }
    Write-Host ("      OBS 프로필: " + $wanted)
    $Live = $true
}

$ErrorActionPreference = 'Continue'
$kit = 'D:\ai-vtuber-kit'
$game = 'C:\Program Files (x86)\Steam\steamapps\common\SlayTheSpire'
$mts = 'C:\Program Files (x86)\Steam\steamapps\workshop\content\646570\1605060445\ModTheSpire.jar'

Write-Host '[1/4] veadotube (아바타)...'
if (Get-Process veadotube-mini -ErrorAction SilentlyContinue) {
    Write-Host '      이미 실행 중'
} else {
    Start-Process "$kit\tools\veadotube\veadotube-mini.exe" -WorkingDirectory "$kit\tools\veadotube"
    Write-Host '      실행함'
}

if ($TikTok) {
    Write-Host '[2/4] TikTok LIVE Studio 실행 (미리 띄워둡니다 - GO LIVE는 나중에)...'
    $studio = 'D:\TikTok LIVE Studio\TikTok LIVE Studio Launcher.exe'
    if (Get-Process | Where-Object { $_.Name -match 'TikTok' }) {
        Write-Host '      이미 실행 중'
    } elseif (Test-Path $studio) {
        Start-Process $studio
        Write-Host '      실행함 - 아직 GO LIVE 누르지 마세요! 두뇌 연결 후 안내합니다.'
    } else {
        Write-Host ('!!! LIVE Studio를 찾을 수 없습니다: ' + $studio)
    }
} else {
    Write-Host '[2/4] OBS 먼저 시작 (QSV 확보)...'
    if (-not (Get-Process obs64 -ErrorAction SilentlyContinue)) {
        $flag = if ($Live) { '--startstreaming' } else { '--startrecording' }
        Start-Process "$kit\tools\obs\bin\64bit\obs64.exe" -WorkingDirectory "$kit\tools\obs\bin\64bit" -ArgumentList $flag
        Write-Host '      OBS 부팅 대기 (40초)...'
        Start-Sleep -Seconds 40
    } else {
        Write-Host '      이미 실행 중 (방송/녹화 시작 버튼은 OBS에서 직접)'
    }
}

Write-Host '[3/4] Slay the Spire (모드 포함, 선택창 없음)...'
Remove-Item "$kit\logs\heartbeat.txt" -ErrorAction SilentlyContinue
Start-Process -FilePath "$game\jre\bin\java.exe" -ArgumentList @('-jar', "`"$mts`"", '--skip-launcher') -WorkingDirectory $game

Write-Host '[4/4] AI 두뇌 연결 대기... (방송 부하 중엔 게임 부팅이 5~10분 걸릴 수 있음 - 정상입니다)'
$hb = "$kit\logs\heartbeat.txt"
$deadline = (Get-Date).AddMinutes(12)
$connected = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 10
    if (Test-Path $hb) {
        $age = ((Get-Date) - (Get-Item $hb).LastWriteTime).TotalSeconds
        if ($age -lt 45) { $connected = $true; break }
    }
    Write-Host ('      대기 중... ' + (Get-Date -Format HH:mm:ss))
}
if ($connected) {
    Write-Host ''
    Write-Host '  ##################################################'
    Write-Host '  #   READY - AI CONNECTED / AI 두뇌 연결 완료     #'
    Write-Host '  #   Cardia is now playing. Leave this window open. #'
    Write-Host '  #   이 창을 닫지 마세요 (닫으면 방송 종료됩니다)  #'
    Write-Host '  ##################################################'
    if ($TikTok) {
        Write-Host ''
        Write-Host '  ====================================================='
        Write-Host '  이제 TikTok LIVE Studio 창으로 가서:'
        Write-Host '   1) 미리보기에 게임+아바타가 보이는지 확인'
        Write-Host '   2) GO LIVE 클릭'
        Write-Host '   3) Studio 창 최소화 (CPU 절약)'
        Write-Host '  ====================================================='
    }
} else {
    Write-Host '!!! 12분 안에 두뇌 연결 신호가 없습니다 - 게임 창이 떠 있는지, 오류 창이 없는지 확인하세요.'
}
Write-Host ''
if ($TikTok) {
    Write-Host '  긴급 음소거: Ctrl+F12  |  방송 종료: LIVE Studio에서 방송 종료 + 게임 창 닫기'
} else {
    Write-Host '  긴급 음소거: Ctrl+F12  |  방송 종료: OBS의 방송 중단 버튼 + 게임 창 닫기'
}
Write-Host '  로그: D:\ai-vtuber-kit\logs\  |  첫 방송들은 반드시 처음부터 끝까지 지켜보세요!'
