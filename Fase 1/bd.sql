-- Crear el esquema
CREATE SCHEMA IF NOT EXISTS imdb_schema;

SET search_path TO imdb_schema, public;
-- ================================
-- TABLAS INDEPENDIENTES (SIN FK)
-- ================================

-- Tabla Categoria
CREATE TABLE IF NOT EXISTS Categoria (
    id_categoria SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE
);

-- Tabla Genero
CREATE TABLE IF NOT EXISTS Genero (
    id_genero SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE
);

-- Tabla Region
CREATE TABLE IF NOT EXISTS Region (
    id_region SERIAL PRIMARY KEY,
    codigo VARCHAR(5) UNIQUE
);

-- Tabla Idioma
CREATE TABLE IF NOT EXISTS Idioma (
    id_idioma SERIAL PRIMARY KEY,
    codigo VARCHAR(5) UNIQUE
);

-- Tabla Tipo_Titulo
CREATE TABLE IF NOT EXISTS Tipo_Titulo (
    id_tipo SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE
);

-- Tabla Atributo
CREATE TABLE IF NOT EXISTS Atributo (
    id_atributo SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE
);

-- Tabla Profesion
CREATE TABLE IF NOT EXISTS Profesion (
    id_profesion SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE
);

-- Tabla Persona 
CREATE TABLE IF NOT EXISTS Persona (
    nconst VARCHAR(20) PRIMARY KEY,
    nombre_artistico TEXT,
    anio_nacimiento INTEGER,
    anio_fallecimiento INTEGER
);

-- ================================
-- TABLAS PRINCIPALES CON FK
-- ================================

-- Tabla Titulo 
CREATE TABLE IF NOT EXISTS Titulo (
    tconst VARCHAR(20) PRIMARY KEY,
    id_categoria INTEGER REFERENCES Categoria(id_categoria),
    titulo_popular TEXT,
    titulo_original TEXT,
    es_contenido_adulto BOOLEAN DEFAULT FALSE,
    anio_lanzamiento INTEGER,
    anio_finalizacion INTEGER,
    duracion_minutos INTEGER
);

-- Tabla Titulo_Alternativo
CREATE TABLE IF NOT EXISTS Titulo_Alternativo (
    id_titulo_alternativo SERIAL PRIMARY KEY,
    tconst VARCHAR(20) REFERENCES Titulo(tconst) ON DELETE CASCADE,
    orden INTEGER,
    nombre_titulo VARCHAR(255),
    id_region INTEGER REFERENCES Region(id_region),
    id_idioma INTEGER REFERENCES Idioma(id_idioma),
    es_original BOOLEAN DEFAULT FALSE,
    CONSTRAINT uk_titulo_orden UNIQUE(tconst, orden)
);

-- Tabla Produccion
CREATE TABLE IF NOT EXISTS Produccion (
    id_produccion INTEGER PRIMARY KEY,
    tconst VARCHAR(20) UNIQUE REFERENCES Titulo(tconst) ON DELETE CASCADE
);

-- Tabla Episodio 
CREATE TABLE IF NOT EXISTS Episodio (
    tconst VARCHAR(20) PRIMARY KEY REFERENCES Titulo(tconst) ON DELETE CASCADE,
    id_titulo VARCHAR(20) REFERENCES Titulo(tconst),
    temporada INTEGER,
    episodio INTEGER
);

-- Tabla Reparto 
CREATE TABLE IF NOT EXISTS Reparto (
    id_reparto INTEGER PRIMARY KEY,
    tconst VARCHAR(20) REFERENCES Titulo(tconst) ON DELETE CASCADE,
    relevancia INTEGER,
    nconst VARCHAR(20) REFERENCES Persona(nconst),
    id_profesion INTEGER REFERENCES Profesion(id_profesion),
    rol TEXT,
    personaje TEXT
);
-- Tabla Puntuacion 
CREATE TABLE IF NOT EXISTS Puntuacion (
    id_puntuacion SERIAL PRIMARY KEY,
    tconst VARCHAR(20) UNIQUE REFERENCES Titulo(tconst) ON DELETE CASCADE,
    promedio DECIMAL(3,1),
    votos INTEGER
);

-- ================================
-- TABLAS DE RELACIÓN (MUCHOS A MUCHOS)
-- ================================

