[CmdletBinding()]
param(
    [ValidateSet('x64')]
    [string] $Target = 'x64',
    [ValidateSet('Debug', 'RelWithDebInfo', 'Release', 'MinSizeRel')]
    [string] $Configuration = 'RelWithDebInfo'
)

$ErrorActionPreference = 'Stop'

if ( $DebugPreference -eq 'Continue' ) {
    $VerbosePreference = 'Continue'
    $InformationPreference = 'Continue'
}

if ( $env:CI -eq $null ) {
    throw "Package-Windows.ps1 requires CI environment"
}

if ( ! ( [System.Environment]::Is64BitOperatingSystem ) ) {
    throw "Packaging script requires a 64-bit system to build and run."
}

if ( $PSVersionTable.PSVersion -lt '7.2.0' ) {
    Write-Warning 'The packaging script requires PowerShell Core 7. Install or upgrade your PowerShell version: https://aka.ms/pscore6'
    exit 2
}

function Package {
    trap {
        Write-Error $_
        exit 2
    }

    $ScriptHome = $PSScriptRoot
    $ProjectRoot = Resolve-Path -Path "$PSScriptRoot/../.."
    $BuildSpecFile = "${ProjectRoot}/buildspec.json"

    $UtilityFunctions = Get-ChildItem -Path $PSScriptRoot/utils.pwsh/*.ps1 -Recurse

    foreach( $Utility in $UtilityFunctions ) {
        Write-Debug "Loading $($Utility.FullName)"
        . $Utility.FullName
    }

    $BuildSpec = Get-Content -Path ${BuildSpecFile} -Raw | ConvertFrom-Json
    $ProductName = $BuildSpec.name
    $ProductVersion = $BuildSpec.version

    $OutputName = "${ProductName}-${ProductVersion}-windows-${Target}"

    $RemoveArgs = @{
        ErrorAction = 'SilentlyContinue'
        Path = @(
            "${ProjectRoot}/release/${ProductName}-*-windows-*.zip"
        )
    }

    Remove-Item @RemoveArgs

    Log-Group "Archiving ${ProductName}..."
    $CompressArgs = @{
        Path = (Get-ChildItem -Path "${ProjectRoot}/release/${Configuration}" -Exclude "${OutputName}*.*")
        CompressionLevel = 'Optimal'
        DestinationPath = "${ProjectRoot}/release/${OutputName}.zip"
        Verbose = ($Env:CI -ne $null)
    }
    Compress-Archive -Force @CompressArgs
    Log-Group

    Log-Group "Building installer for ${ProductName}..."

    # Inno Setup(ISCC) 위치: choco install innosetup 가 PATH shim + 표준 경로 둘 다 제공.
    $IsccPath = "${Env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if ( ! ( Test-Path $IsccPath ) ) {
        $IsccPath = (Get-Command 'iscc.exe' -ErrorAction SilentlyContinue).Source
    }
    if ( ! $IsccPath ) {
        throw "Inno Setup (ISCC.exe) not found. Install it (choco install innosetup) before packaging."
    }

    # cmake install 산출물: release/<config>/<name>/{bin/64bit,data}
    $InstallerSource = "${ProjectRoot}/release/${Configuration}/${ProductName}"
    $IssScript = "${ProjectRoot}/cmake/windows/resources/installer-windows.iss"

    $IsccArgs = @(
        "/DMyAppName=${ProductName}"
        "/DMyAppVersion=${ProductVersion}"
        "/DMyAppPublisher=$($BuildSpec.author)"
        "/DMySourceDir=${InstallerSource}"
        "/DMyOutputDir=${ProjectRoot}/release"
        "/DMyOutputBase=${OutputName}-installer"
        "${IssScript}"
    )

    & $IsccPath @IsccArgs
    if ( $LASTEXITCODE -ne 0 ) {
        throw "Inno Setup compilation failed with exit code ${LASTEXITCODE}."
    }
    Log-Group
}

Package
