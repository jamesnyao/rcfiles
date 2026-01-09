#!/bin/bash
# Dev CLI - Development workflow tool
# Usage: dev <subcommand> [args]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_help() {
    echo "Dev CLI - Development workflow tool"
    echo ""
    echo "Usage: dev <subcommand> [args]"
    echo ""
    echo "Subcommands:"
    echo "  repo <command>    Manage tracked repositories"
    echo "  help              Show this help message"
    echo ""
    echo "Repo commands:"
    echo "  dev repo add <path>        Add a repository to tracking"
    echo "  dev repo remove <name>     Remove a repository from tracking"
    echo "  dev repo list              List all tracked repositories"
    echo "  dev repo sync              Clone missing repositories"
    echo "  dev repo status            Show which repos exist locally"
    echo "  dev repo scan [path]       Scan and add all git repos"
    echo "  dev repo set-path <os> <path>  Set base path for an OS"
}

case "${1:-help}" in
    repo)
        shift
        "$SCRIPT_DIR/repo-manager.sh" "$@"
        ;;
    help|--help|-h|*)
        show_help
        ;;
esac
