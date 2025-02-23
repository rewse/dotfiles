# Amazon Q pre block. Keep at the top of this file.
[[ -f "${HOME}/Library/Application Support/amazon-q/shell/zshrc.pre.zsh" ]] && builtin source "${HOME}/Library/Application Support/amazon-q/shell/zshrc.pre.zsh"

EDITOR=vim
PAGER=less
FTP_PASSIVE=1
PS1='[%n@%m %1~]%# '
PS2='> '
LANG='en_US.UTF-8'
LC_ALL=$LANG
LESS='-R'
export EDITOR PAGER FTP_PASSIVE PS1 PS2 LESS LANG LC_ALL

# require source-highlight
if [ -x /usr/bin/src-hilite-lesspipe.sh ]; then
  export LESSOPEN='| /usr/bin/src-hilite-lesspipe.sh %s'
fi

alias ls="ls -F --color=always"
alias ll="ls -lF --color=always"
alias la="ls -aF --color=always"
alias lal="ls -alF --color=always"
alias rm="rm -i"
alias mv="mv -i"
alias cp="cp -i"
alias ..="cd .."
alias ...="cd ../.."
alias df="df -h"
alias du="du -h"
alias less="less -r"
alias vi="vim"
alias view="vim -R"

[[ -f "$(brew --prefix)/opt/zsh-vi-mode/share/zsh-vi-mode/zsh-vi-mode.plugin.zsh" ]] && builtin source "$(brew --prefix)/opt/zsh-vi-mode/share/zsh-vi-mode/zsh-vi-mode.plugin.zsh"

bindkey -M vicmd 'H' beginning-of-line
bindkey -M vicmd 'L' end-of-line

# Amazon Q post block. Keep at the bottom of this file.
[[ -f "${HOME}/Library/Application Support/amazon-q/shell/zshrc.post.zsh" ]] && builtin source "${HOME}/Library/Application Support/amazon-q/shell/zshrc.post.zsh"
