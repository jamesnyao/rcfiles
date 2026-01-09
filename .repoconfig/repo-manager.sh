#!/bin/bash
# Repo Manager - Cross-platform repository synchronization tool
# Usage: repo-manager.sh <command> [args]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/repos.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Linux*)  echo "linux";;
        Darwin*) echo "darwin";;
        MINGW*|MSYS*|CYGWIN*) echo "windows";;
        *)       echo "linux";;
    esac
}

OS=$(detect_os)

# Get base path for current OS
get_base_path() {
    jq -r ".defaultBasePaths.$OS" "$CONFIG_FILE"
}

# Initialize config if needed
init_config() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        cat > "$CONFIG_FILE" << 'EOF'
{
  "version": 1,
  "description": "Tracked repositories for cross-machine sync",
  "defaultBasePaths": {
    "linux": "/workspace",
    "darwin": "/workspace",
    "windows": "C:\\dev"
  },
  "repos": []
}
EOF
        echo -e "${GREEN}Initialized config at $CONFIG_FILE${NC}"
    fi
}

# Add a repo to tracking
add_repo() {
    local repo_path="$1"
    
    if [[ -z "$repo_path" ]]; then
        echo -e "${RED}Error: Please provide a repository path${NC}"
        echo "Usage: repo-manager.sh add <path>"
        exit 1
    fi

    # Resolve to absolute path
    repo_path="$(cd "$repo_path" 2>/dev/null && pwd)" || {
        echo -e "${RED}Error: Directory does not exist: $repo_path${NC}"
        exit 1
    }

    # Check if it's a git repo
    if [[ ! -d "$repo_path/.git" ]]; then
        echo -e "${RED}Error: Not a git repository: $repo_path${NC}"
        exit 1
    fi

    # Get git remote URL
    local remote_url
    remote_url=$(git -C "$repo_path" remote get-url origin 2>/dev/null) || {
        echo -e "${YELLOW}Warning: No 'origin' remote found. Adding without remote URL.${NC}"
        remote_url=""
    }

    # Get relative name (last component of path)
    local repo_name
    repo_name=$(basename "$repo_path")

    # Check if already tracked
    local existing
    existing=$(jq -r --arg name "$repo_name" '.repos[] | select(.name == $name) | .name' "$CONFIG_FILE")
    if [[ -n "$existing" ]]; then
        echo -e "${YELLOW}Repository '$repo_name' is already tracked. Updating...${NC}"
        # Update existing entry
        local tmp_file
        tmp_file=$(mktemp)
        jq --arg name "$repo_name" --arg url "$remote_url" --arg path "$repo_path" \
            '(.repos[] | select(.name == $name)) |= {name: $name, remoteUrl: $url, addedFrom: $path, addedAt: (now | todate)}' \
            "$CONFIG_FILE" > "$tmp_file" && mv "$tmp_file" "$CONFIG_FILE"
    else
        # Add new entry
        local tmp_file
        tmp_file=$(mktemp)
        jq --arg name "$repo_name" --arg url "$remote_url" --arg path "$repo_path" \
            '.repos += [{name: $name, remoteUrl: $url, addedFrom: $path, addedAt: (now | todate)}]' \
            "$CONFIG_FILE" > "$tmp_file" && mv "$tmp_file" "$CONFIG_FILE"
    fi

    echo -e "${GREEN}Added repository: $repo_name${NC}"
    echo -e "  Remote: ${BLUE}$remote_url${NC}"
    echo -e "  Path: $repo_path"
}

# Remove a repo from tracking
remove_repo() {
    local repo_name="$1"
    
    if [[ -z "$repo_name" ]]; then
        echo -e "${RED}Error: Please provide a repository name${NC}"
        echo "Usage: repo-manager.sh remove <name>"
        exit 1
    fi

    local existing
    existing=$(jq -r --arg name "$repo_name" '.repos[] | select(.name == $name) | .name' "$CONFIG_FILE")
    if [[ -z "$existing" ]]; then
        echo -e "${RED}Repository '$repo_name' is not tracked${NC}"
        exit 1
    fi

    local tmp_file
    tmp_file=$(mktemp)
    jq --arg name "$repo_name" '.repos |= map(select(.name != $name))' "$CONFIG_FILE" > "$tmp_file" && mv "$tmp_file" "$CONFIG_FILE"

    echo -e "${GREEN}Removed repository: $repo_name${NC}"
}

# List all tracked repos
list_repos() {
    echo -e "${BLUE}Tracked Repositories:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local count
    count=$(jq '.repos | length' "$CONFIG_FILE")
    
    if [[ "$count" -eq 0 ]]; then
        echo -e "${YELLOW}No repositories tracked yet.${NC}"
        echo "Use 'repo-manager.sh add <path>' to add a repository."
        return
    fi

    jq -r '.repos[] | "  \(.name)\n    Remote: \(.remoteUrl // "N/A")\n    Added: \(.addedAt // "Unknown")\n"' "$CONFIG_FILE"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "Total: ${GREEN}$count${NC} repositories"
}

