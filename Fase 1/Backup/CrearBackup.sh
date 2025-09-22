#!/bin/bash

# Nombre del contenedor
CONTAINER="imdb_postgres"

# Usuario y base de datos
USER="postgres"
DB="imdb_database"

# Fecha para el nombre del archivo
DATE=$(date +"%Y-%m-%d_%H-%M-%S")

# Nombres de archivos con fecha
CONTAINER_BACKUP="/backup_${DATE}.dump"
HOST_BACKUP_FILE="backup_${DATE}.dump"

echo "Creando backup dentro del contenedor..."
docker exec $CONTAINER pg_dump -U $USER -d $DB -F c -f $CONTAINER_BACKUP

echo "Copiando backup al directorio actual..."
docker cp $CONTAINER:$CONTAINER_BACKUP "./$HOST_BACKUP_FILE"

echo "Backup completado: $HOST_BACKUP_FILE"