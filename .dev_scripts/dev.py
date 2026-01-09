#!/usr/bin/env python3
"""
Dev CLI - Cross-platform development workflow tool
"""

import argparse
import json
import os
import platform
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
    
    print(f"{Colors.YELLOW}⚠ {name}: branch '{current}' is {age_days} days old{Colors.NC}")
    try:
        response = input(f"  Switch to '{default}'? [y/N] ").strip().lower()
    except EOFError:
        return
    
    if response == 'y':
        print(f"  {Colors.BLUE}Switching to {default}...{Colors.NC}")
        run_git(repo_path, 'fetch', 'origin')
        run_git(repo_path, 'checkout', '-f', default)
        run_git(repo_path, 'reset', '--hard', f'origin/{default}')
        print(f"  {Colors.GREEN}✓ Switched to {default}{Colors.NC}")

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
    
    repo_name = repo_path.name
    config = load_config()
    
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
    print("━" * 60)
    
    if not config['repos']:
        print(f"{Colors.YELLOW}No repositories tracked yet.{Colors.NC}")
        print("Use 'dev repo add <path>' to add a repository.")
        return 0
    
    for repo in config['repos']:
        print(f"  {repo['name']}")
        print(f"    Remote: {repo.get('remoteUrl', 'N/A')}")
        print(f"    Added: {repo.get('addedAt', 'Unknown')}")
        print()
    
    print("━" * 60)
    print(f"Total: {Colors.GREEN}{len(config['repos'])}{Colors.NC} repositories")
    return 0

def cmd_repo_sync(args):
    """Clone missing repositories and check for stale branches"""
    config = load_config()
    base_path = Path(get_base_path(config))
    
    print(f"{Colors.BLUE}Syncing repositories to: {base_path}{Colors.NC}")
    print("━" * 60)
    
    if not config['repos']:
        print(f"{Colors.YELLOW}No repositories to sync.{Colors.NC}")
        return 0
    
    base_path.mkdir(parents=True, exist_ok=True)
    
    synced = skipped = failed = 0
    
    for repo in config['repos']:
        name = repo['name']
        url = repo.get('remoteUrl', '')
        target_path = base_path / name
        
        if target_path.exists():
            print(f"{Colors.YELLOW}⏭ Skipping {name} (already exists){Colors.NC}")
            check_stale_branch(target_path, name)
            skipped += 1
            continue
        
        if not url:
            print(f"{Colors.RED}✗ Cannot clone {name} (no remote URL){Colors.NC}")
            failed += 1
            continue
        
        print(f"{Colors.BLUE}⬇ Cloning {name}...{Colors.NC}")
        result = subprocess.run(['git', 'clone', url, str(target_path)])
        if result.returncode == 0:
            print(f"{Colors.GREEN}✓ Cloned {name}{Colors.NC}")
            synced += 1
        else:
            print(f"{Colors.RED}✗ Failed to clone {name}{Colors.NC}")
            failed += 1
    
    print("━" * 60)
    print(f"Synced: {Colors.GREEN}{synced}{Colors.NC} | Skipped: {Colors.YELLOW}{skipped}{Colors.NC} | Failed: {Colors.RED}{failed}{Colors.NC}")
    return 0

def cmd_repo_status(args):
    """Show which repos exist on this machine"""
    config = load_config()
    base_path = Path(get_base_path(config))
    
    print(f"{Colors.BLUE}Repository Status (base: {base_path}){Colors.NC}")
    print("━" * 60)
    
    present = missing = 0
    for repo in config['repos']:
        target_path = base_path / repo['name']
        if target_path.exists():
            print(f"{Colors.GREEN}✓{Colors.NC} {repo['name']}")
            present += 1
        else:
            print(f"{Colors.RED}✗{Colors.NC} {repo['name']} {Colors.YELLOW}(missing){Colors.NC}")
            missing += 1
    
    print("━" * 60)
    print(f"Present: {Colors.GREEN}{present}{Colors.NC} | Missing: {Colors.RED}{missing}{Colors.NC}")
    return 0

def cmd_repo_scan(args):
    """Scan directory and add all git repos"""
    config = load_config()
    scan_path = Path(args.path) if args.path else Path(get_base_path(config))
    
    print(f"{Colors.BLUE}Scanning for git repositories in: {scan_path}{Colors.NC}")
    print("━" * 60)
    
    added = 0
    for entry in scan_path.iterdir():
        if entry.is_dir() and (entry / '.git').exists():
            print(f"Found: {entry}")
            # Simulate args for add
            class AddArgs:
                path = str(entry)
            cmd_repo_add(AddArgs())
            added += 1
    
    print("━" * 60)
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
    
    args = parser.parse_args()
    
    if args.command == 'repo':
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
