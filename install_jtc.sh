#!/bin/bash
echo "install jtc"
if [ "$OSTYPE"=="darwin"* ]; then
  wget https://github.com/ldn-softdev/jtc/releases/download/LatestBuild/jtc-macos-64.latest -O "${PWD}/jtc"
elif [ "$OSTYPE"=="linux-gnu"* ]; then
  wget https://github.com/ldn-softdev/jtc/releases/download/LatestBuild/jtc-linux-64.latest -O "${PWD}/jtc"
fi
chmod a+x "${PWD}/jtc"