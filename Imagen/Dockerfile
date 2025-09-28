FROM postgres:16

# Copiar el backup y script de restauración
COPY backup.dump /backup.dump
COPY restore.sh /docker-entrypoint-initdb.d/restore.sh

# Exponer el puerto estándar de PostgreSQL
EXPOSE 5432