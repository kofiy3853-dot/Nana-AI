$scriptPath = Join-Path $PSScriptRoot "start_nana_v2.bat"
$arguments = "--background"
Start-Process -FilePath "cmd.exe" -ArgumentList "/c \`"$scriptPath\`" $arguments" -WindowStyle Hidden
