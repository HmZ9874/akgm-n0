param(
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [Parameter(Mandatory = $true)][int]$Brightness,
    [int]$Contrast = 1000,
    [int]$Resolution = 75,
    [int]$Extent = 96
)

$manager = New-Object -ComObject WIA.DeviceManager
$info = $manager.DeviceInfos | Where-Object { $_.Type -eq 1 } | Select-Object -First 1
if ($null -eq $info) { throw "No WIA scanner is available" }
$device = $info.Connect()
$item = $device.Items.Item(1)

function Set-WiaProperty([int]$id, [int]$value) {
    $property = $item.Properties | Where-Object { $_.PropertyID -eq $id }
    if ($null -eq $property) { throw "WIA property $id is unavailable" }
    $property.Value = $value
}

Set-WiaProperty 6147 $Resolution
Set-WiaProperty 6148 $Resolution
Set-WiaProperty 6149 0
Set-WiaProperty 6150 0
Set-WiaProperty 6151 $Extent
Set-WiaProperty 6152 $Extent
Set-WiaProperty 6154 $Brightness
Set-WiaProperty 6155 $Contrast

$bmpFormat = "{B96B3CAB-0728-11D3-9D7B-0000F81EF32E}"
$started = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
$image = $item.Transfer($bmpFormat)
$image.SaveFile($OutputPath)
$ended = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
$sha256 = [Security.Cryptography.SHA256]::Create()
$deviceHash = ($sha256.ComputeHash([Text.Encoding]::UTF8.GetBytes($info.DeviceID)) | ForEach-Object { $_.ToString("x2") }) -join ""
$sha256.Dispose()

[PSCustomObject]@{
    ok = $true
    device_id_sha256 = $deviceHash
    bytes = (Get-Item -LiteralPath $OutputPath).Length
    started_at_unix_ms = $started
    ended_at_unix_ms = $ended
    applied_resolution = $Resolution
    applied_extent = $Extent
} | ConvertTo-Json -Compress
