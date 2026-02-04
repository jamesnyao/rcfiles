# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:$HOME/.local/bin:/usr/local/bin:$PATH

# Set up uname platform
export platform=$(uname | tr '[:upper:]' '[:lower:]')

# Detect WSL and set display name
if [[ "$platform" == "linux" ]] && grep -qi microsoft /proc/version 2>/dev/null; then
  export ZSH_THEME_PLATFORM="surface-wsl"
else
  export ZSH_THEME_PLATFORM="$platform"
fi

# Path to your Oh My Zsh installation.
export ZSH="$HOME/.oh-my-zsh"

# Set name of the theme to load --- if set to "random", it will
# load a random theme each time Oh My Zsh is loaded, in which case,
# to know which specific one was loaded, run: echo $RANDOM_THEME
# See https://github.com/ohmyzsh/ohmyzsh/wiki/Themes
cp $HOME/jamyao.zsh-theme $ZSH/themes/jamyao.zsh-theme
ZSH_THEME="jamyao"

# Set list of themes to pick from when loading at random
# Setting this variable when ZSH_THEME=random will cause zsh to load
# a theme from this variable instead of looking in $ZSH/themes/
# If set to an empty array, this variable will have no effect.
# ZSH_THEME_RANDOM_CANDIDATES=( "robbyrussell" "agnoster" )

# Uncomment the following line to use case-sensitive completion.
# CASE_SENSITIVE="true"

# Uncomment the following line to use hyphen-insensitive completion.
# Case-sensitive completion must be off. _ and - will be interchangeable.
# HYPHEN_INSENSITIVE="true"

# Uncomment one of the following lines to change the auto-update behavior
# zstyle ':omz:update' mode disabled  # disable automatic updates
# zstyle ':omz:update' mode auto      # update automatically without asking
# zstyle ':omz:update' mode reminder  # just remind me to update when it's time

# Uncomment the following line to change how often to auto-update (in days).
# zstyle ':omz:update' frequency 13

# Uncomment the following line if pasting URLs and other text is messed up.
# DISABLE_MAGIC_FUNCTIONS="true"

# Uncomment the following line to disable colors in ls.
# DISABLE_LS_COLORS="true"

# Uncomment the following line to disable auto-setting terminal title.
DISABLE_AUTO_TITLE="true"

# Uncomment the following line to enable command auto-correction.
# ENABLE_CORRECTION="true"

# Uncomment the following line to display red dots whilst waiting for completion.
# You can also set it to another string to have that shown instead of the default red dots.
# e.g. COMPLETION_WAITING_DOTS="%F{yellow}waiting...%f"
# Caution: this setting can cause issues with multiline prompts in zsh < 5.7.1 (see #5765)
# COMPLETION_WAITING_DOTS="true"

# Uncomment the following line if you want to disable marking untracked files
# under VCS as dirty. This makes repository status check for large repositories
# much, much faster.
# DISABLE_UNTRACKED_FILES_DIRTY="true"

# Uncomment the following line if you want to change the command execution time
# stamp shown in the history command output.
# You can set one of the optional three formats:
# "mm/dd/yyyy"|"dd.mm.yyyy"|"yyyy-mm-dd"
# or set a custom format using the strftime function format specifications,
# see 'man strftime' for details.
# HIST_STAMPS="mm/dd/yyyy"

# Would you like to use another custom folder than $ZSH/custom?
# ZSH_CUSTOM=/path/to/new-custom-folder

# Which plugins would you like to load?
# Standard plugins can be found in $ZSH/plugins/
# Custom plugins may be added to $ZSH_CUSTOM/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
# Add wisely, as too many plugins slow down shell startup.
plugins=(git zsh-autosuggestions)

source $ZSH/oh-my-zsh.sh

# User configuration

# export MANPATH="/usr/local/man:$MANPATH"

# You may need to manually set your language environment
# export LANG=en_US.UTF-8

# Preferred editor for local and remote sessions
# if [[ -n $SSH_CONNECTION ]]; then
#   export EDITOR='vim'
# else
#   export EDITOR='nvim'
# fi

# Compilation flags
# export ARCHFLAGS="-arch $(uname -m)"

# Set personal aliases, overriding those provided by Oh My Zsh libs,
# plugins, and themes. Aliases can be placed here, though Oh My Zsh
# users are encouraged to define aliases within a top-level file in
# the $ZSH_CUSTOM folder, with .zsh extension. Examples:
# - $ZSH_CUSTOM/aliases.zsh
# - $ZSH_CUSTOM/macos.zsh
# For a full list of active aliases, run `alias`.
#
# Example aliases
# alias zshconfig="mate ~/.zshrc"
# alias ohmyzsh="mate ~/.oh-my-zsh"

platform=$(uname | tr '[:upper:]' '[:lower:]')
if [[ "$platform" == "linux" ]]; then
  PATH="/home/jamyao/.local/bin:/usr/local/go/bin:$PATH"

  zoxide --version > /dev/null
  if [ $? -eq 127 ]; then
    curl -sSfL https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | sh
  fi
  eval "$(zoxide init --cmd cd zsh)"

  PATH="/home/jamyao/.fzf/bin/:$PATH"
  which fzf > /dev/null 2>&1
  if [ $? -ne 0 ]; then
    git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
    ~/.fzf/install
  fi
  source <(fzf --zsh)
fi

# Detect WSL vs native Linux and set paths
if [[ "$platform" == "linux" ]] && grep -qi microsoft /proc/version 2>/dev/null; then
  # WSL
  export ENLIST_BASE="/workspace"
  export DEVCONFIG="wsl-surface"
elif [[ "$platform" == "linux" ]]; then
  # Native Linux devbox
  export ENLIST_BASE="/workspace"
  export DEVCONFIG="linux-devbox"
elif [[ "$platform" == "darwin" ]]; then
  export ENLIST_BASE="$HOME"
  export DEVCONFIG="mac-devbox"
fi

export DEV_WORKSPACE="$ENLIST_BASE"

title "jamyao-dev-$platform"

# Edge ENV
OLD_PATH="$PATH"

DEPOT_TOOLS_PATH="$ENLIST_BASE/edge/depot_tools"
DEPOT_TOOLS_PATH2="$ENLIST_BASE/edge2/depot_tools"

PATH1="$DEPOT_TOOLS_PATH:$DEPOT_TOOLS_PATH/scripts:$OLD_PATH"
PATH2="$DEPOT_TOOLS_PATH2:$DEPOT_TOOLS_PATH2/scripts:$OLD_PATH"

PATH="$PATH1"

[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# Dev CLI
source ~/.dev_scripts/aliases.sh

# Start in edge/src
cd $ENLIST_BASE/edge/src 2>/dev/null || cd $ENLIST_BASE

# WSL-specific: Windows tools
if grep -qi microsoft /proc/version 2>/dev/null; then
  alias cop="copilot.exe --allow-all"
  alias code="/mnt/c/Users/jamyao/AppData/Local/Programs/Microsoft\ VS\ Code/bin/code"
fi
