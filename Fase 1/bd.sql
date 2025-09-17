
-- Crear el esquema
CREATE SCHEMA IF NOT EXISTS imdb_schema;

-- Establecer el esquema por defecto para las tablas
SET search_path TO imdb_schema, public;
-- ================================
-- TABLAS INDEPENDIENTES (SIN FK)
-- ================================

-- Tabla Categoria
CREATE TABLE Categoria (
    id_categoria SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE
);

-- Tabla Genero
CREATE TABLE Genero (
    id_genero SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE
);

-- Tabla Region
CREATE TABLE Region (
    id_region SERIAL PRIMARY KEY,
    codigo VARCHAR(5) UNIQUE
);

-- Tabla Idioma
CREATE TABLE Idioma (
    id_idioma SERIAL PRIMARY KEY,
    codigo VARCHAR(5) UNIQUE
);

-- Tabla Tipo_Titulo
CREATE TABLE Tipo_Titulo (
    id_tipo SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE
);

-- Tabla Atributo
CREATE TABLE Atributo (
    id_atributo SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE
);

-- Tabla Profesion
CREATE TABLE Profesion (
    id_profesion SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE
);

-- Tabla Persona
CREATE TABLE Persona (
    nconst VARCHAR(20) PRIMARY KEY,
    nombre_artistico TEXT,
    anio_nacimiento INTEGER,
    anio_fallecimiento INTEGER,
    CONSTRAINT chk_anios CHECK (anio_fallecimiento IS NULL OR anio_nacimiento IS NULL OR anio_fallecimiento >= anio_nacimiento)
);

-- ================================
-- TABLAS PRINCIPALES CON FK
-- ================================

-- Tabla Titulo
CREATE TABLE Titulo (
    tconst VARCHAR(20) PRIMARY KEY,
    id_categoria INTEGER REFERENCES Categoria(id_categoria),
    titulo_popular TEXT,
    titulo_original TEXT,
    es_contenido_adulto BOOLEAN DEFAULT FALSE,
    anio_lanzamiento INTEGER,
    anio_finalizacion INTEGER,
    duracion_minutos INTEGER,
    CONSTRAINT chk_anios_titulo CHECK (anio_finalizacion IS NULL OR anio_lanzamiento IS NULL OR anio_finalizacion >= anio_lanzamiento),
    CONSTRAINT chk_duracion CHECK (duracion_minutos IS NULL OR duracion_minutos > 0)
);

