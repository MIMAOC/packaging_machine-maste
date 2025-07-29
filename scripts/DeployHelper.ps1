function Deploy-Server {
    param (
        [string]$remoteUser,
        [string]$remoteHost,
        [string]$remotePath
    )

    $scriptPath = $PSScriptRoot
    try {
        $ErrorActionPreference = 'Stop'

        # Resolve the full path of the server directory
        $serverDirectory = Resolve-Path "$scriptPath\..\backend"
        
        if (-not (Test-Path $serverDirectory)) {
            throw "Server directory not found: $serverDirectory"
        }

        Set-Location $serverDirectory

        # Create a tar archive excluding the 'venv' directory
        $tarFilePath = "./server.tar"
        Write-Host "Creating tar archive excluding 'venv'..."

        tar --exclude='venv' -cvf $tarFilePath .
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create tar archive."
        }

        # Use SCP to transfer the tar archive to the remote server
        Write-Host "Transferring tar archive to remote server..."
        scp $tarFilePath "${remoteUser}@${remoteHost}:${remotePath}"
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to transfer tar archive to the remote server."
        }

        # Execute commands on the remote server to extract the tar file, build, and start Docker Compose
        $sshScript = @"
    cd $remotePath
    tar -xvf $tarFilePath
    rm $tarFilePath
    # Remove dangling builders
    sudo docker builder prune -a -f
    # Remove dangling images
    sudo docker image prune -a -f
    sudo docker build -t packaging_machine .
    sudo docker stop packaging_machine
    sudo docker rm packaging_machine
    sudo docker run -d --name packaging_machine -p 8080:8080 packaging_machine
"@

        # Connect to the remote server via SSH and execute the script
        Write-Host "Running docker-compose on the remote server..."
        ssh -n $remoteUser@$remoteHost $sshScript
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to execute docker-compose on the remote server."
        }

        Write-Host "Deployment completed successfully."
    }
    catch {
        Write-Host $_.Exception.Message
    }
    finally {
        # Clean up the local tar file
        if (Test-Path $tarFilePath) {
            Remove-Item $tarFilePath
        }

        Set-Location $scriptPath
    }
}
