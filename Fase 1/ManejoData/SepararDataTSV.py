import csv
import os
from collections import defaultdict
import json
import gc  

def safe_value(value):
    """Convierte \\N en None/NULL para PostgreSQL"""
    return None if value == '\\N' else value

def parse_list(value):
    """Parsea listas en formato JSON de los TSV"""
    if value == '\\N' or not value:
        return []
    try:
        return json.loads(value) if value.startswith('[') else [value]
    except:
        return [value]

def parse_comma_separated(value):
    """Parsea valores separados por comas"""
    if value == '\\N' or not value:
        return []
    return [v.strip() for v in value.split(',')]

class CSVWriter:
    """Clase para manejar escritura incremental a CSV"""
    def __init__(self, filepath, fieldnames):
        self.filepath = filepath
        self.fieldnames = fieldnames
        self.file = open(filepath, 'w', newline='', encoding='utf-8')
        self.writer = csv.DictWriter(self.file, fieldnames=fieldnames)
        self.writer.writeheader()
        self.count = 0
    
    def write_row(self, record):
        """Escribe una fila limpiando valores None"""
        clean_record = {k: ('' if v is None else v) for k, v in record.items()}
        self.writer.writerow(clean_record)
        self.count += 1
        # Flush cada 10000 registros para liberar buffer
        if self.count % 10000 == 0:
            self.file.flush()
    
    def close(self):
        """Cierra el archivo y devuelve el conteo final"""
        self.file.close()
        return self.count

# Directorios
base_dir = os.path.dirname(os.path.abspath(__file__))
datos_dir = os.path.join(os.path.dirname(base_dir), 'Datos')
output_dir = os.path.join(base_dir, 'csv_output')

# Crear directorio de salida
os.makedirs(output_dir, exist_ok=True)

# Diccionarios para almacenar IDs únicos (estos son pequeños, no causarán problemas de memoria)
categorias = {}
generos = {}
regiones = {}
idiomas = {}
tipos_titulo = {}
atributos = {}
profesiones = {}

# Sets para validación (solo almacenan IDs, no registros completos)
personas = set()
titulos = set()

# Contadores para IDs auto-incrementables
categoria_id = 1
genero_id = 1
region_id = 1
idioma_id = 1
tipo_titulo_id = 1
atributo_id = 1
profesion_id = 1
titulo_alternativo_id = 1
produccion_id = 1
reparto_id = 1
puntuacion_id = 1

# Abrir archivos CSV para escritura incremental
print("Inicializando escritores CSV...")

writers = {
    'titulo': CSVWriter(os.path.join(output_dir, 'titulo.csv'),
                       ['tconst', 'id_categoria', 'titulo_popular', 'titulo_original', 
                        'es_contenido_adulto', 'anio_lanzamiento', 'anio_finalizacion', 'duracion_minutos']),
    'titulo_alternativo': CSVWriter(os.path.join(output_dir, 'titulo_alternativo.csv'),
                                   ['id_titulo_alternativo', 'tconst', 'orden', 'nombre_titulo', 
                                    'id_region', 'id_idioma', 'es_original']),
    'produccion': CSVWriter(os.path.join(output_dir, 'produccion.csv'),
                           ['id_produccion', 'tconst']),
    'episodio': CSVWriter(os.path.join(output_dir, 'episodio.csv'),
                         ['tconst', 'id_titulo', 'temporada', 'episodio']),
    'reparto': CSVWriter(os.path.join(output_dir, 'reparto.csv'),
                        ['id_reparto', 'tconst', 'relevancia', 'nconst', 'id_profesion', 'rol', 'personaje']),
    'puntuacion': CSVWriter(os.path.join(output_dir, 'puntuacion.csv'),
                           ['id_puntuacion', 'tconst', 'promedio', 'votos']),
    'genero_titulo': CSVWriter(os.path.join(output_dir, 'genero_titulo.csv'),
                              ['id_genero_titulo', 'tconst', 'id_genero']),
    'titulo_alternativo_atributo': CSVWriter(os.path.join(output_dir, 'titulo_alternativo_atributo.csv'),
                                            ['id_titulo_alternativo_atributo', 'id_titulo_alternativo', 'id_atributo']),
    'titulo_alternativo_tipo': CSVWriter(os.path.join(output_dir, 'titulo_alternativo_tipo.csv'),
                                        ['id_titulo_alternativo_tipo', 'id_titulo_alternativo', 'id_tipo']),
    'produccion_escritor': CSVWriter(os.path.join(output_dir, 'produccion_escritor.csv'),
                                    ['id_produccion_escritor', 'id_persona', 'id_produccion']),
    'produccion_director': CSVWriter(os.path.join(output_dir, 'produccion_director.csv'),
                                    ['id_produccion_director', 'id_persona', 'id_produccion']),
    'profesion_persona_top': CSVWriter(os.path.join(output_dir, 'profesion_persona_top.csv'),
                                      ['id_profesion_persona', 'nconst', 'id_profesion']),
    'pelicula_persona_top': CSVWriter(os.path.join(output_dir, 'pelicula_persona_top.csv'),
                                     ['id_titulo_persona', 'nconst', 'tconst']),
    'persona': CSVWriter(os.path.join(output_dir, 'persona.csv'),
                        ['nconst', 'nombre_artistico', 'anio_nacimiento', 'anio_fallecimiento']),
}

