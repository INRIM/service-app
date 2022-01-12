#!/bin/bash
echo "install jtc"
SO="$(uname)"
if [ $SO == "Darwin" ]; then
  wget https://github.com/ldn-softdev/jtc/releases/download/LatestBuild/jtc-macos-64.latest -O "${PWD}/jtc"
elif [ $SO == "Linux" ]; then
  wget https://github.com/ldn-softdev/jtc/releases/download/LatestBuild/jtc-linux-64.latest -O "${PWD}/jtc"
fi
chmod a+x "${PWD}/jtc"