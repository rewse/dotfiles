uname=`uname`

if [ $uname = "Darwin" ]; then
  alias ls="ls -FG"
  alias ll="ls -lFG"
  alias la="ls -aFG"
  alias lal="ls -alFG"
elif [ $uname = "CYGWIN_NT-6.1-WOW64" ]; then
  alias ls="ls -F --color=always"
  alias ll="ls -lF --color=always"
  alias la="ls -aF --color=always"
  alias lal="ls -alF --color=always"
  chcp.com 65001
elif [ $uname = "Linux" ]; then
  alias ls="ls -F --color=always"
  alias ll="ls -lF --color=always"
  alias la="ls -aF --color=always"
  alias lal="ls -alF --color=always"
elif [ $uname = "SunOS" ]; then
  alias ls="ls -F"
  alias ll="ls -lF"
  alias la="ls -aF"
  alias lal="ls -alF"
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
