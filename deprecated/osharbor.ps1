# Pass -PythonExe if python on PATH is a Windows Store placeholder.
param([string]$PythonExe = 'python', [Parameter(ValueFromRemainingArguments=$true)][string[]]$CliArgs)
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    & $PythonExe -m osharbor @CliArgs
    $commandExit = $LASTEXITCODE
} finally { Pop-Location }
exit $commandExit
