param(
    [string]$BaseUrl = "http://127.0.0.1:8001",
    [string]$ExcelPath,
    [string]$Prompt = "Please answer concisely: What is ROE?",
    [string]$Prompt2 = "Please answer concisely: Provide a simple ROE example.",
    [string]$SessionId,
    [int]$Limit = 10,
    [int]$Turns = 1,
    [switch]$WithSnippet
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-ExcelPath {
    param([string]$Provided)
    if ($Provided) {
        $p = Resolve-Path -LiteralPath $Provided -ErrorAction Stop
        return $p.Path
    }
        $candidates = @(
            (Join-Path -Path $PSScriptRoot -ChildPath 'backend\app\Sample_Financial_Data.xlsx'),
            (Join-Path -Path (Split-Path -Parent $PSScriptRoot) -ChildPath 'backend\app\Sample_Financial_Data.xlsx'),
            (Join-Path -Path (Get-Location) -ChildPath 'backend\app\Sample_Financial_Data.xlsx')
        )
        foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c) { return (Resolve-Path $c).Path }
    }
    throw "Sample_Financial_Data.xlsx not found. Pass -ExcelPath explicitly."
}

function Wait-Backend {
    param([string]$Url, [int]$Retries = 30, [int]$DelayMs = 500)
    for ($i = 0; $i -lt $Retries; $i++) {
        try {
            $h = Invoke-RestMethod -Uri "$Url/health" -Method GET -TimeoutSec 5
            if ($h.status -eq 'ok') { return $true }
        } catch { }
        Start-Sleep -Milliseconds $DelayMs
    }
    return $false
}

function Find-BackendExe {
    $candidates = @(
        (Join-Path -Path $PSScriptRoot -ChildPath '..\ExcelAddIn\ExcelAddIn\backend\run_server.exe'),
        (Join-Path -Path $PSScriptRoot -ChildPath '..\backend\build\run_server\run_server.exe'),
        (Join-Path -Path $PSScriptRoot -ChildPath '..\backend\run_server\run_server.exe')
    ) | ForEach-Object { Resolve-Path -Path $_ -ErrorAction SilentlyContinue } | ForEach-Object { $_.Path }
    foreach ($p in $candidates) { if (Test-Path -LiteralPath $p) { return $p } }
    return $null
}

