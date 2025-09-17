#!/usr/bin/env python3
"""
Script para cargar datos IMDB en el sistema maestro-esclavo PostgreSQL
Tabla recomendada: Titulo (tabla principal con datos representativos)
VERSIÓN CORREGIDA - Compatible con estructura de CSVs proporcionada y esquema de BD
CORRIGE EL PROBLEMA DE TRANSACCIONES FALLIDAS
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
import sys
import random
from datetime import datetime

class IMDBDataLoader:
    def __init__(self):
        # Configuración de conexiones
        self.master_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'imdb_database',
            'user': 'postgres',
            'password': 'postgres'
        }
        
        self.slave_config = {
            'host': 'localhost',
            'port': 5433,
            'database': 'imdb_database',
            'user': 'postgres',
            'password': 'postgres'
        }
        
        # Nombres de tablas (se establecerán después de verificar la estructura)
        self.categoria_table_name = None
        self.titulo_table_name = None
        self.schema_name = None  # Esquema donde están las tablas
    
    def connect_to_master(self):
        """Conectar al servidor maestro"""
        try:
            conn = psycopg2.connect(**self.master_config)
            return conn
        except Exception as e:
            print(f"Error conectando al maestro: {e}")
            return None
    
    def connect_to_slave(self):
        """Conectar al servidor esclavo"""
        try:
            conn = psycopg2.connect(**self.slave_config)
            return conn
        except Exception as e:
            print(f"Error conectando al esclavo: {e}")
            return None
    
    def verify_database_structure(self, conn):
        """Verificar que las tablas existen en la base de datos"""
        cursor = conn.cursor()
        try:
            # Buscar en múltiples esquemas posibles
            schemas_to_check = ['imdb_schema', 'public']
            tables_found = {}
            
            print("Buscando tablas en esquemas...")
            
            for schema in schemas_to_check:
                print(f"Verificando esquema: {schema}")
                
                # Obtener todas las tablas del esquema actual
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = %s
                    ORDER BY table_name
                """, (schema,))
                
                schema_tables = [row[0] for row in cursor.fetchall()]
                
                if schema_tables:
                    print(f"  Tablas encontradas en '{schema}': {schema_tables}")
                    
                    # Buscar las tablas que necesitamos
                    categoria_found = None
                    titulo_found = None
                    
                    for table in schema_tables:
                        if table.lower() == 'categoria':
                            categoria_found = table
                        elif table.lower() == 'titulo':
                            titulo_found = table
                    
                    # Si encontramos ambas tablas en este esquema, usar este esquema
                    if categoria_found and titulo_found:
                        self.schema_name = schema
                        self.categoria_table_name = categoria_found
                        self.titulo_table_name = titulo_found
                        tables_found['categoria'] = categoria_found
                        tables_found['titulo'] = titulo_found
                        
                        print(f"Tablas encontradas en esquema '{schema}':")
                        print(f"  - Categoria: {categoria_found}")
                        print(f"  - Titulo: {titulo_found}")
                        break
                else:
                    print(f"  Sin tablas en esquema '{schema}'")
            
            # Si no encontramos las tablas en ningún esquema
            if not self.schema_name:
                print("ERROR: No se encontraron las tablas 'categoria' y 'titulo'")
                print("TABLAS DISPONIBLES EN TODOS LOS ESQUEMAS:")
                
                # Mostrar todas las tablas disponibles para debug
                cursor.execute("""
                    SELECT table_schema, table_name 
                    FROM information_schema.tables 
                    WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY table_schema, table_name
                """)
                all_tables = cursor.fetchall()
                
                current_schema = None
                for schema, table in all_tables:
                    if current_schema != schema:
                        print(f"\n  Esquema '{schema}':")
                        current_schema = schema
                    print(f"    - {table}")
                
                return False
            
            return True
            
        except Exception as e:
            print(f"Error verificando estructura: {e}")
            return False
        finally:
            cursor.close()
    
    def get_full_table_name(self, table_name):
        """Obtener el nombre completo de la tabla con esquema"""
        if self.schema_name and self.schema_name != 'public':
            return f'"{self.schema_name}"."{table_name}"'
        else:
            return f'"{table_name}"'
    
    def load_csv_data(self, csv_file, limit=None):
        """Cargar datos desde CSV con manejo robusto de errores"""
        try:
            if not os.path.exists(csv_file):
                print(f"Error: Archivo {csv_file} no encontrado")
                return None
            
            print(f"Cargando datos de {csv_file}...")
            
            # Detectar separador automáticamente
            with open(csv_file, 'r', encoding='utf-8') as f:
                first_line = f.readline()
                separator = ',' if ',' in first_line else '\t'
            
            # Leer con configuración robusta
            read_kwargs = {
                'sep': separator,
                'na_values': ['\\N', 'NULL', ''],
                'keep_default_na': True,
                'on_bad_lines': 'skip',
                'encoding': 'utf-8',
                'low_memory': False
            }
            
            if limit is not None:
                read_kwargs['nrows'] = limit
            
            df = pd.read_csv(csv_file, **read_kwargs)
            
            print(f"Datos cargados: {len(df)} registros")
            print(f"Columnas: {list(df.columns)}")
            return df
        except Exception as e:
            print(f"Error cargando CSV {csv_file}: {e}")
            return None
    
    def load_and_insert_categorias(self, conn):
        """Cargar categorías desde CSV e insertarlas"""
        cursor = conn.cursor()
        try:
            print("Cargando categorías...")
            
            # Leer categorías desde CSV
            categorias_df = self.load_csv_data("datos_separados/categorias.csv")
            if categorias_df is None:
                print("No se pudo cargar el archivo de categorías")
                return False
            
            # Preparar datos para inserción
            categorias_data = []
            for _, row in categorias_df.iterrows():
                nombre = row['nombre']
                if pd.notna(nombre) and nombre.strip():
                    categorias_data.append((nombre.strip(),))
            
            if not categorias_data:
                print("No se encontraron categorías válidas")
                return False
            
            # Usar el nombre completo de la tabla con esquema
            full_table_name = self.get_full_table_name(self.categoria_table_name)
            insert_query = f"""
                INSERT INTO {full_table_name} (nombre) 
                VALUES %s 
                ON CONFLICT (nombre) DO NOTHING
            """
            
            print(f"Ejecutando query: {insert_query}")
            execute_values(cursor, insert_query, categorias_data)
            conn.commit()
            print(f"Categorías insertadas: {len(categorias_data)}")
            
            # Verificar inserción
            cursor.execute(f"SELECT nombre FROM {full_table_name} ORDER BY nombre")
            categorias_insertadas = cursor.fetchall()
            print(f"Categorías en BD: {[cat[0] for cat in categorias_insertadas[:10]]}")
            
            return True
            
        except Exception as e:
            print(f"Error insertando categorías: {e}")
            print(f"Detalles del error: {type(e).__name__}")
            conn.rollback()
            return False
        finally:
            cursor.close()
    
    def get_categoria_id(self, conn, nombre_categoria):
        """Obtener ID de categoría"""
        cursor = conn.cursor()
        try:
            full_table_name = self.get_full_table_name(self.categoria_table_name)
            cursor.execute(f"SELECT id_categoria FROM {full_table_name} WHERE nombre = %s", (nombre_categoria,))
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            print(f"Error obteniendo categoría '{nombre_categoria}': {e}")
            return None
        finally:
            cursor.close()
    
    def load_titulos_data(self, limit=None):
        """Cargar datos de la tabla Titulo desde CSV"""
        
        csv_file = "datos_separados/titulos.csv"
        
        df = self.load_csv_data(csv_file, limit)
        if df is None:
            return False
        
        master_conn = self.connect_to_master()
        if not master_conn:
            return False
        
        try:
            # PASO 0: Verificar estructura de base de datos
            print("PASO 0: Verificando estructura de base de datos...")
            if not self.verify_database_structure(master_conn):
                print("ERROR: La estructura de la base de datos no es correcta.")
                print("Por favor ejecuta primero el script de creación de la base de datos.")
                return False
            
            print(f"CONFIGURACIÓN DETECTADA:")
            print(f"  - Esquema: {self.schema_name}")
            print(f"  - Tabla categorías: {self.categoria_table_name}")
            print(f"  - Tabla títulos: {self.titulo_table_name}")
            
            # PASO 1: Insertar categorías primero
            print("\nPASO 1: Insertando categorías...")
            if not self.load_and_insert_categorias(master_conn):
                print("Error cargando categorías")
                return False
            
            cursor = master_conn.cursor()
            
            # PASO 2: Cargar todas las categorías UNA SOLA VEZ (OPTIMIZACIÓN)
            full_categoria_table = self.get_full_table_name(self.categoria_table_name)
            cursor.execute(f"SELECT nombre, id_categoria FROM {full_categoria_table}")
            categoria_map = dict(cursor.fetchall())
            print(f"Mapa de categorías cargado: {categoria_map}")
            
            # PASO 3: Procesar datos de títulos
            print(f"\nPASO 3: Procesando {len(df)} títulos para inserción...")
            insert_data = []
            errores = 0
            procesados = 0
            
            for index, row in df.iterrows():
                try:
                    # Extraer datos del CSV
                    tconst = row.get('tconst')
                    categoria_nombre = row.get('categoria')
                    titulo_popular = row.get('titulo_popular')
                    titulo_original = row.get('titulo_original')
                    es_contenido_adulto = row.get('es_contenido_adulto', 0)
                    anio_lanzamiento = row.get('anio_lanzamiento')
                    anio_finalizacion = row.get('anio_finalizacion')
                    duracion_minutos = row.get('duracion_minutos')
                    
                    # Validaciones básicas
                    if not tconst or pd.isna(tconst):
                        errores += 1
                        continue
                    
                    if not titulo_popular or pd.isna(titulo_popular):
                        titulo_popular = f"Título {tconst}"
                    
                    if not titulo_original or pd.isna(titulo_original):
                        titulo_original = titulo_popular
                    
                    # Convertir valores nulos y tipos
                    anio_lanzamiento = int(anio_lanzamiento) if pd.notna(anio_lanzamiento) else None
                    anio_finalizacion = int(anio_finalizacion) if pd.notna(anio_finalizacion) else None
                    duracion_minutos = int(duracion_minutos) if pd.notna(duracion_minutos) else None
                    
                    # Convertir es_contenido_adulto a boolean
                    es_adulto = bool(int(es_contenido_adulto)) if pd.notna(es_contenido_adulto) else False
                    
                    # Obtener ID de categoría usando el mapa precargado
                    categoria_id = categoria_map.get(categoria_nombre)
                    if not categoria_id:
                        print(f"Categoría no encontrada: '{categoria_nombre}' para título {tconst}")
                        errores += 1
                        continue
                    
                    # Preparar datos para inserción
                    insert_data.append((
                        str(tconst).strip(),
                        categoria_id,
                        str(titulo_popular).strip(),
                        str(titulo_original).strip(),
                        es_adulto,
                        anio_lanzamiento,
                        anio_finalizacion,
                        duracion_minutos
                    ))
                    
                    procesados += 1
                    
                    # Insertar en lotes para optimizar rendimiento
                    if len(insert_data) >= 1000:  # Lotes de 1000
                        success_count = self.insert_batch_titulos_safe(master_conn, insert_data)
                        insert_data = []
                        if procesados % 10000 == 0:  # Mostrar progreso cada 10k
                            print(f"Procesados {procesados} registros... (errores: {errores})")
                
                except Exception as e:
                    print(f"Error procesando registro {index}: {e}")
                    errores += 1
                    continue
            
            # Insertar último lote
            if insert_data:
                self.insert_batch_titulos_safe(master_conn, insert_data)
            
            master_conn.commit()
            print(f"\nINSERCIÓN COMPLETADA:")
            print(f"  - Registros procesados: {procesados}")
            print(f"  - Errores: {errores}")
            
            # Verificar inserción
            full_titulo_table = self.get_full_table_name(self.titulo_table_name)
            cursor.execute(f"SELECT COUNT(*) FROM {full_titulo_table}")
            total_titulos = cursor.fetchone()[0]
            print(f"  - Total títulos en BD: {total_titulos}")
            
            print("Esperando replicación (5 segundos)...")
            import time
            time.sleep(5)
            
            return True
            
        except Exception as e:
            print(f"Error cargando datos de títulos: {e}")
            print(f"Tipo de error: {type(e).__name__}")
            master_conn.rollback()
            return False
        finally:
            master_conn.close()
    
    def insert_batch_titulos_safe(self, conn, data):
        """Insertar lote de títulos con manejo seguro de transacciones"""
        cursor = conn.cursor()
        try:
            full_titulo_table = self.get_full_table_name(self.titulo_table_name)
            insert_query = f"""
                INSERT INTO {full_titulo_table} (tconst, id_categoria, titulo_popular, titulo_original, 
                                    es_contenido_adulto, anio_lanzamiento, anio_finalizacion, duracion_minutos)
                VALUES %s
                ON CONFLICT (tconst) DO NOTHING
            """
            execute_values(cursor, insert_query, data, page_size=500)
            return len(data)
        except Exception as e:
            print(f"Error en lote de inserción: {e}")
            # ROLLBACK para limpiar el estado de la transacción
            conn.rollback()
            
            # Crear una nueva transacción para insertar individualmente
            try:
                success_count = 0
                full_titulo_table = self.get_full_table_name(self.titulo_table_name)
                for item in data:
                    try:
                        cursor.execute(f"""
                            INSERT INTO {full_titulo_table} (tconst, id_categoria, titulo_popular, titulo_original, 
                                                es_contenido_adulto, anio_lanzamiento, anio_finalizacion, duracion_minutos)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (tconst) DO NOTHING
                        """, item)
                        success_count += 1
                    except Exception as item_error:
                        print(f"Error en registro individual {item[0]}: {item_error}")
                        # Rollback individual para limpiar el estado
                        conn.rollback()
                        continue
                
                # Commit después de las inserciones individuales exitosas
                conn.commit()
                return success_count
            except Exception as individual_error:
                print(f"Error en inserción individual: {individual_error}")
                conn.rollback()
                return 0
        finally:
            cursor.close()
    
    def verify_replication(self):
        """Verificar que la replicación funciona correctamente"""
        print("\n" + "="*50)
        print("VERIFICANDO REPLICACIÓN")
        print("="*50)
        
        # Conectar a ambos servidores
        master_conn = self.connect_to_master()
        slave_conn = self.connect_to_slave()
        
        if not master_conn or not slave_conn:
            print("Error de conexión a uno o ambos servidores")
            return False
        
        try:
            master_cursor = master_conn.cursor()
            slave_cursor = slave_conn.cursor()
            
            # Usar nombres completos de tablas
            full_titulo_table = self.get_full_table_name(self.titulo_table_name)
            full_categoria_table = self.get_full_table_name(self.categoria_table_name)
            
            # Contar registros en ambos servidores
            master_cursor.execute(f"SELECT COUNT(*) FROM {full_titulo_table};")
            master_count = master_cursor.fetchone()[0]
            
            master_cursor.execute(f"SELECT COUNT(*) FROM {full_categoria_table};")
            master_cat_count = master_cursor.fetchone()[0]
            
            slave_cursor.execute(f"SELECT COUNT(*) FROM {full_titulo_table};")
            slave_count = slave_cursor.fetchone()[0]
            
            slave_cursor.execute(f"SELECT COUNT(*) FROM {full_categoria_table};")
            slave_cat_count = slave_cursor.fetchone()[0]
            
            print(f"MAESTRO - Categorías: {master_cat_count}, Títulos: {master_count}")
            print(f"ESCLAVO - Categorías: {slave_cat_count}, Títulos: {slave_count}")
            
            # Verificar sincronización
            if master_count == slave_count and master_cat_count == slave_cat_count:
                print("REPLICACIÓN EXITOSA - Los datos están sincronizados")
                replication_ok = True
            else:
                print("ADVERTENCIA - Diferencia en número de registros")
                replication_ok = False
            
            # Mostrar muestra de datos
            print("\n--- MUESTRA DE DATOS MAESTRO ---")
            master_cursor.execute(f"""
                SELECT t.tconst, t.titulo_popular, t.anio_lanzamiento, c.nombre
                FROM {full_titulo_table} t 
                JOIN {full_categoria_table} c ON t.id_categoria = c.id_categoria
                ORDER BY t.tconst
                LIMIT 5
            """)
            for row in master_cursor.fetchall():
                titulo_truncado = (row[1][:30] + "...") if len(row[1]) > 30 else row[1]
                print(f"  {row[0]} | {titulo_truncado} | {row[2]} | {row[3]}")
            
            print("\n--- MUESTRA DE DATOS ESCLAVO ---")
            slave_cursor.execute(f"""
                SELECT t.tconst, t.titulo_popular, t.anio_lanzamiento, c.nombre
                FROM {full_titulo_table} t 
                JOIN {full_categoria_table} c ON t.id_categoria = c.id_categoria
                ORDER BY t.tconst
                LIMIT 5
            """)
            for row in slave_cursor.fetchall():
                titulo_truncado = (row[1][:30] + "...") if len(row[1]) > 30 else row[1]
                print(f"  {row[0]} | {titulo_truncado} | {row[2]} | {row[3]}")
            
            return replication_ok
            
        except Exception as e:
            print(f"Error verificando replicación: {e}")
            return False
        finally:
            master_conn.close()
            slave_conn.close()
    
    def test_insert_new_record(self):
        """Insertar un nuevo registro para probar replicación en tiempo real"""
        print("\n" + "="*50)
        print("PROBANDO INSERCIÓN EN TIEMPO REAL")
        print("="*50)
        
        master_conn = self.connect_to_master()
        if not master_conn:
            return False
        
        try:
            cursor = master_conn.cursor()
            
            # Obtener ID de categoría para movie
            categoria_id = self.get_categoria_id(master_conn, 'movie')
            if not categoria_id:
                print("No se encontró categoría 'movie', usando la primera disponible...")
                full_categoria_table = self.get_full_table_name(self.categoria_table_name)
                cursor.execute(f"SELECT id_categoria, nombre FROM {full_categoria_table} LIMIT 1")
                result = cursor.fetchone()
                if result:
                    categoria_id, categoria_nombre = result
                    print(f"Usando categoría: {categoria_nombre}")
                else:
                    print("No se encontraron categorías")
                    return False
            
            # Crear registro único con timestamp
            unique_id = random.randint(100000, 999999)
            new_tconst = f"tt{unique_id}"
            new_title = f"Película Prueba {unique_id}"
            
            # Insertar en maestro
            full_titulo_table = self.get_full_table_name(self.titulo_table_name)
            cursor.execute(f"""
                INSERT INTO {full_titulo_table} (tconst, id_categoria, titulo_popular, titulo_original, 
                                    es_contenido_adulto, anio_lanzamiento)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (new_tconst, categoria_id, new_title, new_title, False, 2024))
            
            master_conn.commit()
            print(f"NUEVO REGISTRO INSERTADO EN MAESTRO: {new_tconst}")
            
            # Esperar replicación
            print("Esperando replicación (3 segundos)...")
            import time
            time.sleep(3)
            
            # Verificar en esclavo
            slave_conn = self.connect_to_slave()
            if slave_conn:
                slave_cursor = slave_conn.cursor()
                slave_cursor.execute(
                    f"SELECT titulo_popular FROM {full_titulo_table} WHERE tconst = %s", 
                    (new_tconst,)
                )
                result = slave_cursor.fetchone()
                
                if result:
                    print(f"REGISTRO ENCONTRADO EN ESCLAVO: {result[0]}")
                    print("REPLICACIÓN EN TIEMPO REAL FUNCIONANDO")
                    replication_ok = True
                else:
                    print("REGISTRO NO ENCONTRADO EN ESCLAVO")
                    print("POSIBLE PROBLEMA CON LA REPLICACIÓN")
                    replication_ok = False
                
                slave_conn.close()
                return replication_ok
            
            return False
            
        except Exception as e:
            print(f"Error en prueba de inserción: {e}")
            master_conn.rollback()
            return False
        finally:
            master_conn.close()

def main():
    print("CARGADOR DE DATOS IMDB - SISTEMA MAESTRO-ESCLAVO")
    print("VERSIÓN CORREGIDA - Manejo seguro de transacciones")
    print("="*70)
    
    loader = IMDBDataLoader()
    
    # Verificar conexión inicial
    print("Verificando conexiones...")
    master_conn = loader.connect_to_master()
    slave_conn = loader.connect_to_slave()
    
    if not master_conn:
        print("ERROR: No se puede conectar al servidor maestro")
        return
    if not slave_conn:
        print("ERROR: No se puede conectar al servidor esclavo")
        return
    
    master_conn.close()
    slave_conn.close()
    print("Conexiones verificadas correctamente")
    
    # 1. Cargar datos desde CSV
    print("\nIniciando carga de datos...")
    success = loader.load_titulos_data(limit=None)  # Cargar todos los registros
    
    if not success:
        print("Error cargando datos. Verificar:")
        print("1. Que la base de datos 'imdb_database' existe")
        print("2. Que las tablas han sido creadas correctamente")
        print("3. Que los archivos CSV están en la carpeta 'datos_separados/'")
        print("4. Que las tablas están en el esquema 'imdb_schema' o 'public'")
        return
    
    # 2. Verificar replicación
    print("\nVerificando replicación...")
    replication_ok = loader.verify_replication()
    
    # 3. Probar inserción en tiempo real
    print("\nProbando inserción en tiempo real...")
    realtime_ok = loader.test_insert_new_record()
    
    # Resumen final
    print("\n" + "="*70)
    print("RESUMEN FINAL")
    print("="*70)
    print(f"Carga de datos: {'EXITOSA' if success else 'FALLIDA'}")
    print(f"Replicación: {'FUNCIONANDO' if replication_ok else 'CON PROBLEMAS'}")
    print(f"Replicación en tiempo real: {'FUNCIONANDO' if realtime_ok else 'CON PROBLEMAS'}")
    
    if success and replication_ok and realtime_ok:
        print("\n¡PROCESO COMPLETADO EXITOSAMENTE!")
    else:
        print("\nProceso completado con advertencias. Revisar configuración de replicación.")
    
    print("="*70)

if __name__ == "__main__":
    main()