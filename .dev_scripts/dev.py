#!/usr/bin/env python3
"""
Dev CLI - Cross-platform development workflow tool
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Colors (ANSI escape codes, disabled on Windows cmd)
class Colors:
    if sys.platform == 'win32' and 'WT_SESSION' not in os.environ:
        RED = YELLOW = GREEN = BLUE = CYAN = NC = ''
    else:
        RED = '\033[0;31m'
        YELLOW = '\033[1;33m'
        GREEN = '\033[0;32m'
        BLUE = '\033[0;34m'
        CYAN = '\033[0;36m'
        NC = '\033[0m'

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_DIR = SCRIPT_DIR / 'repoconfig'
CONFIG_FILE = CONFIG_DIR / 'repos.json'

def get_os_type():
    system = platform.system().lower()
    if system == 'darwin':
        return 'darwin'
    elif system == 'windows':
        return 'windows'
    return 'linux'

def load_config():
    if not CONFIG_FILE.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config = {
            'version': 1,
            'description': 'Tracked repositories for cross-machine sync',
            'defaultBasePaths': {
                'linux': '/workspace',
                'darwin': '/workspace',
                'windows': 'C:\\dev'
            },
            'repos': []
        }
        save_config(config)
        return config
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def get_base_path(config):
    return config['defaultBasePaths'].get(get_os_type(), '/workspace')

def run_git(repo_path, *args):
    """Run git command and return output"""
    try:
        result = subprocess.run(
            ['git', '-C', str(repo_path)] + list(args),
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception:
        return False, ''

def get_remote_url(repo_path):
    success, url = run_git(repo_path, 'remote', 'get-url', 'origin')
    return url if success else ''

def get_current_branch(repo_path):
    success, branch = run_git(repo_path, 'rev-parse', '--abbrev-ref', 'HEAD')
    return branch if success else None

def get_default_branch(repo_path):
    # Try to get from origin/HEAD
    success, ref = run_git(repo_path, 'symbolic-ref', 'refs/remotes/origin/HEAD')
    if success and ref:
        return ref.replace('refs/remotes/origin/', '')

    # Fallback to common defaults
    for branch in ['main', 'master']:
        success, _ = run_git(repo_path, 'show-ref', '--verify', '--quiet', f'refs/remotes/origin/{branch}')
        if success:
            return branch
    return None

def get_branch_age_days(repo_path):
    """Get age of last commit on current branch in days"""
    success, timestamp = run_git(repo_path, 'log', '-1', '--format=%ct')
    if not success or not timestamp:
        return 0
    try:
        commit_time = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
        age = datetime.now(timezone.utc) - commit_time
        return age.days
    except Exception:
        return 0

def check_stale_branch(repo_path, name):
    """Check if branch is stale and offer to switch to default"""
    current = get_current_branch(repo_path)
    if not current or current == 'HEAD':
        return

    age_days = get_branch_age_days(repo_path)
    if age_days < 14:
        return

    default = get_default_branch(repo_path)
    if not default or current == default:
        return

    print(f"{Colors.YELLOW}[WARN] {name}: branch '{current}' is {age_days} days old{Colors.NC}")
    try:
        response = input(f"  Switch to '{default}'? [Y/n] ").strip().lower() or 'y'
    except EOFError:
        return

    if response == 'y':
        print(f"  {Colors.BLUE}Switching to {default}...{Colors.NC}")
        run_git(repo_path, 'fetch', 'origin')
        run_git(repo_path, 'checkout', '-f', default)
        run_git(repo_path, 'reset', '--hard', f'origin/{default}')
        print(f"  {Colors.GREEN}[OK] Switched to {default}{Colors.NC}")

def compute_repo_name(repo_path, base_path=None):
    """
    Compute a repo name from path, supporting nested structures like edge/src, cr/depot_tools.
    If the repo is under a known enlistment structure (contains .gclient), use parent/name format.
    """
    repo_path = Path(repo_path).resolve()
    
    # Check if parent directory looks like a gclient enlistment (has .gclient file)
    parent = repo_path.parent
    if (parent / '.gclient').exists():
        # This is a nested repo like edge/src or cr/depot_tools
        return f"{parent.name}/{repo_path.name}"
    
    # Check if this is a top-level repo directly in base_path
    if base_path:
        base_path = Path(base_path).resolve()
        try:
            rel_path = repo_path.relative_to(base_path)
            parts = rel_path.parts
            if len(parts) >= 2:
                # Check if the intermediate dir is an enlistment
                intermediate = base_path / parts[0]
                if (intermediate / '.gclient').exists():
                    return '/'.join(parts[:2])
        except ValueError:
            pass
    
    return repo_path.name

# ============ REPO COMMANDS ============

def cmd_repo_add(args):
    """Add a repository to tracking"""
    repo_path = Path(args.path).resolve()

    if not repo_path.exists():
        print(f"{Colors.RED}Error: Directory does not exist: {repo_path}{Colors.NC}")
        return 1

    git_dir = repo_path / '.git'
    if not git_dir.exists():
        print(f"{Colors.RED}Error: Not a git repository: {repo_path}{Colors.NC}")
        return 1

    remote_url = get_remote_url(repo_path)
    if not remote_url:
        print(f"{Colors.YELLOW}Warning: No 'origin' remote found{Colors.NC}")

    config = load_config()
    base_path = get_base_path(config)
    repo_name = compute_repo_name(repo_path, base_path)

    # Remove existing entry if present
    config['repos'] = [r for r in config['repos'] if r['name'] != repo_name]

    config['repos'].append({
        'name': repo_name,
        'remoteUrl': remote_url,
        'addedFrom': str(repo_path),
        'addedAt': datetime.now(timezone.utc).isoformat()
    })

    save_config(config)
    print(f"{Colors.GREEN}Added repository: {repo_name}{Colors.NC}")
    print(f"  Remote: {Colors.CYAN}{remote_url}{Colors.NC}")
    print(f"  Path: {repo_path}")
    return 0

def cmd_repo_remove(args):
    """Remove a repository from tracking"""
    config = load_config()
    original_count = len(config['repos'])
    config['repos'] = [r for r in config['repos'] if r['name'] != args.name]

    if len(config['repos']) == original_count:
        print(f"{Colors.RED}Repository '{args.name}' is not tracked{Colors.NC}")
        return 1

    save_config(config)
    print(f"{Colors.GREEN}Removed repository: {args.name}{Colors.NC}")
    return 0

def cmd_repo_list(args):
    """List all tracked repositories"""
    config = load_config()
    print(f"{Colors.BLUE}Tracked Repositories:{Colors.NC}")
    print("-" * 60)

    if not config['repos']:
        print(f"{Colors.YELLOW}No repositories tracked yet.{Colors.NC}")
        print("Use 'dev repo add <path>' to add a repository.")
        return 0

    for repo in sorted(config['repos'], key=lambda r: r['name']):
        print(f"  {repo['name']}")
        print(f"    Remote: {repo.get('remoteUrl', 'N/A')}")
        print(f"    Added: {repo.get('addedAt', 'Unknown')}")
        print()

    print("-" * 60)
    print(f"Total: {Colors.GREEN}{len(config['repos'])}{Colors.NC} repositories")
    return 0

def sync_rcfiles():
    """Sync rcfiles (dev_scripts config) - pull, auto-commit, and push"""
    print(f"{Colors.BLUE}Syncing rcfiles (dev_scripts)...{Colors.NC}")
    
    # Check for local changes first
    _, status = run_git(SCRIPT_DIR, 'status', '--porcelain')
    has_local_changes = bool(status.strip())
    
    if has_local_changes:
        # Auto-commit local changes
        run_git(SCRIPT_DIR, 'add', '-A')
        import socket
        hostname = socket.gethostname()
        run_git(SCRIPT_DIR, 'commit', '-m', f'Auto-sync from {hostname}')
        print(f"{Colors.GREEN}[OK]{Colors.NC} Committed local changes")
    
    # Pull with rebase to integrate remote changes
    success, output = run_git(SCRIPT_DIR, 'pull', '--rebase', '--autostash')
    if not success:
        print(f"{Colors.RED}[X]{Colors.NC} Failed to pull rcfiles: {output}")
        return
    
    # Check if we have commits to push
    _, status = run_git(SCRIPT_DIR, 'status', '--porcelain', '-b')
    if 'ahead' in status:
        success, output = run_git(SCRIPT_DIR, 'push')
        if success:
            print(f"{Colors.GREEN}[OK]{Colors.NC} rcfiles synced (pushed changes)")
        else:
            print(f"{Colors.RED}[X]{Colors.NC} Failed to push rcfiles: {output}")
    else:
        print(f"{Colors.GREEN}[OK]{Colors.NC} rcfiles synced")


def cmd_repo_sync(args):
    """Clone missing repositories and check for stale branches"""
    config = load_config()
    base_path = Path(get_base_path(config))
    
    # First, merge copilot instructions (before syncing rcfiles so changes get pushed)
    merge_copilot_instructions_to_repoconfig(base_path)
    
    # Now sync rcfiles (pull, commit local changes including copilot, push)
    sync_rcfiles()
    print()

    print(f"{Colors.BLUE}Syncing repositories to: {base_path}{Colors.NC}")
    print("-" * 60)

    if not config['repos']:
        print(f"{Colors.YELLOW}No repositories to sync.{Colors.NC}")
        return 0

    base_path.mkdir(parents=True, exist_ok=True)

    synced = skipped = failed = 0

    for repo in sorted(config['repos'], key=lambda r: r['name']):
        name = repo['name']
        url = repo.get('remoteUrl', '')
        # Handle nested paths like edge/src
        target_path = base_path / name.replace('/', os.sep)

        if target_path.exists():
            print(f"{Colors.GREEN}[OK]{Colors.NC} {name}")
            check_stale_branch(target_path, name)
            skipped += 1
            continue

        if not url:
            print(f"{Colors.RED}[X] Cannot clone {name} (no remote URL){Colors.NC}")
            failed += 1
            continue

        # Create parent directory if needed (for nested repos)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"{Colors.BLUE}[DOWN] Cloning {name}...{Colors.NC}")
        result = subprocess.run(['git', 'clone', url, str(target_path)])
        if result.returncode == 0:
            print(f"{Colors.GREEN}[OK] Cloned {name}{Colors.NC}")
            synced += 1
        else:
            print(f"{Colors.RED}[X] Failed to clone {name}{Colors.NC}")
            failed += 1

    print("-" * 60)
    print(f"Synced: {Colors.GREEN}{synced}{Colors.NC} | Skipped: {Colors.YELLOW}{skipped}{Colors.NC} | Failed: {Colors.RED}{failed}{Colors.NC}")
    # Apply copilot instructions to workspace (repoconfig was already updated and pushed)
    apply_copilot_instructions_to_workspace(base_path)

    return 0


def merge_copilot_instructions_to_repoconfig(base_path):
    """Merge workspace copilot instructions into repoconfig (before rcfiles push).
    
    This captures any workspace changes into repoconfig so they get pushed.
    """
    copilot_src = CONFIG_DIR / 'copilot-instructions.md'
    copilot_dest = base_path / '.github' / 'copilot-instructions.md'
    
    if not copilot_dest.exists():
        return  # No workspace file to merge
    
    src_content = copilot_src.read_text(encoding='utf-8') if copilot_src.exists() else ''
    dest_content = copilot_dest.read_text(encoding='utf-8')
    
    # Normalize for comparison
    src_normalized = src_content.replace('\r\n', '\n')
    dest_normalized = dest_content.replace('\r\n', '\n')
    
    if src_normalized == dest_normalized:
        return  # Already in sync
    
    # If repoconfig is empty, just copy from workspace
    if not src_content.strip():
        copilot_src.write_text(dest_content, encoding='utf-8')
        return
    
    # If workspace is empty, nothing to merge
    if not dest_content.strip():
        return
    
    # Merge workspace changes into repoconfig
    merged_content, has_conflicts = try_git_merge(src_content, dest_content)
    
    if merged_content is None:
        # Fallback to section merge
        merged_content, has_conflicts = section_merge(src_content, dest_content)
    
    # Write merged content to repoconfig (will be committed and pushed)
    if merged_content:
        copilot_src.write_text(merged_content, encoding='utf-8')


def apply_copilot_instructions_to_workspace(base_path):
    """Apply repoconfig copilot instructions to workspace (after rcfiles pull).
    
    This propagates the merged/synced instructions to the workspace.
    """
    copilot_src = CONFIG_DIR / 'copilot-instructions.md'
    copilot_dest = base_path / '.github' / 'copilot-instructions.md'
    
    copilot_dest.parent.mkdir(parents=True, exist_ok=True)
    
    src_content = copilot_src.read_text(encoding='utf-8') if copilot_src.exists() else ''
    dest_content = copilot_dest.read_text(encoding='utf-8') if copilot_dest.exists() else ''
    
    # Normalize for comparison
    src_normalized = src_content.replace('\r\n', '\n')
    dest_normalized = dest_content.replace('\r\n', '\n')
    
    if src_normalized == dest_normalized:
        if src_content:
            print(f"{Colors.GREEN}[OK]{Colors.NC} Copilot instructions up to date")
        return
    
    # Check for conflict markers in either file
    has_src_conflicts = '<<<<<<<' in src_content
    has_dest_conflicts = '<<<<<<<' in dest_content
    
    if has_src_conflicts or has_dest_conflicts:
        print(f"{Colors.YELLOW}[CONFLICT]{Colors.NC} Copilot instructions have merge conflicts")
        print("  Conflict markers in .github/copilot-instructions.md")
        print("  Use Copilot to resolve, then run 'dev repo sync' again")
        return
    
    # Apply repoconfig to workspace
    if src_content.strip():
        copilot_dest.write_text(src_content, encoding='utf-8')
        print(f"{Colors.GREEN}[OK]{Colors.NC} Copilot instructions synced")
    elif dest_content.strip():
        # Workspace has content but repoconfig doesn't - preserve workspace
        copilot_src.write_text(dest_content, encoding='utf-8')
        print(f"{Colors.GREEN}[OK]{Colors.NC} Copilot instructions synced from workspace")


def sync_copilot_instructions(base_path):
    """Merge copilot instructions using git's 3-way merge for automatic conflict resolution.
    
    Auto-merges when possible. Leaves conflict markers for Copilot to resolve when needed.
    Never prompts for user input.
    """
    import difflib
    
    copilot_src = CONFIG_DIR / 'copilot-instructions.md'
    copilot_dest = base_path / '.github' / 'copilot-instructions.md'

    copilot_dest.parent.mkdir(parents=True, exist_ok=True)
    
    src_content = copilot_src.read_text(encoding='utf-8') if copilot_src.exists() else ''
    dest_content = copilot_dest.read_text(encoding='utf-8') if copilot_dest.exists() else ''

    # Normalize line endings for comparison
    src_normalized = src_content.replace('\r\n', '\n')
    dest_normalized = dest_content.replace('\r\n', '\n')

    if src_normalized == dest_normalized:
        if src_content:
            print(f"{Colors.GREEN}[OK]{Colors.NC} Copilot instructions up to date")
        return

    # If one is empty, use the other
    if not src_content.strip():
        copilot_src.write_text(dest_content, encoding='utf-8')
        print(f"{Colors.GREEN}[OK]{Colors.NC} Copilot instructions synced from workspace")
        return
    
    if not dest_content.strip():
        copilot_dest.write_text(src_content, encoding='utf-8')
        print(f"{Colors.GREEN}[OK]{Colors.NC} Copilot instructions synced to workspace")
        return

    # Try git merge-file for automatic 3-way merge
    merged_content, has_conflicts = try_git_merge(src_content, dest_content)
    
    if merged_content is not None and not has_conflicts:
        # Auto-merge succeeded with no conflicts
        copilot_src.write_text(merged_content, encoding='utf-8')
        copilot_dest.write_text(merged_content, encoding='utf-8')
        print(f"{Colors.GREEN}[OK]{Colors.NC} Copilot instructions auto-merged")
        return
    
    if merged_content is not None and has_conflicts:
        # Merge has conflicts - write to workspace with markers for Copilot to resolve
        copilot_dest.write_text(merged_content, encoding='utf-8')
        print(f"{Colors.YELLOW}[CONFLICT]{Colors.NC} Copilot instructions have merge conflicts")
        print("  Conflict markers written to .github/copilot-instructions.md")
        print("  Use Copilot to resolve, then run 'dev repo sync' again")
        return

    # Fallback: git merge not available - do section-based merge
    merged_content, has_conflicts = section_merge(src_content, dest_content)
    
    if not has_conflicts:
        copilot_src.write_text(merged_content, encoding='utf-8')
        copilot_dest.write_text(merged_content, encoding='utf-8')
        print(f"{Colors.GREEN}[OK]{Colors.NC} Copilot instructions auto-merged (section-based)")
    else:
        copilot_dest.write_text(merged_content, encoding='utf-8')
        print(f"{Colors.YELLOW}[CONFLICT]{Colors.NC} Copilot instructions have merge conflicts")
        print("  Conflict markers written to .github/copilot-instructions.md")
        print("  Use Copilot to resolve, then run 'dev repo sync' again")


def section_merge(src_content, dest_content):
    """Merge markdown files by section (## headers).
    
    Merges non-conflicting sections automatically.
    Returns (merged_content, has_conflicts).
    """
    import re
    
    def parse_sections(content):
        """Parse markdown into sections by ## headers."""
        sections = {}
        current_header = '__preamble__'
        current_lines = []
        
        for line in content.splitlines(keepends=True):
            if line.startswith('## '):
                if current_lines:
                    sections[current_header] = ''.join(current_lines)
                current_header = line.strip()
                current_lines = [line]
            else:
                current_lines.append(line)
        
        if current_lines:
            sections[current_header] = ''.join(current_lines)
        
        return sections
    
    src_sections = parse_sections(src_content)
    dest_sections = parse_sections(dest_content)
    
    all_headers = []
    seen = set()
    # Preserve order from both, src first
    for h in list(src_sections.keys()) + list(dest_sections.keys()):
        if h not in seen:
            all_headers.append(h)
            seen.add(h)
    
    merged_parts = []
    has_conflicts = False
    
    for header in all_headers:
        src_sec = src_sections.get(header, '')
        dest_sec = dest_sections.get(header, '')
        
        # Normalize for comparison (strip trailing whitespace)
        src_normalized = src_sec.rstrip()
        dest_normalized = dest_sec.rstrip()
        
        if src_normalized == dest_normalized:
            # Identical - use either (prefer dest to keep formatting)
            merged_parts.append(dest_sec if dest_sec else src_sec)
        elif not src_sec.strip():
            # Only in dest (workspace) - keep it
            merged_parts.append(dest_sec)
        elif not dest_sec.strip():
            # Only in src (repoconfig) - add it
            merged_parts.append(src_sec)
        else:
            # Both have content but different - conflict
            has_conflicts = True
            conflict = f"<<<<<<< repoconfig\n{src_sec.rstrip()}\n=======\n{dest_sec.rstrip()}\n>>>>>>> workspace\n\n"
            merged_parts.append(conflict)
    
    return ''.join(merged_parts), has_conflicts


def try_git_merge(src_content, dest_content):
    """Attempt 3-way merge using git merge-file.
    
    Uses the common ancestor (LCS) as base for merge.
    Returns (merged_content, has_conflicts) or (None, False) if git unavailable.
    """
    import subprocess
    import tempfile
    import difflib
    
    # Find common base using longest common subsequence of lines
    src_lines = src_content.splitlines(keepends=True)
    dest_lines = dest_content.splitlines(keepends=True)
    
    matcher = difflib.SequenceMatcher(None, src_lines, dest_lines)
    base_lines = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            base_lines.extend(src_lines[i1:i2])
    base_content = ''.join(base_lines)
    
    # If no common content, can't do 3-way merge meaningfully
    if not base_content.strip():
        return None, False
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_file = Path(tmpdir) / 'base.md'
            src_file = Path(tmpdir) / 'repoconfig.md'
            dest_file = Path(tmpdir) / 'workspace.md'
            
            base_file.write_text(base_content, encoding='utf-8')
            src_file.write_text(src_content, encoding='utf-8')
            dest_file.write_text(dest_content, encoding='utf-8')
            
            # git merge-file modifies dest_file in place
            # Returns 0 on clean merge, >0 on conflicts, <0 on error
            result = subprocess.run(
                ['git', 'merge-file', '-p', 
                 '--marker-size=7',
                 '-L', 'repoconfig', '-L', 'base', '-L', 'workspace',
                 str(src_file), str(base_file), str(dest_file)],
                capture_output=True,
                text=True
            )
            
            if result.returncode < 0:
                return None, False  # Error, fall back to manual
            
            merged = result.stdout
            has_conflicts = result.returncode > 0 or '<<<<<<<' in merged
            
            return merged, has_conflicts
            
    except FileNotFoundError:
        # git not available
        return None, False
    except Exception:
        return None, False

def cmd_repo_status(args):
    """Show which repos exist on this machine"""
    config = load_config()
    base_path = Path(get_base_path(config))

    print(f"{Colors.BLUE}Repository Status (base: {base_path}){Colors.NC}")
    print("-" * 60)

    present = missing = 0
    for repo in sorted(config['repos'], key=lambda r: r['name']):
        # Handle nested paths like edge/src
        target_path = base_path / repo['name'].replace('/', os.sep)
        if target_path.exists():
            print(f"{Colors.GREEN}[OK]{Colors.NC} {repo['name']}")
            present += 1
        else:
            print(f"{Colors.RED}[X]{Colors.NC} {repo['name']} {Colors.YELLOW}(missing){Colors.NC}")
            missing += 1

    print("-" * 60)
    print(f"Present: {Colors.GREEN}{present}{Colors.NC} | Missing: {Colors.RED}{missing}{Colors.NC}")
    return 0

def cmd_repo_scan(args):
    """Scan directory and add all git repos, including nested ones in enlistments"""
    config = load_config()
    scan_path = Path(args.path) if args.path else Path(get_base_path(config))

    print(f"{Colors.BLUE}Scanning for git repositories in: {scan_path}{Colors.NC}")
    print("-" * 60)

    added = 0
    
    def add_repo(path):
        nonlocal added
        print(f"Found: {path}")
        class AddArgs:
            pass
        add_args = AddArgs()
        add_args.path = str(path)
        cmd_repo_add(add_args)
        added += 1
    
    for entry in scan_path.iterdir():
        if not entry.is_dir():
            continue
            
        if (entry / '.git').exists():
            # Top-level git repo
            add_repo(entry)
        elif (entry / '.gclient').exists():
            # This is a gclient enlistment, only track src and depot_tools
            print(f"{Colors.CYAN}Found enlistment: {entry.name}{Colors.NC}")
            for subname in ['src', 'depot_tools']:
                subentry = entry / subname
                if subentry.is_dir() and (subentry / '.git').exists():
                    add_repo(subentry)

    print("-" * 60)
    print(f"Added {Colors.GREEN}{added}{Colors.NC} repositories")
    return 0

def cmd_repo_set_path(args):
    """Set base path for an OS"""
    if args.os not in ('linux', 'darwin', 'windows'):
        print(f"{Colors.RED}Error: OS must be linux, darwin, or windows{Colors.NC}")
        return 1

    config = load_config()
    config['defaultBasePaths'][args.os] = args.path
    save_config(config)
    print(f"{Colors.GREEN}Set {args.os} base path to: {args.path}{Colors.NC}")
    return 0


# ============ PYTHON COMMANDS ============

def get_python_command():
    """Get the Python command for this platform"""
    if get_os_type() == 'windows':
        return ['py']
    return ['python3']

def get_current_python_version():
    """Get the currently installed Python version"""
    try:
        cmd = get_python_command() + ['--version']
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None

def cmd_python_update(args):
    """Update Python to the latest stable version"""
    os_type = get_os_type()

    print(f'{Colors.BLUE}Checking Python installation...{Colors.NC}')
    current = get_current_python_version()
    if current:
        print(f'  Current: {Colors.CYAN}{current}{Colors.NC}')

    if os_type == 'windows':
        print(f'{Colors.BLUE}Updating Python via winget...{Colors.NC}')
        # Capture output to detect "no upgrade available"
        result = subprocess.run(['winget', 'upgrade', 'Python.Python.3.12'], 
                               capture_output=True, text=True)
        if 'No available upgrade found' in result.stdout or 'No installed package found' in result.stdout:
            if 'No installed package found' in result.stdout:
                print(f'{Colors.YELLOW}Not installed, installing...{Colors.NC}')
                result = subprocess.run(['winget', 'install', 'Python.Python.3.12', 
                                        '--accept-package-agreements', '--accept-source-agreements'])
                if result.returncode == 0:
                    print(f'{Colors.GREEN}Python installed successfully{Colors.NC}')
                    print(f'{Colors.YELLOW}Note: Restart your terminal for changes to take effect{Colors.NC}')
                    return 0
            else:
                print(f'{Colors.GREEN}Python is already up to date{Colors.NC}')
                return 0
        elif result.returncode == 0:
            print(f'{Colors.GREEN}Python updated successfully{Colors.NC}')
            print(f'{Colors.YELLOW}Note: Restart your terminal for changes to take effect{Colors.NC}')
            return 0
        print(f'{Colors.RED}Failed to update Python{Colors.NC}')
        return 1

    elif os_type == 'darwin':
        print(f'{Colors.BLUE}Updating Python via Homebrew...{Colors.NC}')
        result = subprocess.run(['brew', 'upgrade', 'python@3.12'])
        if result.returncode != 0:
            result = subprocess.run(['brew', 'install', 'python@3.12'])
        return 0 if result.returncode == 0 else 1

    else:
        print(f'{Colors.BLUE}Updating Python...{Colors.NC}')
        result = subprocess.run(['which', 'apt'], capture_output=True)
        if result.returncode == 0:
            subprocess.run(['sudo', 'apt', 'update'])
            result = subprocess.run(['sudo', 'apt', 'install', '-y', 'python3.12'])
        else:
            result = subprocess.run(['sudo', 'dnf', 'install', '-y', 'python3.12'])
        return 0 if result.returncode == 0 else 1


def cmd_test(args):
    """Run dev.py unit tests"""
    test_file = SCRIPT_DIR / 'test_dev.py'
    if not test_file.exists():
        print(f"{Colors.RED}Error: test_dev.py not found{Colors.NC}")
        return 1
    
    print(f"{Colors.BLUE}Running tests...{Colors.NC}")
    result = subprocess.run([sys.executable, str(test_file)], cwd=str(SCRIPT_DIR))
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description='Dev CLI - Development workflow tool')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # repo subcommand
    repo_parser = subparsers.add_parser('repo', help='Manage tracked repositories')
    repo_sub = repo_parser.add_subparsers(dest='repo_command')

    add_p = repo_sub.add_parser('add', help='Add a repository to tracking')
    add_p.add_argument('path', help='Path to the repository')

    remove_p = repo_sub.add_parser('remove', help='Remove a repository from tracking')
    remove_p.add_argument('name', help='Name of the repository')

    repo_sub.add_parser('list', help='List all tracked repositories')
    repo_sub.add_parser('sync', help='Clone missing repositories')
    repo_sub.add_parser('status', help='Show repo status on this machine')

    scan_p = repo_sub.add_parser('scan', help='Scan and add all git repos')
    scan_p.add_argument('path', nargs='?', help='Path to scan')

    setpath_p = repo_sub.add_parser('set-path', help='Set base path for an OS')
    setpath_p.add_argument('os', help='OS (linux/darwin/windows)')
    setpath_p.add_argument('path', help='Base path')


    # python subcommand
    pyenv_parser = subparsers.add_parser('python', help='Python environment management')
    pyenv_sub = pyenv_parser.add_subparsers(dest='python_command')
    pyenv_sub.add_parser('update', help='Update Python to latest stable version')

    # Test command
    subparsers.add_parser('test', help='Run dev.py unit tests')

    args = parser.parse_args()

    if args.command == 'test':
        return cmd_test(args)
    elif args.command == 'python':
        if args.python_command == 'update':
            return cmd_python_update(args)
        else:
            pyenv_parser.print_help()
    elif args.command == 'repo':
        cmd_map = {
            'add': cmd_repo_add,
            'remove': cmd_repo_remove,
            'list': cmd_repo_list,
            'sync': cmd_repo_sync,
            'status': cmd_repo_status,
            'scan': cmd_repo_scan,
            'set-path': cmd_repo_set_path,
        }
        if args.repo_command in cmd_map:
            return cmd_map[args.repo_command](args)
        else:
            repo_parser.print_help()
    else:
        parser.print_help()

    return 0

if __name__ == '__main__':
    sys.exit(main())

