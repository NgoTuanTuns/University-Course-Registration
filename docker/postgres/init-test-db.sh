#!/bin/sh
set -eu

createdb \
  --username "$POSTGRES_USER" \
  --owner "$POSTGRES_USER" \
  "$TEST_POSTGRES_DB"