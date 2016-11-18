EDITOR=vim
PAGER=less
FTP_PASSIVE=1
PS1='[\u@\h \W]\$ '
PS2='> '
LESS='-R'
export EDITOR PAGER FTP_PASSIVE PS1 PS2 LESS

# require source-highlight
if [ -x /usr/bin/src-hilite-lesspipe.sh ]; then
  export LESSOPEN='| /usr/bin/src-hilite-lesspipe.sh %s'
fi
