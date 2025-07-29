# stop-ollama.ps1
# Gracefully unload all Ollama models and stop the background server

# Get all models
try {
    $models = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get
    foreach ($m in $models.models) {
        Write-Output "Unloading model: $($m.name)"
        Invoke-RestMethod -Uri "http://localhost:11434/api/unload" -Method Post -Body (@{ model = $m.name } | ConvertTo-Json) -ContentType "application/json"
    }
} catch {
    Write-Output "Could not connect to Ollama API. Skipping unload."
}

# Kill all Ollama processes
$ollamaProcesses = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
foreach ($p in $ollamaProcesses) {
    Write-Output "Killing Ollama process ID $($p.Id)"
    Stop-Process -Id $p.Id -Force
}
Write-Output "✅ Ollama fully stopped and memory should be cleared."