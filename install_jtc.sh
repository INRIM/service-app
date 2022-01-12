#!/bin/bash
echo "install jtc"
case $(uname | tr '[:upper:]' '[:lower:]') in
    linux*)
      wget https://github.com/ldn-softdev/jtc/releases/download/LatestBuild/jtc-linux-64.latest -O "${PWD}/jtc"
      ;;
    darwin*)
      wget https://github.com/ldn-softdev/jtc/releases/download/LatestBuild/jtc-macos-64.latest -O "${PWD}/jtc"
      ;;
    msys*)
      export TRAVIS_OS_NAME=windows
      ;;
    *)
      export TRAVIS_OS_NAME=notset
      ;;
  esac
chmod a+x "${PWD}/jtc"