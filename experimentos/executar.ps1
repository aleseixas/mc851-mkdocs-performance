param(
    [string]$PythonExecutable = '',
    [int]$Repetitions = 10,
    [string]$RunName = ('reexecucao-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if ($RunName -notmatch '^[A-Za-z0-9_-]+$' -or $RunName -eq 'principal') {
    throw 'Use um nome simples e diferente de principal para preservar a coleta original.'
}
if (-not $PythonExecutable) {
    $bundledPython = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundledPython) { $PythonExecutable = $bundledPython }
    else { $PythonExecutable = (Get-Command python -ErrorAction Stop).Source }
}
$pythonVersion = & $PythonExecutable -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ($pythonVersion -ne '3.12') { throw 'Para reproduzir o ambiente, indique Python 3.12 em -PythonExecutable.' }
$scratchRoot = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) ('MC851A-MkDocs\' + $RunName)
$outputRoot = Join-Path $projectRoot ('resultados\' + $RunName)
if ((Test-Path -LiteralPath $scratchRoot) -or (Test-Path -LiteralPath $outputRoot)) { throw 'Diretório já existente. Escolha outro RunName.' }
[void](New-Item -ItemType Directory -Path $scratchRoot)
$environmentPath = Join-Path $scratchRoot 'venv'
& $PythonExecutable -m venv $environmentPath
if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar ambiente virtual.' }
$venvPython = Join-Path $environmentPath 'Scripts\python.exe'
& $venvPython -m pip install -r (Join-Path $PSScriptRoot 'requirements-lock.txt')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependências.' }
& $venvPython (Join-Path $PSScriptRoot 'benchmark.py') --work-dir (Join-Path $scratchRoot 'trabalho') --output-dir $outputRoot --repetitions $Repetitions
if ($LASTEXITCODE -ne 0) { throw 'Falha na coleta. Os registros parciais foram preservados.' }
& $venvPython (Join-Path $PSScriptRoot 'analisar.py') --run-dir $outputRoot --figures-dir (Join-Path $projectRoot ('graficos\' + $RunName))
if ($LASTEXITCODE -ne 0) { throw 'Falha na validação ou geração dos gráficos.' }
Write-Output ('Nova coleta: ' + $outputRoot)
Write-Output ('Python isolado: ' + $venvPython)
