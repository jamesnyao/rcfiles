# Dev CLI - Shell Aliases
# Add this to your ~/.bashrc or ~/.zshrc:
#   source ~/.dev_scripts/aliases.sh

DEV_SCRIPTS="$HOME/.dev_scripts"
export PATH="$DEV_SCRIPTS:$PATH"

# Save original PATH for switching between enlistments
export OLD_PATH="${OLD_PATH:-$PATH}"

# Workspace base (override in ~/.bashrc before sourcing if different)
: ${DEV_WORKSPACE:=/workspace}

# Helper to construct PATH with depot_tools
_make_depot_path() {
    local depot_tools="$1"
    local use_shim="${2:-true}"  # Default: include dev_scripts for python shim
    
    if [[ "$use_shim" == "true" ]]; then
        echo "$DEV_SCRIPTS:$depot_tools:$depot_tools/scripts:$OLD_PATH"
    else
        echo "$depot_tools:$depot_tools/scripts:$OLD_PATH"
    fi
}

# Set to downstream Edge enlistment (uses depot_tools python, no shim)
set-downstream() {
    export DEPOT_TOOLS_PATH="$DEV_WORKSPACE/edge/depot_tools"
    export PATH="$(_make_depot_path "$DEPOT_TOOLS_PATH" false)"
    cd $DEV_WORKSPACE/edge/src
    echo "Set to downstream (edge) enlistment"
}

# Set to upstream Chromium enlistment (uses python shim)
set-upstream() {
    export DEPOT_TOOLS_PATH="$DEV_WORKSPACE/cr/depot_tools"
    export PATH="$(_make_depot_path "$DEPOT_TOOLS_PATH" false)"
    cd $DEV_WORKSPACE/cr/src
    echo "Set to upstream (cr) enlistment"
}

# Set to internal Edge enlistment (uses python shim)
set-clean() {
    export DEPOT_TOOLS_PATH="$DEV_WORKSPACE/edge/depot_tools"
    export PATH="$(_make_depot_path "$DEPOT_TOOLS_PATH" true)"
    export SISO_LIMITS=""
    export SISO_EXPERIMENTS=""
    echo "Set to workspace defaults"
}

# Reset PATH to original
set-no-depot-tools() {
    export PATH="$OLD_PATH"
    unset DEPOT_TOOLS_PATH
    echo "Reset PATH to $OLD_PATH"
}

set-dev-re() {
  export REAPI_ADDRESS="rbedev.westus3.cloudapp.azure.com:443"
  export REAPI_CAS_ADDRESS="rbecasdev.westus3.cloudapp.azure.com:443"
}

set-staging-re() {
  export REAPI_ADDRESS="rbestaging.westus3.cloudapp.azure.com:443"
  export REAPI_CAS_ADDRESS="rbecasstaging.westus3.cloudapp.azure.com:443"
}

set-prod-re() {
  export REAPI_ADDRESS="rbeprod.westus.cloudapp.azure.com:443"
  export REAPI_CAS_ADDRESS="rbecasprod.westus.cloudapp.azure.com:443"
}

set-remote-only() {
  export SISO_LIMITS="fastlocal=0"
  export SISO_EXPERIMENTS="no-fallback"
}