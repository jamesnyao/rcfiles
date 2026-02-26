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
  
  $userHostName = "jamyao"

  # Custom machine name
  if ($env:COMPUTERNAME -like "CPC-jamya*") {
    $hostName = "cloud-devbox"
  } elseif ($env:COMPUTERNAME -eq "JAMYAO-DEVBOX") {
    $hostName = "devbox"
  } elseif ($env:COMPUTERNAME -eq "JAMYAO-SURFACE") {
    $hostName = "surface"
  } else {
    $hostName = $env:COMPUTERNAME.ToLower()
    $userHostName = $env:USERNAME
  }

  # Dev config
  $env:DEVCONFIG = "win-$hostname"
  
  # User@Host in green (like zsh default)
  $userHost = "`e[32m$userHostName@$hostName`e[0m"
  
  # Path in blue (like zsh default)
  $pathDisplay = "`e[96m$currentPath`e[0m"
  
  # Prompt char: red if last command failed, otherwise default
  if ($lastSuccess) {
    $promptChar = "`e[0m$ "
  } else {
    $promptChar = "`e[31m$ `e[0m"
  }
  
  return "$userHost $pathDisplay$gitBranch $promptChar"
}

# Set PATH values
if (-not ($env:PATH -like "*$env:USERPROFILE\.dev_scripts*")) {
  $env:PATH = "$env:USERPROFILE\.dev_scripts;$env:PATH"
}
if (-not ($env:PATH -like "*$env:USERPROFILE\.local\bin*")) {
  $env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
}
if (-not ($env:PATH -like "*$env:ProgramFiles\GitHub CLI*")) {
  $env:PATH = "$env:ProgramFiles\GitHub CLI;$env:PATH"
}
if (-not ($env:PATH -like "*$env:ProgramFiles\LLVM\bin*")) {
  $env:PATH = "$env:ProgramFiles\LLVM\bin;$env:PATH"
}

# Check if choco is installed
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
  Write-Output "Chocolatey is not installed. Installing..."
  winget install "Chocolatey.Chocolatey" --source winget
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
  winget install ajeetdsouza.zoxide --source winget
  choco install fzf
  Invoke-Expression (& { (zoxide init --cmd cd powershell | Out-String) })
}

$env:OLD_PATH = $env:PATH
if ($env:COMPUTERNAME -eq "JAMYAO-DEVBOX") {
  $env:MachineType = "dev"
  $env:Dev = "D:\dev"
  $env:DownEnlistRoot = "D:\dev\edge"
  $env:UpEnlistRoot = "D:\dev\cr"
}
elseif ($env:COMPUTERNAME -eq "JAMYAO-SURFACE") {
  $env:MachineType = "dev"
  $env:Dev = "C:\dev"
  $env:DownEnlistRoot = "C:\dev\edge"
  $env:UpEnlistRoot = "C:\dev\cr"
}
elseif ($env:COMPUTERNAME -eq "NEXUS") {
  $env:MachineType = "dev"
  $env:Dev = "D:\dev"
  $env:NonMsft = $true
}
$env:DEPOT_TOOLS_PREVIEW_RING = 1


function Set-Downstream() {
  if ([string]::IsNullOrEmpty($env:DownEnlistRoot)) {
    return
  }
  # Set up depot_tools
  $env:DEPOT_TOOLS_PATH = "$env:DownEnlistRoot\depot_tools"
  $env:PATH = "$env:DEPOT_TOOLS_PATH;$env:DEPOT_TOOLS_PATH\scripts;$env:OLD_PATH"
  Set-Location "$env:DownEnlistRoot\src"
  Write-Output "Depot Tools set up for Edge Downstream"
}

