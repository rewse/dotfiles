EDITOR=vim
PAGER=less
FTP_PASSIVE=1
PS1='[\u@\h \W]\$ '
PS2='> '
LANG='en_US.UTF-8'
LC_ALL=$LANG
LESS='-R'
export EDITOR PAGER FTP_PASSIVE PS1 PS2 LANG LC_ALL LESS

# require source-highlight
if [ -x /usr/bin/src-hilite-lesspipe.sh ]; then
  export LESSOPEN='| /usr/bin/src-hilite-lesspipe.sh %s'
fi