try {
    Write-Host "[1/6] Checking backend at $BaseUrl ..." -ForegroundColor Cyan
    if (-not (Wait-Backend -Url $BaseUrl)) {
        Write-Host "Backend not reachable. Attempting to start packaged backend..." -ForegroundColor Yellow
        $exe = Find-BackendExe
        if ($exe) {
            $wd = Split-Path -Parent $exe
            Write-Host "Starting: $exe" -ForegroundColor DarkGray
            Start-Process -FilePath $exe -WorkingDirectory $wd -WindowStyle Minimized | Out-Null
            # Packaged backend listens on 8000 by default; adjust if needed
            if ($BaseUrl -match '^http://127\.0\.0\.1:8001') { $BaseUrl = 'http://127.0.0.1:8000' }
            if (-not (Wait-Backend -Url $BaseUrl -Retries 60 -DelayMs 1000)) {
                throw "Backend failed to start at $BaseUrl."
            }
            Write-Host "Backend is up at $BaseUrl" -ForegroundColor DarkGreen
        } else {
            throw "Backend not reachable at $BaseUrl and no packaged backend found."
        }
    }

    Write-Host "[2/6] Resolving Excel path ..." -ForegroundColor Cyan
    $excel = Resolve-ExcelPath -Provided $ExcelPath
    Write-Host "Using Excel: $excel" -ForegroundColor DarkGray

    Write-Host "[3/6] Initializing index (/initialize) ..." -ForegroundColor Cyan
    $initBody = @{ path = $excel } | ConvertTo-Json
    $initResp = Invoke-RestMethod -Uri "$BaseUrl/initialize" -Method POST -ContentType 'application/json' -Body $initBody
    Write-Host ("Initialized: {0} snippets" -f $initResp.snippets) -ForegroundColor DarkGreen

    if (-not $SessionId -or [string]::IsNullOrWhiteSpace($SessionId)) {
        $SessionId = [guid]::NewGuid().Guid
    }
    Write-Host "[4/6] Sending chat (/chat) session=$SessionId ..." -ForegroundColor Cyan
    if ($WithSnippet) {
        $chatBody = @{ prompt = $Prompt; detailed = $false; session_id = $SessionId; snippets = @("Sample Financial Data snippet for logging") } | ConvertTo-Json
    } else {
        $chatBody = @{ prompt = $Prompt; detailed = $false; session_id = $SessionId } | ConvertTo-Json
    }
    $chatResp = Invoke-RestMethod -Uri "$BaseUrl/chat" -Method POST -ContentType 'application/json' -Body $chatBody
    Write-Host "Chat response (truncated):" -ForegroundColor DarkGray
    $preview = ($chatResp.response | Out-String).Trim()
    if ($preview.Length -gt 200) { $preview = $preview.Substring(0,200) + '...' }
    Write-Host $preview

    if ($Turns -gt 1) {
        Write-Host "[4b/6] Sending 2nd turn in same session ..." -ForegroundColor Cyan
        if ($WithSnippet) {
            $chatBody2 = @{ prompt = $Prompt2; detailed = $false; session_id = $SessionId; snippets = @("Sample Financial Data snippet for logging - turn2") } | ConvertTo-Json
        } else {
            $chatBody2 = @{ prompt = $Prompt2; detailed = $false; session_id = $SessionId } | ConvertTo-Json
        }
        $chatResp2 = Invoke-RestMethod -Uri "$BaseUrl/chat" -Method POST -ContentType 'application/json' -Body $chatBody2
        $preview2 = ($chatResp2.response | Out-String).Trim()
        if ($preview2.Length -gt 200) { $preview2 = $preview2.Substring(0,200) + '...' }
        Write-Host $preview2 -ForegroundColor DarkGray
    }

        Write-Host "[5/6] Fetching history (try unified -> grouped -> flat) ..." -ForegroundColor Cyan
        $hist = $null
        $histUris = @(
            "$BaseUrl/history/unified?limit=$Limit",
            "$BaseUrl/history/grouped?limit=$Limit",
            "$BaseUrl/history?limit=$Limit"
        )
        foreach ($u in $histUris) {
            try { $hist = Invoke-RestMethod -Uri $u -Method GET; if ($hist) { break } } catch { }
        }
        if (-not $hist) { throw "Unable to fetch history: all endpoints failed." }
        $count = ($hist | Measure-Object).Count
        Write-Host "History sessions/items returned: $count" -ForegroundColor DarkGreen

        Write-Host "[6/6] Opening session (try POST /history/open -> GET /history/session/{id} -> GET /history_session/{id}) ..." -ForegroundColor Cyan
        $openResp = $null
        try {
            $openBody = @{ session_id = $SessionId } | ConvertTo-Json
            $openResp = Invoke-RestMethod -Uri "$BaseUrl/history/open" -Method POST -ContentType 'application/json' -Body $openBody
        } catch { }
        if (-not $openResp) {
            try { $openResp = Invoke-RestMethod -Uri "$BaseUrl/history/session/$SessionId" -Method GET } catch { }
        }
        if (-not $openResp) {
            try { $openResp = Invoke-RestMethod -Uri "$BaseUrl/history_session/$SessionId" -Method GET } catch { }
        }
        if (-not $openResp) { throw "Unable to open session $SessionId via any endpoint." }

    Write-Host "[6/6] Opening session (/history/open) ..." -ForegroundColor Cyan
    $openBody = @{ session_id = $SessionId } | ConvertTo-Json
    $openResp = Invoke-RestMethod -Uri "$BaseUrl/history/open" -Method POST -ContentType 'application/json' -Body $openBody
    Write-Host ("Session {0}: {1} turns" -f $openResp.session_id, $openResp.turns) -ForegroundColor DarkGreen

    # Output a compact summary as JSON for CI/logs
    $summary = [pscustomobject]@{
        baseUrl = $BaseUrl
        excel = $excel
        session_id = $SessionId
        snippets = $initResp.snippets
        unified_count = $count
        turns = $openResp.turns
        title = $openResp.title
    }
    $summary | ConvertTo-Json -Depth 5
}
catch {
    Write-Error $_
    exit 1
}