#!/bin/sh
set -eu

# Keep this database name literal: the reset guard only allows this target.
if psql --username "$POSTGRES_USER" --dbname postgres --tuples-only --no-align \
  --command "SELECT 1 FROM pg_database WHERE datname = 'course_reg_loadtest'" \
  | grep -qx 1; then
  echo "Database course_reg_loadtest already exists."
else
  createdb --username "$POSTGRES_USER" --owner "$POSTGRES_USER" course_reg_loadtest
  echo "Created database course_reg_loadtest."
fi
