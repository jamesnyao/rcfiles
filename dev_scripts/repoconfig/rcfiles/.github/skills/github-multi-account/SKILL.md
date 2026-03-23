# GitHub Multi-Account SSH Configuration

This workspace uses multiple GitHub accounts with SSH host aliases for authentication.

## Accounts

| Host Alias | GitHub User | Purpose | SSH Key |
|------------|-------------|---------|---------|
| `github.com-personal` | `jamesnyao` | Personal repos (rcfiles) | `~/.ssh/github_edge` |
| `github.com-edge` | `jamyao_microsoft` | Edge org repos (edge-agents) | `~/.ssh/github_personal` |

## SSH Config (`~/.ssh/config`)

```
# GitHub - Personal (jamesnyao)
Host github.com-personal
  HostName github.com
  User git
  IdentityFile ~/.ssh/github_edge
  IdentitiesOnly yes

# GitHub - Edge/Work (edge-microsoft org)
Host github.com-edge
  HostName github.com
  User git
  IdentityFile ~/.ssh/github_personal
  IdentitiesOnly yes
```

## Remote URL Patterns

| Repo | Remote URL |
|------|------------|
| `rcfiles` (dev_scripts) | `git@github.com-personal:jamesnyao/rcfiles.git` |
| `edge-agents` | `git@github.com-edge:edge-microsoft/edge-agents.git` |

## dev.py Auto-Normalization

The `dev repo add` command automatically converts GitHub URLs to the correct SSH format using the `GITHUB_SSH_HOSTS` mapping in `dev.py`:

```python
GITHUB_SSH_HOSTS = {
    'jamesnyao': 'github.com-personal',
    'edge-microsoft': 'github.com-edge',
}
```

This ensures new GitHub repos are tracked with the correct SSH host alias.

## Testing Authentication

```bash
ssh -T git@github.com-personal  # Should show: Hi jamesnyao!
ssh -T git@github.com-edge      # Should show: Hi jamyao_microsoft!
```

## Troubleshooting

If authentication fails:
1. Verify SSH keys are added to the correct GitHub accounts
2. Check `~/.ssh/config` has correct `IdentityFile` paths
3. Ensure `IdentitiesOnly yes` is set to prevent SSH agent from offering wrong keys
