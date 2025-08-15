# Import the helper script
. .\DeployHelper.ps1

$remoteUser = "229192814"
$remoteHost = "34.87.46.188"
$remotePath = "/home/229192814/packaging_machine"

Deploy-Server -remoteUser $remoteUser -remoteHost $remoteHost -remotePath $remotePath