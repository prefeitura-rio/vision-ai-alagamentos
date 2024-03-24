#!/usr/bin/env bash
cat snapshots.txt | sort -R | head -n 200 > random_snapshots.txt
