# EXP-001 scope control: qwen3:8b measured at ~96 s/task (18x qwen2.5-coder:7b),
# making its MBPP arm a ~13 h run. Let the HumanEval arm finish for a real
# head-to-head, then stop the scheduler before it starts MBPP. Deviation is
# documented in EXPERIMENTS.md.
$runDir = "runs\7656889d539c"

while ($true) {
    $m = Get-Content "$runDir\manifest.json" -Raw -ErrorAction SilentlyContinue | ConvertFrom-Json
    if ($m.outcome -eq "completed") { break }
    Start-Sleep -Seconds 60
}
Write-Output "qwen3 humaneval completed: pass@1=$($m.totals.'pass@1')"

# Stop the scheduler and any qwen3 MBPP run it may have just launched.
Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'run_qwen3_when_ready|--bench mbpp --model qwen3' } |
    ForEach-Object {
        Write-Output "stopping pid=$($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
Write-Output "=== qwen3 MBPP arm skipped by design ==="
