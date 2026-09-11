param([string]$OutputPath)
$ErrorActionPreference = 'Stop'
$report = [ordered]@{ capturedAt = (Get-Date).ToUniversalTime().ToString('o') }
try { $report.firmware = (Get-ComputerInfo -Property BiosFirmwareType).BiosFirmwareType.ToString() } catch { $report.firmwareError = $_.Exception.Message }
$report.volumes = @(Get-Volume | Select-Object UniqueId,DriveLetter,FileSystemLabel,FileSystem,SizeRemaining)
$report.partitions = @(Get-Partition | Select-Object DiskNumber,PartitionNumber,Guid,GptType,Offset,Size,IsBoot,IsSystem)
try { $report.secureBoot = Confirm-SecureBootUEFI } catch { $report.secureBootError = $_.Exception.Message }
$report.bcd = @(& bcdedit.exe /enum all 2>&1 | ForEach-Object { "$_" })
$report.bcdExitCode = $LASTEXITCODE
$report.firmwareEntries = @(& bcdedit.exe /enum firmware 2>&1 | ForEach-Object { "$_" })
$report.firmwareEntriesExitCode = $LASTEXITCODE
$report.note = 'Read-only. ESP contents were not mounted or hashed. Access-denied output is not verification.'
$json = $report | ConvertTo-Json -Depth 8
if ($OutputPath) { $json | Set-Content -LiteralPath $OutputPath -Encoding utf8 } else { $json }
