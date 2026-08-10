#!/bin/sh
set -e

cd /app/uis/website && npm run dev -- -p 3000 &
cd /app/uis/backoffice && npm run dev -- -p 3001 &

wait
