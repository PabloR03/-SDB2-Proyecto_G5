import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import logging
from typing import List, Tuple, Set
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OptimizedPuntuacionLoader:
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
    
    def check_titulos_exist_batch(self, tconst_list: List[str]) -> Set[str]:
        """Verificar qué tconst existen en la tabla Titulo (en lotes)"""
        try:
            with self.conn.cursor() as cursor:
                # Usar ANY para verificar múltiples valores de una vez
                cursor.execute("""
                    SELECT tconst 
                    FROM imdb_schema.Titulo 
                    WHERE tconst = ANY(%s)
                """, (tconst_list,))
                
                existing = {row[0] for row in cursor.fetchall()}
                return existing
                
        except Exception as e:
            logger.error(f"Error verificando títulos existentes: {e}")
            raise
    
    def clean_puntuacion_table(self):
        """Limpiar la tabla Puntuacion antes de cargar"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("DELETE FROM imdb_schema.Puntuacion")
                self.conn.commit()
                logger.info("Tabla Puntuacion limpiada")
        except Exception as e:
            logger.error(f"Error limpiando tabla Puntuacion: {e}")
            self.conn.rollback()
            raise
    
    def insert_valid_records_batch(self, valid_records: List[Tuple]):
        """Insertar registros válidos en lotes pequeños"""
        try:
            total_inserted = 0
            
            for i in range(0, len(valid_records), self.insert_batch_size):
                batch = valid_records[i:i + self.insert_batch_size]
                
                with self.conn.cursor() as cursor:
                    # No incluimos id_puntuacion porque es SERIAL (auto-generado)
                    execute_values(
                        cursor,
                        "INSERT INTO imdb_schema.Puntuacion (tconst, promedio, votos) VALUES %s",
                        batch,
                        page_size=500
                    )
                    self.conn.commit()
                    total_inserted += len(batch)
                    
                    if total_inserted % 10000 == 0:
                        logger.info(f"Insertadas {total_inserted:,} puntuaciones...")
            
            logger.info(f"Total insertado en este lote: {total_inserted:,}")
            return total_inserted
                
        except Exception as e:
            logger.error(f"Error insertando registros: {e}")
            self.conn.rollback()
            raise
    
    def process_csv_chunk(self, df_chunk: pd.DataFrame) -> Tuple[int, int]:
        """Procesar un chunk del CSV"""
        chunk_size = len(df_chunk)
        
        # Extraer lista de tconst únicos del chunk
        tconst_list = df_chunk['tconst'].dropna().unique().tolist()
        
        # Verificar cuáles existen en la tabla Titulo
        existing_tconst = self.check_titulos_exist_batch(tconst_list)
        
        # Filtrar registros válidos
        valid_records = []
        invalid_count = 0
        
        for _, row in df_chunk.iterrows():
            tconst = row['tconst']
            promedio = float(row['promedio']) if pd.notna(row['promedio']) else None
            votos = int(row['votos']) if pd.notna(row['votos']) else None
            
            # Verificar si tconst existe en Titulo
            if tconst not in existing_tconst:
                invalid_count += 1
                continue
            
            # Si llegamos aquí, el registro es válido
            valid_records.append((tconst, promedio, votos))
        
        # Insertar registros válidos de este chunk
        if valid_records:
            self.insert_valid_records_batch(valid_records)
        
        return len(valid_records), invalid_count
    
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
                logger.info("Limpiando tabla Puntuacion...")
                self.clean_puntuacion_table()
            
            # Obtener total de filas para progreso
            total_rows = self.get_csv_row_count(csv_path)
            logger.info(f"Total de filas en CSV: {total_rows:,}")
            
            # Contadores
            total_valid = 0
            total_invalid = 0
            processed_rows = 0
            start_time = time.time()
            
            # Procesar CSV por chunks
            logger.info(f"Procesando CSV en chunks de {self.batch_size:,} filas...")
            
            chunk_iter = pd.read_csv(csv_path, chunksize=self.batch_size)
            
            for chunk_num, df_chunk in enumerate(chunk_iter, 1):
                chunk_start = time.time()
                
                # Procesar chunk
                valid_count, invalid_count = self.process_csv_chunk(df_chunk)
                
                # Actualizar contadores
                total_valid += valid_count
                total_invalid += invalid_count
                processed_rows += len(df_chunk)
                
                # Estadísticas del chunk
                chunk_time = time.time() - chunk_start
                elapsed_time = time.time() - start_time
                progress = (processed_rows / total_rows) * 100 if total_rows > 0 else 0
                
                logger.info(f"Chunk {chunk_num}: {valid_count:,} válidos, {invalid_count:,} omitidos "
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
            
            print("\n" + "="*70)
            print("RESUMEN DEL PROCESO OPTIMIZADO - PUNTUACIONES")
            print("="*70)
            print(f"Total filas procesadas: {processed_rows:,}")
            print(f"Registros válidos insertados: {total_valid:,}")
            print(f"Registros omitidos (tconst no existe): {total_invalid:,}")
            print(f"Registros finales en tabla: {final_count:,}")
            print(f"Tiempo total: {total_time/60:.1f} minutos")
            print(f"Velocidad promedio: {processed_rows/total_time:.0f} filas/segundo")
            print(f"Porcentaje de éxito: {(total_valid/processed_rows*100):.1f}%")
            print("="*70)
            
        except Exception as e:
            logger.error(f"Error en el proceso optimizado: {e}")
            raise
        finally:
            self.disconnect()
    
    def get_final_count(self) -> int:
        """Obtener el conteo final de registros en la tabla"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM imdb_schema.Puntuacion")
                count = cursor.fetchone()[0]
                return count
        except Exception as e:
            logger.error(f"Error obteniendo conteo final: {e}")
            return 0

def main():
    # Configuración
    CSV_PATH = "/home/manuelimal02/Descargas/puntuaciones.csv" 
    
    print("Iniciando carga optimizada de puntuaciones...")
    print(f"Archivo: {CSV_PATH}")

    
    # Crear instancia del loader optimizado
    loader = OptimizedPuntuacionLoader()
    
    try:
        # Procesar el archivo CSV de forma optimizada
        loader.process_csv_optimized(CSV_PATH, clean_table=True)
        print("\n¡Proceso de puntuaciones completado exitosamente!")
        
    except Exception as e:
        print(f"\nError durante el proceso: {e}")

if __name__ == "__main__":
    main()