# Sync/clone repos to current machine
sync_repos() {
    local base_path
    base_path=$(get_base_path)
    
    echo -e "${BLUE}Syncing repositories to: $base_path${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    local count
    count=$(jq '.repos | length' "$CONFIG_FILE")
    
    if [[ "$count" -eq 0 ]]; then
        echo -e "${YELLOW}No repositories to sync.${NC}"
        return
    fi

    # Create base path if needed
    mkdir -p "$base_path"

    local synced=0
    local skipped=0
    local failed=0

    while IFS= read -r repo; do
        local name url
        name=$(echo "$repo" | jq -r '.name')
        url=$(echo "$repo" | jq -r '.remoteUrl')
        
        local target_path="$base_path/$name"

        if [[ -d "$target_path" ]]; then
            echo -e "${YELLOW}⏭ Skipping $name (already exists at $target_path)${NC}"
            ((skipped++))
            continue
        fi

        if [[ -z "$url" || "$url" == "null" ]]; then
            echo -e "${RED}✗ Cannot clone $name (no remote URL)${NC}"
            ((failed++))
            continue
        fi

        echo -e "${BLUE}⬇ Cloning $name...${NC}"
        if git clone "$url" "$target_path"; then
            echo -e "${GREEN}✓ Cloned $name${NC}"
            ((synced++))
        else
            echo -e "${RED}✗ Failed to clone $name${NC}"
            ((failed++))
        fi
    done < <(jq -c '.repos[]' "$CONFIG_FILE")

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "Synced: ${GREEN}$synced${NC} | Skipped: ${YELLOW}$skipped${NC} | Failed: ${RED}$failed${NC}"
}

# Scan workspace and add all git repos
scan_workspace() {
    local scan_path="${1:-$(get_base_path)}"
    
    echo -e "${BLUE}Scanning for git repositories in: $scan_path${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    local added=0
    
    # Find all .git directories (max depth 2 for performance)
    while IFS= read -r git_dir; do
        local repo_dir
        repo_dir=$(dirname "$git_dir")
        echo -e "Found: $repo_dir"
        add_repo "$repo_dir"
        ((added++))
    done < <(find "$scan_path" -maxdepth 2 -type d -name ".git" 2>/dev/null)

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "Added ${GREEN}$added${NC} repositories"
}

# Set base path for an OS
set_base_path() {
    local os="$1"
    local path="$2"

    if [[ -z "$os" || -z "$path" ]]; then
        echo -e "${RED}Error: Please provide OS and path${NC}"
        echo "Usage: repo-manager.sh set-path <linux|darwin|windows> <path>"
        exit 1
    fi

    if [[ ! "$os" =~ ^(linux|darwin|windows)$ ]]; then
        echo -e "${RED}Error: OS must be linux, darwin, or windows${NC}"
        exit 1
    fi

    local tmp_file
    tmp_file=$(mktemp)
    jq --arg os "$os" --arg path "$path" '.defaultBasePaths[$os] = $path' "$CONFIG_FILE" > "$tmp_file" && mv "$tmp_file" "$CONFIG_FILE"

    echo -e "${GREEN}Set $os base path to: $path${NC}"
}

# Show status of repos on current machine
status() {
    local base_path
    base_path=$(get_base_path)
    
    echo -e "${BLUE}Repository Status (base: $base_path)${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    local present=0
    local missing=0

    while IFS= read -r repo; do
        local name
        name=$(echo "$repo" | jq -r '.name')
        local target_path="$base_path/$name"

        if [[ -d "$target_path" ]]; then
            echo -e "${GREEN}✓${NC} $name"
            ((present++))
        else
            echo -e "${RED}✗${NC} $name ${YELLOW}(missing)${NC}"
            ((missing++))
        fi
    done < <(jq -c '.repos[]' "$CONFIG_FILE")

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "Present: ${GREEN}$present${NC} | Missing: ${RED}$missing${NC}"
}

# Show help
show_help() {
    echo -e "${BLUE}Repo Manager${NC} - Cross-platform repository synchronization"
    echo ""
    echo "Usage: repo-manager.sh <command> [args]"
    echo ""
    echo "Commands:"
    echo "  add <path>        Add a repository to tracking"
    echo "  remove <name>     Remove a repository from tracking"
    echo "  list              List all tracked repositories"
    echo "  sync              Clone missing repositories to this machine"
    echo "  status            Show which repos exist on this machine"
    echo "  scan [path]       Scan directory and add all git repos found"
    echo "  set-path <os> <path>  Set base path for an OS (linux/darwin/windows)"
    echo "  help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  repo-manager.sh add /workspace/example.es"
    echo "  repo-manager.sh scan /workspace"
    echo "  repo-manager.sh sync"
    echo "  repo-manager.sh set-path windows 'D:\\repos'"
}

# Main
init_config

case "${1:-help}" in
    add)      add_repo "$2" ;;
    remove)   remove_repo "$2" ;;
    list)     list_repos ;;
    sync)     sync_repos ;;
    status)   status ;;
    scan)     scan_workspace "$2" ;;
    set-path) set_base_path "$2" "$3" ;;
    help|*)   show_help ;;
esac
