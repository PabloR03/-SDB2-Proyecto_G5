import csv
import os
import logging
from pathlib import Path
import gc

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IMDBPendientes:
    def __init__(self, input_folder="../Datos", output_folder="datos_separados"):
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.chunk_size = 3000 
        
        # Crear carpeta de salida si no existe
        self.output_folder.mkdir(exist_ok=True)
        
    def clean_value(self, value):
        """Limpia valores nulos y los convierte a None o cadena vacía"""
        if not value or str(value).strip() in ['\\N', 'N/A', '', 'NULL']:
            return ''
        return str(value).strip()
    
    def split_list_field(self, value, separator=','):
        """Divide campos que contienen listas separadas por comas"""
        if not value or value == '':
            return []
        return [item.strip() for item in str(value).split(separator) if item.strip()]
    
    def process_title_principals_csv(self):
        """Procesa title.principals.tsv usando CSV reader nativo (más eficiente en memoria)"""
        logger.info("Procesando title.principals.tsv con CSV reader...")
        
        input_file = self.input_folder / "title.principals.tsv" / "title.principals.tsv"
        output_file = self.output_folder / "reparto.csv"
        
        if not input_file.exists():
            logger.error(f"Archivo no encontrado: {input_file}")
            return
        
        count = 0
        batch_count = 0
        reparto_batch = []
        
        with open(input_file, 'r', encoding='utf-8') as infile, \
             open(output_file, 'w', encoding='utf-8', newline='') as outfile:
            
            reader = csv.DictReader(infile, delimiter='\t')
            writer = csv.DictWriter(outfile, fieldnames=[
                'tconst', 'relevancia', 'nconst', 'categoria_profesion', 'rol', 'personaje'
            ])
            writer.writeheader()
            
            for row in reader:
                count += 1
                
                if count % 10000 == 0:
                    logger.info(f"Procesados {count} registros de title.principals...")
                
                tconst = self.clean_value(row.get('tconst', ''))
                if not tconst:
                    continue
                
                reparto_item = {
                    'tconst': tconst,
                    'relevancia': self.clean_value(row.get('ordering', '')),
                    'nconst': self.clean_value(row.get('nconst', '')),
                    'categoria_profesion': self.clean_value(row.get('category', '')),
                    'rol': self.clean_value(row.get('job', '')),
                    'personaje': self.clean_value(row.get('characters', ''))
                }
                
                reparto_batch.append(reparto_item)
                
                # Escribir en lotes para ahorrar memoria
                if len(reparto_batch) >= self.chunk_size:
                    writer.writerows(reparto_batch)
                    reparto_batch = []
                    batch_count += 1
                    
                    # Forzar garbage collection
                    if batch_count % 100 == 0:
                        gc.collect()
            
            # Escribir último lote
            if reparto_batch:
                writer.writerows(reparto_batch)
        
        logger.info(f"title.principals completado: {count} registros procesados")
    
    def process_title_ratings_csv(self):
        """Procesa title.ratings.tsv usando CSV reader"""
        logger.info("Procesando title.ratings.tsv...")
        
        input_file = self.input_folder / "title.ratings.tsv" / "title.ratings.tsv"
        output_file = self.output_folder / "puntuaciones.csv"
        
        if not input_file.exists():
            logger.error(f"Archivo no encontrado: {input_file}")
            return
        
        count = 0
        
        with open(input_file, 'r', encoding='utf-8') as infile, \
             open(output_file, 'w', encoding='utf-8', newline='') as outfile:
            
            reader = csv.DictReader(infile, delimiter='\t')
            writer = csv.DictWriter(outfile, fieldnames=['tconst', 'promedio', 'votos'])
            writer.writeheader()
            
            for row in reader:
                count += 1
                
                if count % 50000 == 0:
                    logger.info(f"Procesados {count} registros de title.ratings...")
                
                tconst = self.clean_value(row.get('tconst', ''))
                if not tconst:
                    continue
                
                puntuacion_data = {
                    'tconst': tconst,
                    'promedio': self.clean_value(row.get('averageRating', '')),
                    'votos': self.clean_value(row.get('numVotes', ''))
                }
                
                writer.writerow(puntuacion_data)
        
        logger.info(f"title.ratings completado: {count} registros procesados")
    
    def process_remaining_files(self):
        """Procesa solo los archivos que quedaron pendientes"""
        logger.info("Procesando archivos pendientes...")
        
        try:
            # Verificar qué archivos existen ya
            existing_files = list(self.output_folder.glob("*.csv"))
            existing_names = [f.stem for f in existing_files]
            
            logger.info(f"Archivos ya existentes: {existing_names}")
            
            # Procesar title.principals si no existe
            if 'reparto' not in existing_names:
                self.process_title_principals_csv()
            else:
                logger.info("reparto.csv ya existe, saltando...")
            
            # Procesar title.ratings si no existe
            if 'puntuaciones' not in existing_names:
                self.process_title_ratings_csv()
            else:
                logger.info("puntuaciones.csv ya existe, saltando...")
            
            logger.info("Procesamiento de archivos pendientes completado!")
            
        except Exception as e:
            logger.error(f"Error durante el procesamiento: {str(e)}")
            raise

if __name__ == "__main__":
    # Crear instancia del procesador
    processor = IMDBPendientes()
    
    # Procesar archivos pendientes
    processor.process_remaining_files()