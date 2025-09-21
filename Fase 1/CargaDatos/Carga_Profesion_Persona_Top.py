import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import logging
from typing import List, Tuple, Set
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OptimizedProfesionPersonaTopLoader:
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
    
    def check_personas_exist_batch(self, nconst_list: List[str]) -> Set[str]:
        """Verificar qué nconst existen en la tabla Persona (en lotes)"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT nconst 
                    FROM imdb_schema.Persona 
                    WHERE nconst = ANY(%s)
                """, (nconst_list,))
                
                existing = {row[0] for row in cursor.fetchall()}
                return existing
                
        except Exception as e:
            logger.error(f"Error verificando personas existentes: {e}")
            raise
    
    def check_profesiones_exist_batch(self, id_profesion_list: List[int]) -> Set[int]:
        """Verificar qué id_profesion existen en la tabla Profesion (en lotes)"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id_profesion 
                    FROM imdb_schema.Profesion 
                    WHERE id_profesion = ANY(%s)
                """, (id_profesion_list,))
                
                existing = {row[0] for row in cursor.fetchall()}
                return existing
                
        except Exception as e:
            logger.error(f"Error verificando profesiones existentes: {e}")
            raise
    
    def clean_profesion_persona_top_table(self):
        """Limpiar la tabla Profesion_Persona_Top antes de cargar"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("DELETE FROM imdb_schema.Profesion_Persona_Top")
                self.conn.commit()
                logger.info("Tabla Profesion_Persona_Top limpiada")
        except Exception as e:
            logger.error(f"Error limpiando tabla Profesion_Persona_Top: {e}")
            self.conn.rollback()
            raise
    
    def insert_valid_records_batch(self, valid_records: List[Tuple]):
        """Insertar registros válidos en lotes pequeños"""
        try:
            total_inserted = 0
            
            # Procesar en lotes pequeños para evitar memory issues
            for i in range(0, len(valid_records), self.insert_batch_size):
                batch = valid_records[i:i + self.insert_batch_size]
                
                with self.conn.cursor() as cursor:
                    execute_values(
                        cursor,
                        "INSERT INTO imdb_schema.Profesion_Persona_Top (id_profesion_persona, nconst, id_profesion) VALUES %s",
                        batch,
                        page_size=500
                    )
                    self.conn.commit()
                    total_inserted += len(batch)
                    
                    if total_inserted % 10000 == 0:
                        logger.info(f"Insertados {total_inserted:,} registros de profesión-persona...")
            
            logger.info(f"Total insertado en este lote: {total_inserted:,}")
            return total_inserted
                
        except Exception as e:
            logger.error(f"Error insertando registros: {e}")
            self.conn.rollback()
            raise
    
    def process_csv_chunk(self, df_chunk: pd.DataFrame) -> Tuple[int, int, int]:
        """Procesar un chunk del CSV"""
        chunk_size = len(df_chunk)
        
        # Extraer listas únicas de nconst e id_profesion del chunk
        nconst_list = df_chunk['nconst'].dropna().unique().tolist()
        id_profesion_list = df_chunk['id_profesion'].dropna().unique().astype(int).tolist()
        
        # Verificar cuáles existen en las tablas respectivas
        existing_personas = self.check_personas_exist_batch(nconst_list)
        existing_profesiones = self.check_profesiones_exist_batch(id_profesion_list)
        
        # Filtrar registros válidos
        valid_records = []
        invalid_persona_count = 0
        invalid_profesion_count = 0
        
        for _, row in df_chunk.iterrows():
            id_profesion_persona = int(row['id_profesion_persona'])
            nconst = row['nconst']
            id_profesion = int(row['id_profesion']) if pd.notna(row['id_profesion']) else None
            
            # Verificar si nconst existe en Persona
            if nconst not in existing_personas:
                invalid_persona_count += 1
                continue
            
            # Verificar si id_profesion existe en Profesion
            if id_profesion is None or id_profesion not in existing_profesiones:
                invalid_profesion_count += 1
                continue
            
            # Si llegamos aquí, el registro es válido
            valid_records.append((id_profesion_persona, nconst, id_profesion))
        
        # Insertar registros válidos de este chunk
        if valid_records:
            self.insert_valid_records_batch(valid_records)
        
        return len(valid_records), invalid_persona_count, invalid_profesion_count
    
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
                logger.info("Limpiando tabla Profesion_Persona_Top...")
                self.clean_profesion_persona_top_table()
            
            # Obtener total de filas para progreso
            total_rows = self.get_csv_row_count(csv_path)
            logger.info(f"Total de filas en CSV: {total_rows:,}")
            
            # Contadores
            total_valid = 0
            total_invalid_persona = 0
            total_invalid_profesion = 0
            processed_rows = 0
            start_time = time.time()
            
            # Procesar CSV por chunks
            logger.info(f"Procesando CSV en chunks de {self.batch_size:,} filas...")
            
            chunk_iter = pd.read_csv(csv_path, chunksize=self.batch_size)
            
            for chunk_num, df_chunk in enumerate(chunk_iter, 1):
                chunk_start = time.time()
                
                # Procesar chunk
                valid_count, invalid_persona, invalid_profesion = self.process_csv_chunk(df_chunk)
                
                # Actualizar contadores
                total_valid += valid_count
                total_invalid_persona += invalid_persona
                total_invalid_profesion += invalid_profesion
                processed_rows += len(df_chunk)
                
                # Estadísticas del chunk
                chunk_time = time.time() - chunk_start
                elapsed_time = time.time() - start_time
                progress = (processed_rows / total_rows) * 100 if total_rows > 0 else 0
                
                total_invalid = invalid_persona + invalid_profesion
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
            total_invalid_all = total_invalid_persona + total_invalid_profesion
            
            print("\n" + "="*75)
            print("RESUMEN DEL PROCESO OPTIMIZADO - PROFESION_PERSONA_TOP")
            print("="*75)
            print(f"Total filas procesadas: {processed_rows:,}")
            print(f"Registros válidos insertados: {total_valid:,}")
            print(f"Registros omitidos por nconst inválido: {total_invalid_persona:,}")
            print(f"Registros omitidos por id_profesion inválido: {total_invalid_profesion:,}")
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
                cursor.execute("SELECT COUNT(*) FROM imdb_schema.Profesion_Persona_Top")
                count = cursor.fetchone()[0]
                return count
        except Exception as e:
            logger.error(f"Error obteniendo conteo final: {e}")
            return 0

def main():
    # Configuración
    CSV_PATH = "/home/manuelimal02/Descargas/profesion_persona_top.csv" 
    
    print("Iniciando carga optimizada de Profesion_Persona_Top...")
    print(f"Archivo: {CSV_PATH}")

    loader = OptimizedProfesionPersonaTopLoader()
    
    try:
        # Procesar el archivo CSV de forma optimizada
        loader.process_csv_optimized(CSV_PATH, clean_table=True)
        print("\nProceso de Profesion_Persona_Top completado exitosamente!")
        
    except Exception as e:
        print(f"\nError durante el proceso: {e}")

if __name__ == "__main__":
    main()