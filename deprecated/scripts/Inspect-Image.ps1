param([Parameter(Mandatory=$true)][string]$Path)
$ErrorActionPreference = 'Stop'
$imagePath = (Resolve-Path -LiteralPath $Path).Path
$report = [ordered]@{ path=$imagePath; size=(Get-Item -LiteralPath $imagePath).Length; boot='pending' }
if (Get-Command Get-VHD -ErrorAction SilentlyContinue) {
  $report.vhd = Get-VHD -Path $imagePath | Select-Object VhdFormat,VhdType,Size,FileSize,Attached,ParentPath
} else { $report.note = 'Hyper-V Get-VHD unavailable; use osharbor register for header/footer checks.' }
$report | ConvertTo-Json -Depth 5
