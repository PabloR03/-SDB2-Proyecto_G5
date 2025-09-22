#!/bin/bash
set -e

echo "Restaurando backup desde /backup.dump..."
pg_restore -U postgres -d imdb_database /backup.dump
echo "Restauración completada."