-- Tabla Genero_Titulo
CREATE TABLE IF NOT EXISTS Genero_Titulo (
    id_genero_titulo INTEGER PRIMARY KEY,
    tconst VARCHAR(20) REFERENCES Titulo(tconst) ON DELETE CASCADE,
    id_genero INTEGER REFERENCES Genero(id_genero)
);

-- Tabla Titulo_Alternativo_Atributo
CREATE TABLE IF NOT EXISTS Titulo_Alternativo_Atributo (
    id_titulo_alternativo_atributo SERIAL PRIMARY KEY,
    id_titulo_alternativo INTEGER REFERENCES Titulo_Alternativo(id_titulo_alternativo) ON DELETE CASCADE,
    id_atributo INTEGER REFERENCES Atributo(id_atributo),
    CONSTRAINT uk_alt_titulo_atributo UNIQUE(id_titulo_alternativo, id_atributo)
);

-- Tabla Titulo_Alternativo_Tipo
CREATE TABLE IF NOT EXISTS Titulo_Alternativo_Tipo (
    id_titulo_alternativo_tipo SERIAL PRIMARY KEY,
    id_titulo_alternativo INTEGER REFERENCES Titulo_Alternativo(id_titulo_alternativo) ON DELETE CASCADE,
    id_tipo INTEGER REFERENCES Tipo_Titulo(id_tipo),
    CONSTRAINT uk_alt_titulo_tipo UNIQUE(id_titulo_alternativo, id_tipo)
);

-- Tabla Produccion_Escritor
CREATE TABLE IF NOT EXISTS Produccion_Escritor (
    id_produccion_escritor INTEGER PRIMARY KEY,
    id_persona VARCHAR(20) REFERENCES Persona(nconst),
    id_produccion INTEGER REFERENCES Produccion(id_produccion) ON DELETE CASCADE
);

-- Tabla Produccion_Director
CREATE TABLE IF NOT EXISTS Produccion_Director (
    id_produccion_director INTEGER PRIMARY KEY,
    id_persona VARCHAR(20) REFERENCES Persona(nconst),
    id_produccion INTEGER REFERENCES Produccion(id_produccion) ON DELETE CASCADE
);

-- Tabla Profesion_Persona_Top
CREATE TABLE IF NOT EXISTS Profesion_Persona_Top (
    id_profesion_persona INTEGER PRIMARY KEY,
    nconst VARCHAR(20) REFERENCES Persona(nconst) ON DELETE CASCADE,
    id_profesion INTEGER REFERENCES Profesion(id_profesion)
);
-- Tabla Pelicula_Persona_Top
CREATE TABLE IF NOT EXISTS Pelicula_Persona_Top (
    id_titulo_persona INTEGER PRIMARY KEY,
    nconst VARCHAR(20) REFERENCES Persona(nconst) ON DELETE CASCADE,
    tconst VARCHAR(20) REFERENCES Titulo(tconst)
);

-- ================================
-- ÍNDICES PARA OPTIMIZACIÓN
-- ================================

-- Índices en campos de búsqueda frecuente
CREATE INDEX IF NOT EXISTS idx_titulo_categoria ON Titulo(id_categoria) WHERE id_categoria IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_titulo_anio ON Titulo(anio_lanzamiento) WHERE anio_lanzamiento IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_titulo_adulto ON Titulo(es_contenido_adulto);
CREATE INDEX IF NOT EXISTS idx_titulo_popular ON Titulo(titulo_popular) WHERE titulo_popular IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_persona_nombre ON Persona(nombre_artistico) WHERE nombre_artistico IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_persona_nacimiento ON Persona(anio_nacimiento) WHERE anio_nacimiento IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_reparto_titulo ON Reparto(tconst) WHERE tconst IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_reparto_persona ON Reparto(nconst) WHERE nconst IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_reparto_profesion ON Reparto(id_profesion) WHERE id_profesion IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_reparto_relevancia ON Reparto(relevancia) WHERE relevancia IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_genero_titulo_genero ON Genero_Titulo(id_genero) WHERE id_genero IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_genero_titulo_titulo ON Genero_Titulo(tconst) WHERE tconst IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_episodio_serie ON Episodio(id_titulo) WHERE id_titulo IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_episodio_temporada ON Episodio(temporada) WHERE temporada IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_puntuacion_promedio ON Puntuacion(promedio DESC) WHERE promedio IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_puntuacion_votos ON Puntuacion(votos DESC) WHERE votos IS NOT NULL;

-- Mensaje de confirmación
\echo 'Schema imdb_schema y todas las tablas creadas exitosamente.'