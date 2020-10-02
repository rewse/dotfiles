uname=`uname`

if [ $uname = "Darwin" ]; then
  alias ls="ls -FG"
  alias ll="ls -lFG"
  alias la="ls -aFG"
  alias lal="ls -alFG"
elif [ $uname = "Linux" ]; then
  alias ls="ls -F --color=always"
  alias ll="ls -lF --color=always"
  alias la="ls -aF --color=always"
  alias lal="ls -alF --color=always"
fi

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
alias tmux="tmux -2"
alias tmuxa="tmux attach"
