PROMPT="%F{2}%n-dev@$ZSH_THEME_PLATFORM%f %F{14}%~%f"
PROMPT+=' $(git_prompt_info)'
PROMPT+='%(?:%{$reset_color%}:%{$fg[red]%})$ %{$reset_color%}'

ZSH_THEME_GIT_PROMPT_PREFIX="%{$fg[yellow]%}("
ZSH_THEME_GIT_PROMPT_SUFFIX="%{$reset_color%} "
ZSH_THEME_GIT_PROMPT_DIRTY="%{$fg[yellow]%}*)"
ZSH_THEME_GIT_PROMPT_CLEAN="%{$fg[yellow]%})"
