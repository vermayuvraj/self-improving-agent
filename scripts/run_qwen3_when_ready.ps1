# Waits until qwen3:8b is downloaded AND no benchmark run is active (GPU free —
# concurrent runs would corrupt EXP-001's pre-registered latency metric), then
# runs qwen3:8b on both benchmarks with the same config as qwen2.5-coder:7b.
$ollama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"

function Test-SiaRunning {
    $procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue
    foreach ($p in $procs) { if ($p.CommandLine -match 'sia\b.*run|runner') { return $true } }
    return $false
}

Write-Output "waiting for qwen3:8b download and a free GPU..."
while ($true) {
    $have = (& $ollama list 2>$null) -match 'qwen3:8b'
    $busy = Test-SiaRunning
    if ($have -and -not $busy) { break }
    Start-Sleep -Seconds 60
}

Write-Output "=== qwen3:8b runs starting $(Get-Date -Format o) ==="
uv run sia run --bench humaneval --model qwen3:8b --seed 7
Write-Output "--- ollama ps (qwen3 humaneval) ---"; & $ollama ps
uv run sia run --bench mbpp --model qwen3:8b --seed 7
Write-Output "--- ollama ps (qwen3 mbpp) ---"; & $ollama ps
Write-Output "=== EXP-001 complete $(Get-Date -Format o) ==="
