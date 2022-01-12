#!/bin/bash
echo "install jtc"
if [ "$(uname)" == "Darwin" ]; then
  wget https://github.com/ldn-softdev/jtc/releases/download/LatestBuild/jtc-macos-64.latest -O "${PWD}/jtc"
elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
  wget https://github.com/ldn-softdev/jtc/releases/download/LatestBuild/jtc-linux-32.latest -O "${PWD}/jtc"
fi
chmod a+x "${PWD}/jtc"