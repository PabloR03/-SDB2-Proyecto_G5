# Restaurar Base de Datos con Docker

## Pasos

1. **Entrar a la carpeta del proyecto**

   ```bash
   cd RestaurarBase
   ```

2. **Dar permisos al script de restauración**

   ```bash
   chmod +x restore.sh
   ```

3. **Levantar el contenedor y restaurar la base (solo la primera vez)**

   ```bash
   docker compose up -d
   ```

   Esto creará el contenedor `imdb_postgres` y restaurará automáticamente la base `imdb_database` desde el archivo `backup.dump` que ya viene en la imagen.

4. **Verificar que la base está restaurada**
   Conectar al contenedor:

   ```bash
   docker exec -it imdb_postgres psql -U postgres -d imdb_database
   ```

   Y dentro de `psql`:

   ```sql
   \dt
   ```
