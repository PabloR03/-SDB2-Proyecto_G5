import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import logging
from typing import List, Tuple, Set
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OptimizedTituloAlternativoAtributoLoader:
    def __init__(self):
        self.conn_params = {
            'host': 'localhost',
            'port': 5432,
            'database': 'imdb_database',
            'user': 'postgres',
            'password': 'postgres'
        }
        self.conn = None
        self.batch_size = 10000  
        self.insert_batch_size = 1000 
    
    def connect(self):
        """Conectar a la base de datos"""
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            self.conn.autocommit = False  
            logger.info("Conexión exitosa a PostgreSQL")
        except Exception as e:
            logger.error(f"Error conectando a PostgreSQL: {e}")
            raise
    
    def disconnect(self):
        """Desconectar de la base de datos"""
        if self.conn:
            self.conn.close()
            logger.info("Desconectado de PostgreSQL")
    
    def check_titulo_alternativo_exist_batch(self, id_titulo_alternativo_list: List[int]) -> Set[int]:
        """Verificar qué id_titulo_alternativo existen en la tabla Titulo_Alternativo (en lotes)"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id_titulo_alternativo 
                    FROM imdb_schema.Titulo_Alternativo 
                    WHERE id_titulo_alternativo = ANY(%s)
                """, (id_titulo_alternativo_list,))
                
                existing = {row[0] for row in cursor.fetchall()}
                return existing
                
        except Exception as e:
            logger.error(f"Error verificando títulos alternativos existentes: {e}")
            raise
    
    def check_atributos_exist_batch(self, id_atributo_list: List[int]) -> Set[int]:
        """Verificar qué id_atributo existen en la tabla Atributo (en lotes)"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id_atributo 
                    FROM imdb_schema.Atributo 
                    WHERE id_atributo = ANY(%s)
                """, (id_atributo_list,))
                
                existing = {row[0] for row in cursor.fetchall()}
                return existing
                
        except Exception as e:
            logger.error(f"Error verificando atributos existentes: {e}")
            raise
    
    def clean_titulo_alternativo_atributo_table(self):
        """Limpiar la tabla Titulo_Alternativo_Atributo antes de cargar"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("DELETE FROM imdb_schema.Titulo_Alternativo_Atributo")
                self.conn.commit()
                logger.info("Tabla Titulo_Alternativo_Atributo limpiada")
        except Exception as e:
            logger.error(f"Error limpiando tabla Titulo_Alternativo_Atributo: {e}")
            self.conn.rollback()
            raise
    
    def insert_valid_records_batch(self, valid_records: List[Tuple]):
        """Insertar registros válidos en lotes pequeños"""
        try:
            total_inserted = 0
            
            for i in range(0, len(valid_records), self.insert_batch_size):
                batch = valid_records[i:i + self.insert_batch_size]
                
                with self.conn.cursor() as cursor:
                    execute_values(
                        cursor,
                        """INSERT INTO imdb_schema.Titulo_Alternativo_Atributo 
                           (id_titulo_alternativo_atributo, id_titulo_alternativo, id_atributo) 
                           VALUES %s""",
                        batch,
                        page_size=500
                    )
                    self.conn.commit()
                    total_inserted += len(batch)
                    
                    if total_inserted % 10000 == 0:
                        logger.info(f"Insertados {total_inserted:,} registros de título alternativo-atributo...")
            
            logger.info(f"Total insertado en este lote: {total_inserted:,}")
            return total_inserted
                
        except Exception as e:
            logger.error(f"Error insertando registros: {e}")
            self.conn.rollback()
            raise
    
    def process_csv_chunk(self, df_chunk: pd.DataFrame) -> Tuple[int, int, int]:
        """Procesar un chunk del CSV"""
        chunk_size = len(df_chunk)
        
        # Extraer listas únicas del chunk
        id_titulo_alternativo_list = df_chunk['id_titulo_alternativo'].dropna().astype(int).unique().tolist()
        id_atributo_list = df_chunk['id_atributo'].dropna().astype(int).unique().tolist()
        
        # Verificar cuáles existen en las tablas respectivas
        existing_titulo_alternativo = self.check_titulo_alternativo_exist_batch(id_titulo_alternativo_list)
        existing_atributos = self.check_atributos_exist_batch(id_atributo_list)
        
        # Filtrar registros válidos
        valid_records = []
        invalid_titulo_alternativo_count = 0
        invalid_atributo_count = 0
        
        for _, row in df_chunk.iterrows():
            id_titulo_alternativo_atributo = int(row['id_titulo_alternativo_atributo'])
            id_titulo_alternativo = int(row['id_titulo_alternativo'])
            id_atributo = int(row['id_atributo'])
            
            # Verificar si id_titulo_alternativo existe en Titulo_Alternativo
            if id_titulo_alternativo not in existing_titulo_alternativo:
                invalid_titulo_alternativo_count += 1
                continue
            
            # Verificar si id_atributo existe en Atributo
            if id_atributo not in existing_atributos:
                invalid_atributo_count += 1
                continue
            
            # Si llegamos aquí, el registro es válido
            valid_records.append((id_titulo_alternativo_atributo, id_titulo_alternativo, id_atributo))
        
        # Insertar registros válidos de este chunk
        if valid_records:
            self.insert_valid_records_batch(valid_records)
        
        return len(valid_records), invalid_titulo_alternativo_count, invalid_atributo_count
    
    def get_csv_row_count(self, csv_path: str) -> int:
        """Obtener el número total de filas del CSV sin cargarlo completo"""
        try:
            with open(csv_path, 'r') as f:
                return sum(1 for line in f) - 1  # -1 por el header
        except Exception as e:
            logger.error(f"Error contando filas del CSV: {e}")
            return 0
    
    def process_csv_optimized(self, csv_path: str, clean_table: bool = True):
        """Procesar el CSV de forma optimizada por chunks"""
        try:
            # Conectar a la base de datos
            self.connect()
            
            # Limpiar tabla si se solicita
            if clean_table:
                logger.info("Limpiando tabla Titulo_Alternativo_Atributo...")
                self.clean_titulo_alternativo_atributo_table()
            
            # Obtener total de filas para progreso
            total_rows = self.get_csv_row_count(csv_path)
            logger.info(f"Total de filas en CSV: {total_rows:,}")
            
            # Contadores
            total_valid = 0
            total_invalid_titulo_alternativo = 0
            total_invalid_atributo = 0
            processed_rows = 0
            start_time = time.time()
            
            # Procesar CSV por chunks
            logger.info(f"Procesando CSV en chunks de {self.batch_size:,} filas...")
            
            chunk_iter = pd.read_csv(csv_path, chunksize=self.batch_size)
            
            for chunk_num, df_chunk in enumerate(chunk_iter, 1):
                chunk_start = time.time()
                
                # Procesar chunk
                valid_count, invalid_titulo_alternativo, invalid_atributo = self.process_csv_chunk(df_chunk)
                
                # Actualizar contadores
                total_valid += valid_count
                total_invalid_titulo_alternativo += invalid_titulo_alternativo
                total_invalid_atributo += invalid_atributo
                processed_rows += len(df_chunk)
                
                # Estadísticas del chunk
                chunk_time = time.time() - chunk_start
                elapsed_time = time.time() - start_time
                progress = (processed_rows / total_rows) * 100 if total_rows > 0 else 0
                
                total_invalid = invalid_titulo_alternativo + invalid_atributo
                logger.info(f"Chunk {chunk_num}: {valid_count:,} válidos, {total_invalid:,} omitidos "
                          f"({chunk_time:.1f}s) - Progreso: {progress:.1f}%")
                
                # Estimación de tiempo restante
                if processed_rows > 0:
                    rows_per_second = processed_rows / elapsed_time
                    remaining_rows = total_rows - processed_rows
                    eta_seconds = remaining_rows / rows_per_second if rows_per_second > 0 else 0
                    eta_minutes = eta_seconds / 60
                    
                    if eta_minutes > 1:
                        logger.info(f"ETA: {eta_minutes:.1f} minutos restantes")
            
            # Resumen final
            total_time = time.time() - start_time
            final_count = self.get_final_count()
            total_invalid_all = total_invalid_titulo_alternativo + total_invalid_atributo
            
            print("\n" + "="*75)
            print("RESUMEN DEL PROCESO OPTIMIZADO - TITULO_ALTERNATIVO_ATRIBUTO")
            print("="*75)
            print(f"Total filas procesadas: {processed_rows:,}")
            print(f"Registros válidos insertados: {total_valid:,}")
            print(f"Registros omitidos por id_titulo_alternativo inválido: {total_invalid_titulo_alternativo:,}")
            print(f"Registros omitidos por id_atributo inválido: {total_invalid_atributo:,}")
            print(f"Total registros omitidos: {total_invalid_all:,}")
            print(f"Registros finales en tabla: {final_count:,}")
            print(f"Tiempo total: {total_time/60:.1f} minutos")
            print(f"Velocidad promedio: {processed_rows/total_time:.0f} filas/segundo")
            print(f"Porcentaje de éxito: {(total_valid/processed_rows*100):.1f}%")
            print("="*75)
            
        except Exception as e:
            logger.error(f"Error en el proceso optimizado: {e}")
            raise
        finally:
            self.disconnect()
    
    def get_final_count(self) -> int:
        """Obtener el conteo final de registros en la tabla"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM imdb_schema.Titulo_Alternativo_Atributo")
                count = cursor.fetchone()[0]
                return count
        except Exception as e:
            logger.error(f"Error obteniendo conteo final: {e}")
            return 0

def main():
    # Configuración
    CSV_PATH = "/home/manuelimal02/Descargas/titulo_alternativo_atributo.csv"  # Cambia el nombre si es necesario
    
    print("Iniciando carga optimizada de Titulo_Alternativo_Atributo...")
    print(f"Archivo: {CSV_PATH}")

    loader = OptimizedTituloAlternativoAtributoLoader()
    
    try:
        # Procesar el archivo CSV de forma optimizada
        loader.process_csv_optimized(CSV_PATH, clean_table=True)
        print("\nProceso de Titulo_Alternativo_Atributo completado exitosamente!")
        
    except Exception as e:
        print(f"\nError durante el proceso: {e}")

if __name__ == "__main__":
    main()