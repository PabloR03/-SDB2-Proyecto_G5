import pandas as pd
import os
import sys
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IMDBDataSeparator:
    def __init__(self, input_folder="../Datos", output_folder="datos_separados"):
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.chunk_size = 10000
        
        # Crear carpeta de salida
        self.output_folder.mkdir(exist_ok=True)
        
    def clean_value(self, value):
        """Limpia valores nulos y los convierte a None"""
        if pd.isna(value) or str(value).strip() in ['\\N', 'N/A', '', 'NULL']:
            return None
        return str(value).strip()
    
    def split_list_field(self, value, separator=','):
        """Divide campos que contienen listas separadas por comas"""
        if not value or value is None:
            return []
        return [item.strip() for item in str(value).split(separator) if item.strip()]
    
    def process_name_basics(self):
        """Procesa name.basics.tsv para generar datos de personas y profesiones"""
        logger.info("Procesando name.basics.tsv...")
        
        input_file = self.input_folder / "name.basics.tsv" / "name.basics.tsv"
        if not input_file.exists():
            logger.error(f"Archivo no encontrado: {input_file}")
            return
        
        # Archivos de salida
        personas_file = self.output_folder / "personas.csv"
        profesiones_file = self.output_folder / "profesiones.csv"
        profesiones_persona_file = self.output_folder / "profesiones_persona.csv"
        titulos_persona_file = self.output_folder / "titulos_persona_top.csv"
        
        profesiones_set = set()
        personas_data = []
        profesiones_persona_data = []
        titulos_persona_data = []
        
        # Procesar por chunks
        chunk_num = 0
        for chunk in pd.read_csv(input_file, sep='\t', chunksize=self.chunk_size, dtype=str):
            chunk_num += 1
            logger.info(f"Procesando chunk {chunk_num} de name.basics...")
            
            for _, row in chunk.iterrows():
                nconst = self.clean_value(row['nconst'])
                if not nconst:
                    continue
                
                # Datos de persona
                persona_data = {
                    'nconst': nconst,
                    'nombre_artistico': self.clean_value(row['primaryName']),
                    'anio_nacimiento': self.clean_value(row['birthYear']),
                    'anio_fallecimiento': self.clean_value(row['deathYear'])
                }
                personas_data.append(persona_data)
                
                # Profesiones
                profesiones_raw = self.clean_value(row['primaryProfession'])
                if profesiones_raw:
                    profesiones_lista = self.split_list_field(profesiones_raw)
                    for profesion in profesiones_lista:
                        profesiones_set.add(profesion)
                        profesiones_persona_data.append({
                            'nconst': nconst,
                            'profesion': profesion
                        })
                
                # Títulos conocidos
                titulos_raw = self.clean_value(row['knownForTitles'])
                if titulos_raw:
                    titulos_lista = self.split_list_field(titulos_raw)
                    for titulo in titulos_lista:
                        titulos_persona_data.append({
                            'nconst': nconst,
                            'tconst': titulo
                        })
        
        # Guardar archivos
        pd.DataFrame(personas_data).to_csv(personas_file, index=False)
        pd.DataFrame([{'nombre': prof} for prof in profesiones_set]).to_csv(profesiones_file, index=False)
        pd.DataFrame(profesiones_persona_data).to_csv(profesiones_persona_file, index=False)
        pd.DataFrame(titulos_persona_data).to_csv(titulos_persona_file, index=False)
        
        logger.info(f"name.basics procesado: {len(personas_data)} personas, {len(profesiones_set)} profesiones")
    
    def process_title_basics(self):
        """Procesa title.basics.tsv para generar títulos, categorías y géneros"""
        logger.info("Procesando title.basics.tsv...")
        
        input_file = self.input_folder / "title.basics.tsv" / "title.basics.tsv"
        if not input_file.exists():
            logger.error(f"Archivo no encontrado: {input_file}")
            return
        
        # Archivos de salida
        titulos_file = self.output_folder / "titulos.csv"
        categorias_file = self.output_folder / "categorias.csv"
        generos_file = self.output_folder / "generos.csv"
        generos_titulo_file = self.output_folder / "generos_titulo.csv"
        
        categorias_set = set()
        generos_set = set()
        titulos_data = []
        generos_titulo_data = []
        
        chunk_num = 0
        for chunk in pd.read_csv(input_file, sep='\t', chunksize=self.chunk_size, dtype=str):
            chunk_num += 1
            logger.info(f"Procesando chunk {chunk_num} de title.basics...")
            
            for _, row in chunk.iterrows():
                tconst = self.clean_value(row['tconst'])
                if not tconst:
                    continue
                
                categoria = self.clean_value(row['titleType'])
                if categoria:
                    categorias_set.add(categoria)
                
                # Datos de título
                titulo_data = {
                    'tconst': tconst,
                    'categoria': categoria,
                    'titulo_popular': self.clean_value(row['primaryTitle']),
                    'titulo_original': self.clean_value(row['originalTitle']),
                    'es_contenido_adulto': self.clean_value(row['isAdult']),
                    'anio_lanzamiento': self.clean_value(row['startYear']),
                    'anio_finalizacion': self.clean_value(row['endYear']),
                    'duracion_minutos': self.clean_value(row['runtimeMinutes'])
                }
                titulos_data.append(titulo_data)
                
                # Géneros
                generos_raw = self.clean_value(row['genres'])
                if generos_raw:
                    generos_lista = self.split_list_field(generos_raw)
                    for genero in generos_lista:
                        generos_set.add(genero)
                        generos_titulo_data.append({
                            'tconst': tconst,
                            'genero': genero
                        })
        
        # Guardar archivos
        pd.DataFrame(titulos_data).to_csv(titulos_file, index=False)
        pd.DataFrame([{'nombre': cat} for cat in categorias_set]).to_csv(categorias_file, index=False)
        pd.DataFrame([{'nombre': gen} for gen in generos_set]).to_csv(generos_file, index=False)
        pd.DataFrame(generos_titulo_data).to_csv(generos_titulo_file, index=False)
        
        logger.info(f"title.basics procesado: {len(titulos_data)} títulos, {len(categorias_set)} categorías")
    
    def process_title_akas(self):
        """Procesa title.akas.tsv para títulos alternativos"""
        logger.info("Procesando title.akas.tsv...")
        
        input_file = self.input_folder / "title.akas.tsv" / "title.akas.tsv"
        if not input_file.exists():
            logger.error(f"Archivo no encontrado: {input_file}")
            return
        
        # Archivos de salida
        titulos_alt_file = self.output_folder / "titulos_alternativos.csv"
        regiones_file = self.output_folder / "regiones.csv"
        idiomas_file = self.output_folder / "idiomas.csv"
        tipos_titulo_file = self.output_folder / "tipos_titulo.csv"
        atributos_file = self.output_folder / "atributos.csv"
        
        regiones_set = set()
        idiomas_set = set()
        tipos_set = set()
        atributos_set = set()
        titulos_alt_data = []
        
        chunk_num = 0
        for chunk in pd.read_csv(input_file, sep='\t', chunksize=self.chunk_size, dtype=str):
            chunk_num += 1
            logger.info(f"Procesando chunk {chunk_num} de title.akas...")
            
            for _, row in chunk.iterrows():
                tconst = self.clean_value(row['titleId'])
                if not tconst:
                    continue
                
                region = self.clean_value(row['region'])
                idioma = self.clean_value(row['language'])
                tipos_raw = self.clean_value(row['types'])
                atributos_raw = self.clean_value(row['attributes'])
                
                if region:
                    regiones_set.add(region)
                if idioma:
                    idiomas_set.add(idioma)
                
                # Tipos
                tipos_lista = []
                if tipos_raw:
                    tipos_lista = self.split_list_field(tipos_raw)
                    for tipo in tipos_lista:
                        tipos_set.add(tipo)
                
                # Atributos
                atributos_lista = []
                if atributos_raw:
                    atributos_lista = self.split_list_field(atributos_raw)
                    for atributo in atributos_lista:
                        atributos_set.add(atributo)
                
                titulo_alt_data = {
                    'tconst': tconst,
                    'orden': self.clean_value(row['ordering']),
                    'nombre_titulo': self.clean_value(row['title']),
                    'region': region,
                    'idioma': idioma,
                    'tipos': ','.join(tipos_lista) if tipos_lista else None,
                    'atributos': ','.join(atributos_lista) if atributos_lista else None,
                    'es_original': self.clean_value(row['isOriginalTitle'])
                }
                titulos_alt_data.append(titulo_alt_data)
        
        # Guardar archivos
        pd.DataFrame(titulos_alt_data).to_csv(titulos_alt_file, index=False)
        pd.DataFrame([{'codigo': reg} for reg in regiones_set]).to_csv(regiones_file, index=False)
        pd.DataFrame([{'codigo': idi} for idi in idiomas_set]).to_csv(idiomas_file, index=False)
        pd.DataFrame([{'nombre': tipo} for tipo in tipos_set]).to_csv(tipos_titulo_file, index=False)
        pd.DataFrame([{'nombre': attr} for attr in atributos_set]).to_csv(atributos_file, index=False)
        
        logger.info(f"title.akas procesado: {len(titulos_alt_data)} títulos alternativos")
    
    def process_title_crew(self):
        """Procesa title.crew.tsv para directores y escritores"""
        logger.info("Procesando title.crew.tsv...")
        
        input_file = self.input_folder / "title.crew.tsv" / "title.crew.tsv"
        if not input_file.exists():
            logger.error(f"Archivo no encontrado: {input_file}")
            return
        
        directores_data = []
        escritores_data = []
        producciones_data = []
        
        chunk_num = 0
        for chunk in pd.read_csv(input_file, sep='\t', chunksize=self.chunk_size, dtype=str):
            chunk_num += 1
            logger.info(f"Procesando chunk {chunk_num} de title.crew...")
            
            for _, row in chunk.iterrows():
                tconst = self.clean_value(row['tconst'])
                if not tconst:
                    continue
                
                producciones_data.append({'tconst': tconst})
                
                # Directores
                directores_raw = self.clean_value(row['directors'])
                if directores_raw:
                    directores_lista = self.split_list_field(directores_raw)
                    for director in directores_lista:
                        directores_data.append({
                            'tconst': tconst,
                            'nconst': director
                        })
                
                # Escritores
                escritores_raw = self.clean_value(row['writers'])
                if escritores_raw:
                    escritores_lista = self.split_list_field(escritores_raw)
                    for escritor in escritores_lista:
                        escritores_data.append({
                            'tconst': tconst,
                            'nconst': escritor
                        })
        
        # Guardar archivos
        pd.DataFrame(producciones_data).to_csv(self.output_folder / "producciones.csv", index=False)
        pd.DataFrame(directores_data).to_csv(self.output_folder / "directores.csv", index=False)
        pd.DataFrame(escritores_data).to_csv(self.output_folder / "escritores.csv", index=False)
        
        logger.info(f"title.crew procesado: {len(directores_data)} directores, {len(escritores_data)} escritores")
    
    def process_title_episode(self):
        """Procesa title.episode.tsv para episodios"""
        logger.info("Procesando title.episode.tsv...")
        
        input_file = self.input_folder / "title.episode.tsv" / "title.episode.tsv"
        if not input_file.exists():
            logger.error(f"Archivo no encontrado: {input_file}")
            return
        
        episodios_data = []
        
        chunk_num = 0
        for chunk in pd.read_csv(input_file, sep='\t', chunksize=self.chunk_size, dtype=str):
            chunk_num += 1
            logger.info(f"Procesando chunk {chunk_num} de title.episode...")
            
            for _, row in chunk.iterrows():
                tconst = self.clean_value(row['tconst'])
                if not tconst:
                    continue
                
                episodio_data = {
                    'tconst': tconst,
                    'id_titulo': self.clean_value(row['parentTconst']),
                    'temporada': self.clean_value(row['seasonNumber']),
                    'episodio': self.clean_value(row['episodeNumber'])
                }
                episodios_data.append(episodio_data)
        
        pd.DataFrame(episodios_data).to_csv(self.output_folder / "episodios.csv", index=False)
        logger.info(f"title.episode procesado: {len(episodios_data)} episodios")
    
    def process_title_principals(self):
        """Procesa title.principals.tsv para reparto principal"""
        logger.info("Procesando title.principals.tsv...")
        
        input_file = self.input_folder / "title.principals.tsv" / "title.principals.tsv"
        if not input_file.exists():
            logger.error(f"Archivo no encontrado: {input_file}")
            return
        
        reparto_data = []
        
        chunk_num = 0
        for chunk in pd.read_csv(input_file, sep='\t', chunksize=self.chunk_size, dtype=str):
            chunk_num += 1
            logger.info(f"Procesando chunk {chunk_num} de title.principals...")
            
            for _, row in chunk.iterrows():
                tconst = self.clean_value(row['tconst'])
                if not tconst:
                    continue
                
                reparto_item = {
                    'tconst': tconst,
                    'relevancia': self.clean_value(row['ordering']),
                    'nconst': self.clean_value(row['nconst']),
                    'categoria_profesion': self.clean_value(row['category']),
                    'rol': self.clean_value(row['job']),
                    'personaje': self.clean_value(row['characters'])
                }
                reparto_data.append(reparto_item)
        
        pd.DataFrame(reparto_data).to_csv(self.output_folder / "reparto.csv", index=False)
        logger.info(f"title.principals procesado: {len(reparto_data)} registros de reparto")
    
    def process_title_ratings(self):
        """Procesa title.ratings.tsv para puntuaciones"""
        logger.info("Procesando title.ratings.tsv...")
        
        input_file = self.input_folder / "title.ratings.tsv" / "title.ratings.tsv"
        if not input_file.exists():
            logger.error(f"Archivo no encontrado: {input_file}")
            return
        
        puntuaciones_data = []
        
        chunk_num = 0
        for chunk in pd.read_csv(input_file, sep='\t', chunksize=self.chunk_size, dtype=str):
            chunk_num += 1
            logger.info(f"Procesando chunk {chunk_num} de title.ratings...")
            
            for _, row in chunk.iterrows():
                tconst = self.clean_value(row['tconst'])
                if not tconst:
                    continue
                
                puntuacion_data = {
                    'tconst': tconst,
                    'promedio': self.clean_value(row['averageRating']),
                    'votos': self.clean_value(row['numVotes'])
                }
                puntuaciones_data.append(puntuacion_data)
        
        pd.DataFrame(puntuaciones_data).to_csv(self.output_folder / "puntuaciones.csv", index=False)
        logger.info(f"title.ratings procesado: {len(puntuaciones_data)} puntuaciones")
    
    def process_all_files(self):
        """Procesa todos los archivos"""
        logger.info("Iniciando procesamiento de todos los archivos IMDB...")
        
        try:
            self.process_name_basics()
            self.process_title_basics()
            self.process_title_akas()
            self.process_title_crew()
            self.process_title_episode()
            self.process_title_principals()
            self.process_title_ratings()
            
            logger.info("¡Procesamiento completado exitosamente!")
            logger.info(f"Archivos generados en la carpeta: {self.output_folder}")
            
        except Exception as e:
            logger.error(f"Error durante el procesamiento: {str(e)}")
            raise

if __name__ == "__main__":
    # Crear instancia del separador
    separator = IMDBDataSeparator()
    
    # Procesar todos los archivos
    separator.process_all_files()
