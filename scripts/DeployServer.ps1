# Import the helper script
. .\DeployHelper.ps1

$remoteUser = "root"
#$remoteHost = "algormula.com"
$remoteHost = "114.55.151.130"
$remotePath = "/root/packaging_machine"

Deploy-Server -remoteUser $remoteUser -remoteHost $remoteHost -remotePath $remotePath