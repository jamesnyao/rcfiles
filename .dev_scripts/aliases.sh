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
    echo "Set to downstream (edge) enlistment"
}

# Set to internal Edge enlistment (uses python shim)
set-internal() {
    export DEPOT_TOOLS_PATH="$DEV_WORKSPACE/edge/depot_tools"
    export PATH="$(_make_depot_path "$DEPOT_TOOLS_PATH" true)"
    echo "Set to internal (edge) enlistment with python shim"
}

# Set to upstream Chromium enlistment (uses python shim)
set-upstream() {
    export DEPOT_TOOLS_PATH="$DEV_WORKSPACE/cr/depot_tools"
    export PATH="$(_make_depot_path "$DEPOT_TOOLS_PATH" true)"
    echo "Set to upstream (cr) enlistment"
}

# Set to upstream depot_tools (cr/depot_tools, uses python shim)
set-crdt() {
    export DEPOT_TOOLS_PATH="$DEV_WORKSPACE/cr/depot_tools"
    export PATH="$(_make_depot_path "$DEPOT_TOOLS_PATH" true)"
    echo "Set to cr/depot_tools"
}

# Reset PATH to original
reset-path() {
    export PATH="$OLD_PATH"
    unset DEPOT_TOOLS_PATH
    echo "Reset PATH to original"
}