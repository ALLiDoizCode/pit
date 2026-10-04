#!/bin/sh
# post.sh raw.png out.png [bloom1 sigma] [bloom2 sigma] : light paint filter, bloom on the bright centre, small warm grade
magick "$1" -kuwahara ${5:-1.6} \( +clone -level 72%,100% -blur 0x${3:-14} -evaluate multiply 0.8 \) -compose screen -composite \
  \( +clone -level 85%,100% -blur 0x${4:-40} -evaluate multiply 0.45 \) -compose screen -composite \
  -modulate 100,100,100 "$2"
