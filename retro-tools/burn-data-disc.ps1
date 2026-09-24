param(
  [Parameter(Mandatory=$true)][string]$Source,
  [Parameter(Mandatory=$true)][string]$Drive
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Source -PathType Container)) { throw 'Burn source folder does not exist.' }
if ($Drive -notmatch '^[A-Za-z]:$') { throw 'Invalid optical drive letter.' }
$master = New-Object -ComObject IMAPI2.MsftDiscMaster2
$recorder = $null
foreach ($id in $master) {
  $candidate = New-Object -ComObject IMAPI2.MsftDiscRecorder2
  $candidate.InitializeDiscRecorder($id)
  foreach ($path in $candidate.VolumePathNames) {
    if ($path.Substring(0,2).ToUpperInvariant() -eq $Drive.ToUpperInvariant()) { $recorder = $candidate; break }
  }
  if ($recorder) { break }
}
if (-not $recorder) { throw "No IMAPI recorder found for $Drive" }
$writer = New-Object -ComObject IMAPI2.MsftDiscFormat2Data
$writer.Recorder = $recorder
$writer.ClientName = 'Disk Dude'
if (-not $writer.IsCurrentMediaSupported($recorder)) { throw 'The inserted media cannot be written by this recorder.' }
if (-not $writer.MediaHeuristicallyBlank) { throw 'The inserted media is not blank. Insert a blank writable CD.' }
$image = New-Object -ComObject IMAPI2FS.MsftFileSystemImage
$image.ChooseImageDefaults($recorder)
$image.FileSystemsToCreate = 3
$image.Root.AddTree((Resolve-Path -LiteralPath $Source).Path, $false)
$result = $image.CreateResultImage()
$writer.Write($result.ImageStream)
Write-Output "Burn complete on $Drive"
