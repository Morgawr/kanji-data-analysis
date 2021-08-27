#!/bin/bash

set -e

if [ $# -eq 0 ] ; then
  echo "Please specify output directory"
  exit 1
fi

OUT="$1"

cp -v web/kunmap.js "$OUT/kun/"
cp -v web/kunmap.html "$OUT/kun/index.html"
