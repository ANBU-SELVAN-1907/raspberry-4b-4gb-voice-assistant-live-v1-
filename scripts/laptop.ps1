param(
  [Parameter(Mandatory=$true)][string]$PiHost,
  [Parameter(Mandatory=$true)][string]$PiUser
)
$ErrorActionPreference = 'Stop'
if ($PiHost -notmatch '^[a-zA-Z0-9.:-]+$' -or $PiUser -notmatch '^[a-zA-Z0-9_-]+$') {
  throw 'Provide a valid host/IP and username.'
}
Write-Host 'Keep this terminal open. After SSH connects, open http://127.0.0.1:8765 in your laptop browser.'
ssh -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -N -L 127.0.0.1:8765:127.0.0.1:8765 "$PiUser@$PiHost"
