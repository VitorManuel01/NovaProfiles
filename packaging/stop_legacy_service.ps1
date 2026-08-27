[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ServiceName = "GameSirAutoProfile"

try {
    $Service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($null -eq $Service) {
        Write-Host "O serviço antigo $ServiceName não está instalado."
        exit 0
    }

    if ($Service.Status -eq [System.ServiceProcess.ServiceControllerStatus]::Stopped) {
        Write-Host "O serviço antigo já está parado."
        exit 0
    }

    Write-Host "Parando o serviço antigo $ServiceName..."
    Stop-Service -InputObject $Service -ErrorAction Stop
    $Service.WaitForStatus(
        [System.ServiceProcess.ServiceControllerStatus]::Stopped,
        [TimeSpan]::FromSeconds(15)
    )
    $Service.Refresh()
    if ($Service.Status -ne [System.ServiceProcess.ServiceControllerStatus]::Stopped) {
        throw "o serviço não atingiu o estado parado em 15 segundos"
    }

    Write-Host ""
    Write-Host "Serviço parado. Este comando não remove nem desabilita o serviço."
    exit 0
}
catch {
    Write-Error "Não foi possível consultar ou parar o serviço: $($_.Exception.Message)"
    exit 1
}