function Set-Upstream() {
  if ([string]::IsNullOrEmpty($env:UpEnlistRoot)) {
    return
  }
  # Set up depot_tools
  $env:DEPOT_TOOLS_PATH = "$env:UpEnlistRoot\depot_tools"
  $env:PATH = "$env:USERPROFILE\.dev_scripts;$env:DEPOT_TOOLS_PATH;$env:DEPOT_TOOLS_PATH\scripts;$env:OLD_PATH"
  Set-Location "$env:UpEnlistRoot\src"
  Write-Output "Depot Tools set up for Edge Upstream"
}

function Set-Internal() {
  if (![string]::IsNullOrEmpty($env:DownEnlistRoot)) {
    # Set up depot_tools
    $env:DEPOT_TOOLS_PATH = "$env:DownEnlistRoot\depot_tools"
    $env:PATH = "$env:USERPROFILE\.dev_scripts;$env:DEPOT_TOOLS_PATH;$env:DEPOT_TOOLS_PATH\scripts;$env:OLD_PATH"
  }
  Set-Location $env:Dev
}

function Set-SisoPath() {
  $env:SISO_PATH = "$env:Dev\infra\go\src\infra\build\siso\siso"
  Write-Output "Depot Tools set up for SISO Path $env:Dev"
}

function Set-RemoteOnly() {
  $env:SISO_EXPERIMENTS = "no-fallback"
}

function Set-DevRE() {
  $env:REAPI_CAS_ADDRESS = "rbecasdev.westus3.cloudapp.azure.com:443"
  $env:REAPI_ADDRESS = "rbedev.westus3.cloudapp.azure.com:443"
  $env:SISO_EXPERIMENTS=""
  $env:SISO_LIMITS = "fastlocal=0,local=1,remote=24"
}

function Set-StagingRE() {
  $env:REAPI_CAS_ADDRESS = "rbecasstaging.westus3.cloudapp.azure.com:443"
  $env:REAPI_ADDRESS = "rbestaging.westus3.cloudapp.azure.com:443"
  $env:SISO_EXPERIMENTS=""
  $env:SISO_LIMITS = "fastlocal=0,local=1,remote=24"
}

function Set-ProdRE() {
  $env:REAPI_CAS_ADDRESS = "rbecasprod.westus.cloudapp.azure.com:443"
  $env:REAPI_ADDRESS = "rbeprod.westus.cloudapp.azure.com:443"
  $env:SISO_EXPERIMENTS=""
  $env:SISO_LIMITS = "fastlocal=0,local=1"
}

function Set-Clean() {
  $env:DEPOT_TOOLS_PATH = "$env:Dev\edge\depot_tools"
  $env:PATH = "$env:USERPROFILE\.dev_scripts;$env:DEPOT_TOOLS_PATH;$env:DEPOT_TOOLS_PATH\scripts;$env:OLD_PATH"
  $env:SISO_LIMITS = ""
  $env:SISO_PATH = ""
  $env:SISO_EXPERIMENTS = ""
  Write-Output "Clean PATH $env:Dev"
}

# Dev CLI
function dev {
  if (Get-Command py -ErrorAction SilentlyContinue) {
    py "$env:USERPROFILE\.dev_scripts\dev.py" @args
  } elseif ($args.Count -ge 1 -and $args[0] -eq 'python') {
    Write-Host "Python not found. Bootstrapping via winget..." -ForegroundColor Blue
    winget install Python.Python.3.12 --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -eq 0) {
      Write-Host "Python installed. Restart your terminal to use it." -ForegroundColor Green
    } else {
      Write-Host "Failed to install Python." -ForegroundColor Red
    }
  } else {
    Write-Host "Python is not installed. Run 'dev python update' to bootstrap it." -ForegroundColor Red
  }
}

function copilot {
  & "agency" copilot --allow-all @args
}

function claude {
  & "claude.exe" --allow-dangerously-skip-permissions @args
}

function cop {
  Set-Internal
  if ($env:NonMsft) {
    & "claude" @args
  } else {
    & "copilot" @args
  }
}

if ($PWD.Path -like "$HOME") {
  Set-Internal
}
