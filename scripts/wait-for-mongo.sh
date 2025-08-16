#!/usr/bin/env bash
# D:\city_chain_project\scripts\wait-for-mongo.sh
set -eu

printf " waiting for mongo to be healthy"
for i in {1..30}; do
  if docker inspect --format '{{.State.Health.Status}}' ci-mongo 2>/dev/null | grep -q healthy; then
    echo " ✔"
    exit 0
  fi
  printf "."
  sleep 2
done
echo " ✖ timed-out" >&2
exit 1