# Contadores para las relaciones
genero_titulo_id = 1
titulo_alternativo_atributo_id = 1
titulo_alternativo_tipo_id = 1
produccion_escritor_id = 1
produccion_director_id = 1
profesion_persona_id = 1
pelicula_persona_id = 1

print("Procesando archivos TSV...")

# 1. Procesar title.basics.tsv
print("Procesando title.basics.tsv...")
title_basics_path = os.path.join(datos_dir, 'title.basics.tsv', 'title.basics.tsv')
if os.path.exists(title_basics_path):
    with open(title_basics_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        batch_count = 0
        
        for row in reader:
            tconst = row['tconst']
            titulos.add(tconst)
            
            # Mapear titleType a categoria
            title_type = row['titleType']
            if title_type not in categorias:
                categorias[title_type] = categoria_id
                categoria_id += 1
            
            # Procesar géneros
            genres_list = parse_comma_separated(row['genres'])
            for genre in genres_list:
                if genre and genre not in generos:
                    generos[genre] = genero_id
                    genero_id += 1
            
            # Escribir registro de título directamente
            writers['titulo'].write_row({
                'tconst': tconst,
                'id_categoria': categorias[title_type],
                'titulo_popular': safe_value(row['primaryTitle']),
                'titulo_original': safe_value(row['originalTitle']),
                'es_contenido_adulto': '1' if row['isAdult'] == '1' else '0',
                'anio_lanzamiento': safe_value(row['startYear']),
                'anio_finalizacion': safe_value(row['endYear']),
                'duracion_minutos': safe_value(row['runtimeMinutes'])
            })
            
            # Escribir relaciones género-título directamente
            for genre in genres_list:
                if genre:
                    writers['genero_titulo'].write_row({
                        'id_genero_titulo': genero_titulo_id,
                        'tconst': tconst,
                        'id_genero': generos[genre]
                    })
                    genero_titulo_id += 1
            
            batch_count += 1
            if batch_count % 100000 == 0:
                print(f"  Procesados {batch_count} títulos...")
                gc.collect()  # Forzar recolección de basura

# 2. Procesar name.basics.tsv
print("Procesando name.basics.tsv...")
name_basics_path = os.path.join(datos_dir, 'name.basics.tsv', 'name.basics.tsv')
if os.path.exists(name_basics_path):
    with open(name_basics_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        batch_count = 0
        
        for row in reader:
            nconst = row['nconst']
            personas.add(nconst)
            
            # Procesar profesiones
            professions_list = parse_comma_separated(row['primaryProfession'])
            for prof in professions_list:
                if prof and prof not in profesiones:
                    profesiones[prof] = profesion_id
                    profesion_id += 1
            
            # Escribir registro de persona directamente
            writers['persona'].write_row({
                'nconst': nconst,
                'nombre_artistico': safe_value(row['primaryName']),
                'anio_nacimiento': safe_value(row['birthYear']),
                'anio_fallecimiento': safe_value(row['deathYear'])
            })
            
            # Escribir profesiones principales directamente
            for prof in professions_list:
                if prof:
                    writers['profesion_persona_top'].write_row({
                        'id_profesion_persona': profesion_persona_id,
                        'nconst': nconst,
                        'id_profesion': profesiones[prof]
                    })
                    profesion_persona_id += 1
            
            # Escribir títulos conocidos directamente
            known_titles = parse_comma_separated(row['knownForTitles'])
            for title in known_titles:
                if title and title != '\\N':
                    writers['pelicula_persona_top'].write_row({
                        'id_titulo_persona': pelicula_persona_id,
                        'nconst': nconst,
                        'tconst': title
                    })
                    pelicula_persona_id += 1
            
            batch_count += 1
            if batch_count % 100000 == 0:
                print(f"  Procesadas {batch_count} personas...")
                gc.collect()

# 3. Procesar title.akas.tsv (el archivo más grande)
print("Procesando title.akas.tsv...")
title_akas_path = os.path.join(datos_dir, 'title.akas.tsv', 'title.akas.tsv')
if os.path.exists(title_akas_path):
    # Aumentar el límite de tamaño de campo para CSV
    import sys
    old_limit = csv.field_size_limit()
    csv.field_size_limit(sys.maxsize)
    
    try:
        with open(title_akas_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            batch_count = 0
            
            for row in reader:
                try:
                    tconst = row['titleId']
                    
                    # Procesar región
                    region = safe_value(row['region'])
                    if region and region not in regiones:
                        regiones[region] = region_id
                        region_id += 1
                    
                    # Procesar idioma
                    language = safe_value(row['language'])
                    if language and language not in idiomas:
                        idiomas[language] = idioma_id
                        idioma_id += 1
                    
                    # Procesar tipos
                    types_list = parse_comma_separated(row['types']) if row['types'] else []
                    for type_name in types_list:
                        if type_name and type_name not in tipos_titulo:
                            tipos_titulo[type_name] = tipo_titulo_id
                            tipo_titulo_id += 1
                    
                    # Procesar atributos
                    attrs_list = parse_comma_separated(row['attributes']) if row['attributes'] else []
                    for attr in attrs_list:
                        if attr and attr not in atributos:
                            atributos[attr] = atributo_id
                            atributo_id += 1
                    
                    # Truncar título muy largo para evitar problemas
                    titulo_truncado = safe_value(row['title'])
                    if titulo_truncado and len(titulo_truncado) > 1000:
                        titulo_truncado = titulo_truncado[:1000] + "..."
                    
                    # Escribir registro de título alternativo directamente
                    current_alt_id = titulo_alternativo_id
                    writers['titulo_alternativo'].write_row({
                        'id_titulo_alternativo': current_alt_id,
                        'tconst': tconst,
                        'orden': safe_value(row['ordering']),
                        'nombre_titulo': titulo_truncado,
                        'id_region': regiones.get(region) if region else None,
                        'id_idioma': idiomas.get(language) if language else None,
                        'es_original': '1' if row['isOriginalTitle'] == '1' else '0'
                    })
                    titulo_alternativo_id += 1
                    
                    # Escribir relaciones con tipos directamente
                    for type_name in types_list:
                        if type_name:
                            writers['titulo_alternativo_tipo'].write_row({
                                'id_titulo_alternativo_tipo': titulo_alternativo_tipo_id,
                                'id_titulo_alternativo': current_alt_id,
                                'id_tipo': tipos_titulo[type_name]
                            })
                            titulo_alternativo_tipo_id += 1
                    
                    # Escribir relaciones con atributos directamente
                    for attr in attrs_list:
                        if attr:
                            writers['titulo_alternativo_atributo'].write_row({
                                'id_titulo_alternativo_atributo': titulo_alternativo_atributo_id,
                                'id_titulo_alternativo': current_alt_id,
                                'id_atributo': atributos[attr]
                            })
                            titulo_alternativo_atributo_id += 1
                    
                    batch_count += 1
                    if batch_count % 100000 == 0:
                        print(f"  Procesados {batch_count} títulos alternativos...")
                        gc.collect()
                        
                except Exception as e:
                    print(f"  Error procesando fila {batch_count + 1}: {str(e)[:100]}... - Continuando...")
                    continue
    
    finally:
        # Restaurar el límite original
        csv.field_size_limit(old_limit)

# 4. Procesar title.crew.tsv
print("Procesando title.crew.tsv...")
title_crew_path = os.path.join(datos_dir, 'title.crew.tsv', 'title.crew.tsv')
if os.path.exists(title_crew_path):
    with open(title_crew_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        batch_count = 0
        
        for row in reader:
            tconst = row['tconst']
            if tconst in titulos:
                # Escribir registro de producción directamente
                current_prod_id = produccion_id
                writers['produccion'].write_row({
                    'id_produccion': current_prod_id,
                    'tconst': tconst
                })
                produccion_id += 1
                
                # Procesar y escribir directores directamente
                directors = parse_comma_separated(row['directors'])
                for director in directors:
                    if director and director != '\\N':
                        writers['produccion_director'].write_row({
                            'id_produccion_director': produccion_director_id,
                            'id_persona': director,
                            'id_produccion': current_prod_id
                        })
                        produccion_director_id += 1
                
                # Procesar y escribir escritores directamente
                writers_list = parse_comma_separated(row['writers'])
                for writer in writers_list:
                    if writer and writer != '\\N':
                        writers['produccion_escritor'].write_row({
                            'id_produccion_escritor': produccion_escritor_id,
                            'id_persona': writer,
                            'id_produccion': current_prod_id
                        })
                        produccion_escritor_id += 1
            
            batch_count += 1
            if batch_count % 100000 == 0:
                print(f"  Procesadas {batch_count} producciones...")
                gc.collect()

# 5. Procesar title.episode.tsv
print("Procesando title.episode.tsv...")
title_episode_path = os.path.join(datos_dir, 'title.episode.tsv', 'title.episode.tsv')
if os.path.exists(title_episode_path):
    with open(title_episode_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        batch_count = 0
        
        for row in reader:
            writers['episodio'].write_row({
                'tconst': row['tconst'],
                'id_titulo': safe_value(row['parentTconst']),
                'temporada': safe_value(row['seasonNumber']),
                'episodio': safe_value(row['episodeNumber'])
            })
            
            batch_count += 1
            if batch_count % 100000 == 0:
                print(f"  Procesados {batch_count} episodios...")
                gc.collect()

# 6. Procesar title.principals.tsv
print("Procesando title.principals.tsv...")
title_principals_path = os.path.join(datos_dir, 'title.principals.tsv', 'title.principals.tsv')
if os.path.exists(title_principals_path):
    with open(title_principals_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        batch_count = 0
        
        for row in reader:
            # Procesar categoría/profesión
            category = safe_value(row['category'])
            if category and category not in profesiones:
                profesiones[category] = profesion_id
                profesion_id += 1
            
            # Procesar personajes
            characters = safe_value(row['characters'])
            if characters and characters.startswith('['):
                try:
                    char_list = json.loads(characters)
                    characters = ', '.join(char_list) if char_list else None
                except:
                    pass
            
            writers['reparto'].write_row({
                'id_reparto': reparto_id,
                'tconst': row['tconst'],
                'relevancia': safe_value(row['ordering']),
                'nconst': safe_value(row['nconst']),
                'id_profesion': profesiones.get(category) if category else None,
                'rol': safe_value(row['job']),
                'personaje': characters
            })
            reparto_id += 1
            
            batch_count += 1
            if batch_count % 100000 == 0:
                print(f"  Procesados {batch_count} registros de reparto...")
                gc.collect()

# 7. Procesar title.ratings.tsv
print("Procesando title.ratings.tsv...")
title_ratings_path = os.path.join(datos_dir, 'title.ratings.tsv', 'title.ratings.tsv')
if os.path.exists(title_ratings_path):
    with open(title_ratings_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        batch_count = 0
        
        for row in reader:
            writers['puntuacion'].write_row({
                'id_puntuacion': puntuacion_id,
                'tconst': row['tconst'],
                'promedio': safe_value(row['averageRating']),
                'votos': safe_value(row['numVotes'])
            })
            puntuacion_id += 1
            
            batch_count += 1
            if batch_count % 100000 == 0:
                print(f"  Procesadas {batch_count} puntuaciones...")
                gc.collect()

# Cerrar todos los writers y obtener conteos
print("\nCerrando archivos CSV...")
counts = {}
for name, writer in writers.items():
    counts[name] = writer.close()

# Escribir tablas de catálogo (estas son pequeñas, podemos hacerlas al final)
print("\nEscribiendo tablas de catálogo...")

def write_catalog_csv(filename, data_dict, fieldnames):
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for key, value in data_dict.items():
            if fieldnames[1] == 'nombre':
                writer.writerow({fieldnames[0]: value, fieldnames[1]: key})
            else:
                writer.writerow({fieldnames[0]: value, fieldnames[1]: key})
    print(f"  - Creado: {filename} ({len(data_dict)} registros)")

write_catalog_csv('categoria.csv', categorias, ['id_categoria', 'nombre'])
write_catalog_csv('genero.csv', generos, ['id_genero', 'nombre'])
write_catalog_csv('region.csv', regiones, ['id_region', 'codigo'])
write_catalog_csv('idioma.csv', idiomas, ['id_idioma', 'codigo'])
write_catalog_csv('tipo_titulo.csv', tipos_titulo, ['id_tipo', 'nombre'])
write_catalog_csv('atributo.csv', atributos, ['id_atributo', 'nombre'])
write_catalog_csv('profesion.csv', profesiones, ['id_profesion', 'nombre'])

print(f"\nProceso completado. {len(os.listdir(output_dir))} archivos CSV creados en: {output_dir}")
print("\nResumen de datos procesados:")
for name, count in counts.items():
    print(f"  - {name}: {count} registros")
print(f"  - Categorías: {len(categorias)}")
print(f"  - Géneros: {len(generos)}")
print(f"  - Profesiones: {len(profesiones)}")
print(f"  - Regiones: {len(regiones)}")
print(f"  - Idiomas: {len(idiomas)}")

with open(import_script_path, 'w', encoding='utf-8') as f:
    f.write(sql_import_script)

print(f"\nScript SQL de importación creado: {import_script_path}")
print("\nPara importar los datos en PostgreSQL:")
print("1. Asegúrate de que tu base de datos esté creada con el esquema")
print("2. Ajusta las rutas en el archivo import_data.sql si es necesario")
print("3. Ejecuta: psql -d tu_base_datos -f csv_output/import_data.sql")

# Liberar memoria final
gc.collect()
print("\nMemoria liberada. Proceso completado exitosamente.")