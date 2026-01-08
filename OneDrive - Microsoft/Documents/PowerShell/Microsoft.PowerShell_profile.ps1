# oh-my-posh init pwsh | Invoke-Expression
# ZSH-style colored prompt
function prompt {
  $lastSuccess = $?
  $currentPath = (Get-Location).Path
  
  # Get git branch if in a git repo
  $gitBranch = ""
  try {
    $branch = git branch --show-current 2>$null
    if ($branch) {
      $gitBranch = " `e[33m($branch)`e[0m"
    }
  } catch {}
  
  # Custom machine name
  if ($env:COMPUTERNAME -like "CPC-jamya*") {
    $hostName = "devbox"
  } elseif ($env:COMPUTERNAME -eq "JAMYAO-DEV") {
    $hostName = "devbox"
  } elseif ($env:COMPUTERNAME -eq "JAMYAO-SURFACE") {
    $hostName = "surface"
  } else {
    $hostName = $env:COMPUTERNAME.ToLower()
  }
  
  # User@Host in green (like zsh default)
  $userHost = "`e[32mjamyao-dev@$hostName`e[0m"
  
  # Path in blue (like zsh default)
  $pathDisplay = "`e[34m$currentPath`e[0m"
  
  # Prompt char: red if last command failed, otherwise default
  if ($lastSuccess) {
    $promptChar = "`e[0m$ "
  } else {
    $promptChar = "`e[31m$ `e[0m"
  }
  
  return "$userHost $pathDisplay$gitBranch`n$promptChar"
}


# Check if choco is installed
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
  Write-Output "Chocolatey is not installed. Installing..."
  winget install "Chocolatey.Chocolatey"
}

# Import the Chocolatey Profile that contains the necessary code to enable
# tab-completions to function for `choco`.
# Be aware that if you are missing these lines from your profile, tab completion
# for `choco` will not function.
# See https://ch0.co/tab-completion for details.
$ChocolateyProfile = "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1"
if (Test-Path($ChocolateyProfile)) {
  Import-Module "$ChocolateyProfile"
}

try {
  Invoke-Expression (& { (zoxide init --cmd cd powershell | Out-String) })
} catch {
  winget install ajeetdsouza.zoxide
  choco install fzf
  Invoke-Expression (& { (zoxide init --cmd cd powershell | Out-String) })
}

$env:PATH_BASE = $env:PATH
if ($env:COMPUTERNAME -like "CPC-jamya*") {
  $env:MachineType = "dev-cloud"
  $env:Dev = "Q:\dev"
  $env:DownEnlistRoot = "Q:\edge"
  $env:UpEnlistRoot = "Q:\cr"
}
elseif ($env:COMPUTERNAME -eq "JAMYAO-DEV") {
  $env:MachineType = "dev"
  $env:Dev = "X:\dev"
  $env:DownEnlistRoot = "X:\edge"
  $env:UpEnlistRoot = "X:\cr"
}
elseif ($env:COMPUTERNAME -eq "JAMYAO-SURFACE") {
  $env:MachineType = "dev"
  $env:Dev = "C:\dev"
  $env:DownEnlistRoot = "C:\edge"
  $env:UpEnlistRoot = "C:\cr"
}
$env:DEPOT_TOOLS_PREVIEW_RING = 1

$env:PATH_PREFIX="C:\Users\jamyao\scripts"

function Set-Downstream() {
  # Set up depot_tools
  $env:DEPOT_TOOLS_PATH = "$env:DownEnlistRoot\depot_tools"
  $env:PATH = "$env:PATH_PREFIX;$env:DEPOT_TOOLS_PATH;$env:DEPOT_TOOLS_PATH\scripts;$env:PATH_BASE"
  #$env:SISO_LIMITS = "fastlocal=8,startlocal=12"
  $env:REPROXY_CFG = "$env:DownEnlistRoot\src\buildtools\reclient_cfgs\reproxy.cfg"
  Set-Location "$env:DownEnlistRoot\src"
  Write-Output "Depot Tools set up for Edge Downstream"
}

function Set-Upstream() {
  # Set up depot_tools
  $env:DEPOT_TOOLS_PATH = "$env:UpEnlistRoot\depot_tools"
  $env:PATH = "$env:PATH_PREFIX;$env:DEPOT_TOOLS_PATH;$env:DEPOT_TOOLS_PATH\scripts;$env:PATH_BASE"
  #$env:SISO_LIMITS = "fastlocal=8,startlocal=12"
  $env:REPROXY_CFG = "$env:UpEnlistRoot\src\buildtools\reclient_cfgs\reproxy.cfg"
  Set-Location "$env:UpEnlistRoot\src"
  Write-Output "Depot Tools set up for Edge Upstream"
}

function Set-Internal() {
  # Set up depot_tools
  $env:DEPOT_TOOLS_PATH = "$env:Dev\depot_tools"
  $env:PATH = "$env:PATH_PREFIX;$env:DEPOT_TOOLS_PATH;$env:DEPOT_TOOLS_PATH\scripts;$env:PATH_BASE"
  Set-Location $env:Dev
  Write-Output "Depot Tools set up for $env:Dev"
}

function Set-CrDT() {
  # Set up depot_tools
  $env:DEPOT_TOOLS_PATH = "$env:Dev\depot_tools.cr"
  $env:PATH = "$env:PATH_PREFIX;$env:DEPOT_TOOLS_PATH;$env:PATH_BASE"
  $env:SISO_PATH = "$env:Dev\infra\go\src\infra\build\siso\siso"
  #Set-Location "$env:Dev\infra"
  Write-Output "Depot Tools set up for $env:Dev"
}

function Set-SisoPath() {
  $env:SISO_PATH = "$env:Dev\infra\go\src\infra\build\siso\siso"
  Write-Output "Depot Tools set up for SISO Path $env:Dev"
}

function Set-RemoteOnly() {
  $env:SISO_LIMITS = "fastlocal=0,startlocal=0"
  $env:SISO_EXPERIMENTS = "no-fallback"
}

function Set-DevRE() {
  $env:REAPI_CAS_ADDRESS = "rbecasdev.westus3.cloudapp.azure.com:443"
  $env:REAPI_ADDRESS = "rbedev.westus3.cloudapp.azure.com:443"
}

function Set-StagingRE() {
  $env:REAPI_CAS_ADDRESS = "rbecasstaging.westus3.cloudapp.azure.com:443"
  $env:REAPI_ADDRESS = "rbestaging.westus3.cloudapp.azure.com:443"
}

function Set-ProdRE() {
  $env:REAPI_CAS_ADDRESS = "rbecasprod.westus.cloudapp.azure.com:443"
  $env:REAPI_ADDRESS = "rbeprod.westus.cloudapp.azure.com:443"
}

function Set-Clean() {
  # No depot_tools
  $env:DEPOT_TOOLS_PATH = ""
  $env:PATH = "$env:PATH_PREFIX;$env:PATH_BASE"
  $env:SISO_LIMITS = ""
  $env:SISO_PATH = ""
  $env:SISO_EXPERIMENTS = ""
  Write-Output "Clean PATH $env:Dev"
}

if ($env:MachineType -eq "dev-cloud") {
  
}
else {

}



#Set-Clean
Set-Internal