-- Tabla Titulo_Alternativo
CREATE TABLE Titulo_Alternativo (
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
CREATE TABLE Produccion (
    id_produccion SERIAL PRIMARY KEY,
    tconst VARCHAR(20) UNIQUE REFERENCES Titulo(tconst) ON DELETE CASCADE
);

-- Tabla Episodio
CREATE TABLE Episodio (
    tconst VARCHAR(20) PRIMARY KEY REFERENCES Titulo(tconst) ON DELETE CASCADE,
    id_titulo VARCHAR(20) REFERENCES Titulo(tconst),
    temporada INTEGER,
    episodio INTEGER,
    CONSTRAINT chk_temporada CHECK (temporada IS NULL OR temporada > 0),
    CONSTRAINT chk_episodio CHECK (episodio IS NULL OR episodio > 0)
);

-- Tabla Reparto
CREATE TABLE Reparto (
    id_reparto SERIAL PRIMARY KEY,
    tconst VARCHAR(20) REFERENCES Titulo(tconst) ON DELETE CASCADE,
    relevancia INTEGER,
    nconst VARCHAR(20) REFERENCES Persona(nconst),
    id_profesion INTEGER REFERENCES Profesion(id_profesion),
    rol TEXT,
    personaje TEXT,
    CONSTRAINT uk_reparto_orden UNIQUE(tconst, relevancia),
    CONSTRAINT chk_relevancia CHECK (relevancia IS NULL OR relevancia > 0)
);

-- Tabla Puntuacion
CREATE TABLE Puntuacion (
    id_puntuacion SERIAL PRIMARY KEY,
    tconst VARCHAR(20) UNIQUE REFERENCES Titulo(tconst) ON DELETE CASCADE,
    promedio DECIMAL(3,1),
    votos INTEGER,
    CONSTRAINT chk_promedio CHECK (promedio IS NULL OR (promedio >= 1.0 AND promedio <= 10.0)),
    CONSTRAINT chk_votos CHECK (votos IS NULL OR votos > 0)
);

-- ================================
-- TABLAS DE RELACIÓN (MUCHOS A MUCHOS)
-- ================================

-- Tabla Genero_Titulo
CREATE TABLE Genero_Titulo (
    id_genero_titulo SERIAL PRIMARY KEY,
    tconst VARCHAR(20) REFERENCES Titulo(tconst) ON DELETE CASCADE,
    id_genero INTEGER REFERENCES Genero(id_genero),
    CONSTRAINT uk_genero_titulo UNIQUE(tconst, id_genero)
);

-- Tabla Titulo_Alternativo_Atributo
CREATE TABLE Titulo_Alternativo_Atributo (
    id_titulo_alternativo_atributo SERIAL PRIMARY KEY,
    id_titulo_alternativo INTEGER REFERENCES Titulo_Alternativo(id_titulo_alternativo) ON DELETE CASCADE,
    id_atributo INTEGER REFERENCES Atributo(id_atributo),
    CONSTRAINT uk_alt_titulo_atributo UNIQUE(id_titulo_alternativo, id_atributo)
);

-- Tabla Titulo_Alternativo_Tipo
CREATE TABLE Titulo_Alternativo_Tipo (
    id_titulo_alternativo_tipo SERIAL PRIMARY KEY,
    id_titulo_alternativo INTEGER REFERENCES Titulo_Alternativo(id_titulo_alternativo) ON DELETE CASCADE,
    id_tipo INTEGER REFERENCES Tipo_Titulo(id_tipo),
    CONSTRAINT uk_alt_titulo_tipo UNIQUE(id_titulo_alternativo, id_tipo)
);

-- Tabla Produccion_Escritor
CREATE TABLE Produccion_Escritor (
    id_produccion_escritor SERIAL PRIMARY KEY,
    id_persona VARCHAR(20) REFERENCES Persona(nconst),
    id_produccion INTEGER REFERENCES Produccion(id_produccion) ON DELETE CASCADE,
    CONSTRAINT uk_produccion_escritor UNIQUE(id_persona, id_produccion)
);

-- Tabla Produccion_Director
CREATE TABLE Produccion_Director (
    id_produccion_director SERIAL PRIMARY KEY,
    id_persona VARCHAR(20) REFERENCES Persona(nconst),
    id_produccion INTEGER REFERENCES Produccion(id_produccion) ON DELETE CASCADE,
    CONSTRAINT uk_produccion_director UNIQUE(id_persona, id_produccion)
);

-- Tabla Profesion_Persona_Top
CREATE TABLE Profesion_Persona_Top (
    id_profesion_persona SERIAL PRIMARY KEY,
    nconst VARCHAR(20) REFERENCES Persona(nconst) ON DELETE CASCADE,
    id_profesion INTEGER REFERENCES Profesion(id_profesion),
    CONSTRAINT uk_profesion_persona UNIQUE(nconst, id_profesion)
);

-- Tabla Pelicula_Persona_Top
CREATE TABLE Pelicula_Persona_Top (
    id_titulo_persona SERIAL PRIMARY KEY,
    nconst VARCHAR(20) REFERENCES Persona(nconst) ON DELETE CASCADE,
    tconst VARCHAR(20) REFERENCES Titulo(tconst),
    CONSTRAINT uk_titulo_persona UNIQUE(nconst, tconst)
);

-- ================================
-- ÍNDICES PARA OPTIMIZACIÓN
-- ================================

-- Índices en campos de búsqueda frecuente
CREATE INDEX idx_titulo_categoria ON Titulo(id_categoria) WHERE id_categoria IS NOT NULL;
CREATE INDEX idx_titulo_anio ON Titulo(anio_lanzamiento) WHERE anio_lanzamiento IS NOT NULL;
CREATE INDEX idx_titulo_adulto ON Titulo(es_contenido_adulto);
CREATE INDEX idx_titulo_popular ON Titulo(titulo_popular) WHERE titulo_popular IS NOT NULL;

CREATE INDEX idx_persona_nombre ON Persona(nombre_artistico) WHERE nombre_artistico IS NOT NULL;
CREATE INDEX idx_persona_nacimiento ON Persona(anio_nacimiento) WHERE anio_nacimiento IS NOT NULL;

CREATE INDEX idx_reparto_titulo ON Reparto(tconst) WHERE tconst IS NOT NULL;
CREATE INDEX idx_reparto_persona ON Reparto(nconst) WHERE nconst IS NOT NULL;
CREATE INDEX idx_reparto_profesion ON Reparto(id_profesion) WHERE id_profesion IS NOT NULL;
CREATE INDEX idx_reparto_relevancia ON Reparto(relevancia) WHERE relevancia IS NOT NULL;

CREATE INDEX idx_genero_titulo_genero ON Genero_Titulo(id_genero) WHERE id_genero IS NOT NULL;
CREATE INDEX idx_genero_titulo_titulo ON Genero_Titulo(tconst) WHERE tconst IS NOT NULL;

CREATE INDEX idx_episodio_serie ON Episodio(id_titulo) WHERE id_titulo IS NOT NULL;
CREATE INDEX idx_episodio_temporada ON Episodio(temporada) WHERE temporada IS NOT NULL;

CREATE INDEX idx_puntuacion_promedio ON Puntuacion(promedio DESC) WHERE promedio IS NOT NULL;
CREATE INDEX idx_puntuacion_votos ON Puntuacion(votos DESC) WHERE votos IS NOT NULL;

-- Mensaje de confirmación
\echo 'Schema imdb_schema y todas las tablas creadas exitosamente!'
