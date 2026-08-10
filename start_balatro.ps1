# Cardia — Balatro stream launcher.
#   .\start_balatro.ps1            rehearsal (records locally, not live)
#   .\start_balatro.ps1 -YouTube   live on YouTube
#   .\start_balatro.ps1 -Twitch    live on Twitch
#
# Order matters: OBS must start while the CPU is idle or it fails to grab the
# QSV hardware encoder (measured on this machine).
param([switch]$YouTube, [switch]$Twitch)

$ErrorActionPreference = 'Continue'
$kit = 'D:\ai-vtuber-kit'
$live = $YouTube -or $Twitch

# Balatro is launched directly, NOT through `uv tool run balatrobot serve`.
# Windows Application Control started blocking uv's trampoline .exe and even
# the .pyd files of the Python uv had downloaded to D: ("os error 4551"), so
# the game would never start. On Windows that command only ever did two
# things: set these BALATROBOT_* variables and run Balatro.exe. The mod
# itself is loaded by version.dll (Lovely) sitting next to the game, so
# doing it here needs no Python 3.13, no uv, and nothing the policy blocks.
$balatro = 'C:\Program Files (x86)\Steam\steamapps\common\Balatro\Balatro.exe'
$lovely  = 'C:\Program Files (x86)\Steam\steamapps\common\Balatro\version.dll'
$env:BALATROBOT_HOST          = '127.0.0.1'
$env:BALATROBOT_PORT          = '12346'
$env:BALATROBOT_FPS_CAP       = '60'
$env:BALATROBOT_GAMESPEED     = '4'
$env:BALATROBOT_ANIMATION_FPS = '10'
$env:BALATROBOT_LOGS_PATH     = "$kit\logs"

Write-Host '[1/5] veadotube (avatar)...'
if (Get-Process veadotube-mini -ErrorAction SilentlyContinue) {
    Write-Host '      already running'
} else {
    Start-Process "$kit\tools\veadotube\veadotube-mini.exe" -WorkingDirectory "$kit\tools\veadotube"
    Write-Host '      started'
}

# Scene collection always switches to the Balatro one (it captures the
# Balatro window instead of Slay the Spire); the profile only decides where
# the stream goes.
$profile = if ($YouTube) { 'Cardia-YouTube' } elseif ($Twitch) { 'Cardia' } else { $null }
foreach ($f in @("$kit\tools\obs\config\obs-studio\user.ini",
                 "$kit\tools\obs\config\obs-studio\global.ini")) {
    if (Test-Path $f) {
        $fc = Get-Content $f -Raw
        if ($profile) {
            $fc = $fc -replace '(?m)^Profile=.*', "Profile=$profile"
            $fc = $fc -replace '(?m)^ProfileDir=.*', "ProfileDir=$profile"
        }
        # user.ini stores the file with a .json suffix, global.ini without it
        $fc = $fc -replace '(?m)^SceneCollection=.*', 'SceneCollection=Cardia-Balatro'
        $fc = $fc -replace '(?m)^SceneCollectionFile=.*\.json\s*$', 'SceneCollectionFile=Cardia-Balatro.json'
        $fc = $fc -replace '(?m)^SceneCollectionFile=(?!Cardia-Balatro)[^\r\n]*$', 'SceneCollectionFile=Cardia-Balatro'
        [System.IO.File]::WriteAllText($f, $fc, (New-Object System.Text.UTF8Encoding $false))
    }
}
if ($live) {
    Write-Host ("[2/5] OBS (profile: " + $profile + ", scenes: Cardia-Balatro, going live)...")
} else {
    Write-Host '[2/5] OBS (rehearsal: recording only, scenes: Cardia-Balatro)...'
}
if (-not (Get-Process obs64 -ErrorAction SilentlyContinue)) {
    $flag = if ($live) { '--startstreaming' } else { '--startrecording' }
    Start-Process "$kit\tools\obs\bin\64bit\obs64.exe" -WorkingDirectory "$kit\tools\obs\bin\64bit" -ArgumentList $flag
    Write-Host '      waiting 40s for OBS to boot...'
    Start-Sleep -Seconds 40
} else {
    Write-Host '      already running'
}

Write-Host '[3/5] Balatro with the bot mod...'
# balatrobot mutes the game on every launch (its configure_settings sets all
# three volumes to 0 and G.F_MUTE = true) unless BALATROBOT_AUDIO=1, which
# switches it to configure_audio() instead. Without this the game is silent on
# stream no matter what the in-game settings say.
$env:BALATROBOT_AUDIO = '1'
if (-not (Test-Path $balatro)) {
    Write-Host "!!! Balatro not found: $balatro"
    return
}
if (-not (Test-Path $lovely)) {
    Write-Host '!!! version.dll (Lovely injector) is missing, so the bot mod'
    Write-Host "    will not load and the API will never answer: $lovely"
    return
}
Start-Process -FilePath $balatro -WorkingDirectory (Split-Path $balatro)

# Start the brain NOW, not after the game is up: booting the claude CLI takes
# about a minute on this CPU, and doing it while Balatro loads means the first
# decision is instant instead of waiting ~66s for both.
Write-Host '[4/5] AI brain (warming up while the game loads)...'
Remove-Item "$kit\logs\heartbeat.txt" -ErrorAction SilentlyContinue
Start-Process -FilePath 'C:\Users\korea\AppData\Local\Programs\Python\Python312\python.exe' `
    -ArgumentList '-u', "$kit\orchestrator.py", '--balatro' `
    -WorkingDirectory $kit -WindowStyle Minimized `
    -RedirectStandardError "$kit\logs\balatro_brain.log"

Write-Host '[5/5] waiting for the Balatro API...'
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Seconds 5
    try {
        $r = Invoke-RestMethod -Uri 'http://127.0.0.1:12346' -Method Post `
             -ContentType 'application/json' `
             -Body '{"jsonrpc":"2.0","method":"health","id":1}' -TimeoutSec 5
        if ($r.result.status -eq 'ok') { $ready = $true; break }
    } catch { }
    Write-Host ('      waiting... ' + (Get-Date -Format HH:mm:ss))
}
if (-not $ready) {
    Write-Host '!!! Balatro API never answered. Is the game window open? Check for a mod crash screen.'
    return
}

$hb = "$kit\logs\heartbeat.txt"
$connected = $false
for ($i = 0; $i -lt 24; $i++) {
    Start-Sleep -Seconds 5
    if (Test-Path $hb) {
        if (((Get-Date) - (Get-Item $hb).LastWriteTime).TotalSeconds -lt 45) {
            $connected = $true; break
        }
    }
}
Write-Host ''
if ($connected) {
    Write-Host '  ##################################################'
    Write-Host '  #   READY - AI CONNECTED / AI 두뇌 연결 완료     #'
    Write-Host '  #   Cardia is playing Balatro now.               #'
    Write-Host '  #   이 창을 닫지 마세요 (닫으면 방송 종료됩니다)  #'
    Write-Host '  ##################################################'
} else {
    Write-Host '!!! 두뇌 연결 신호 없음 - logs\balatro_brain.log 를 확인하세요.'
}
Write-Host ''
Write-Host '  Mute: Ctrl+F12   |   Stop: close OBS + the Balatro window'
Write-Host '  Logs: D:\ai-vtuber-kit\logs\   |   Vault: D:\balatro'
