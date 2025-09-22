CREATE OR REPLACE PROCEDURE sp_mostrar_informacion_titulo(
    p_tconst VARCHAR(20)
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_titulo_info RECORD;
    v_genero_nombre VARCHAR(50);
    v_alternativo_record RECORD;
    v_puntuacion_record RECORD;
    v_reparto_record RECORD;
    v_episodio_record RECORD;
    v_contenido_adulto TEXT;
    v_es_original_text TEXT;
BEGIN
    -- Información básica del título
    SELECT 
        t.tconst,
        t.titulo_popular,
        t.titulo_original,
        c.nombre as categoria,
        t.es_contenido_adulto,
        t.anio_lanzamiento,
        t.anio_finalizacion,
        t.duracion_minutos
    INTO v_titulo_info
    FROM Titulo t
    JOIN Categoria c ON t.id_categoria = c.id_categoria
    WHERE t.tconst = p_tconst;
    
    IF NOT FOUND THEN
        RAISE NOTICE 'No se encontró el título con tconst: %', p_tconst;
        RETURN;
    END IF;
    
    -- Convertir booleanos a texto
    IF v_titulo_info.es_contenido_adulto THEN
        v_contenido_adulto := 'Verdadero';
    ELSE
        v_contenido_adulto := 'Falso';
    END IF;
    
    -- Mostrar información básica
    RAISE NOTICE '========================================';
    RAISE NOTICE 'INFORMACIÓN DEL TÍTULO: %', p_tconst;
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Título popular: %', COALESCE(v_titulo_info.titulo_popular, 'N/A');
    RAISE NOTICE 'Título original: %', COALESCE(v_titulo_info.titulo_original, 'N/A');
    RAISE NOTICE 'Categoría: %', COALESCE(v_titulo_info.categoria, 'N/A');
    RAISE NOTICE 'Contenido adulto: %', v_contenido_adulto;
    RAISE NOTICE 'Año lanzamiento: %', COALESCE(v_titulo_info.anio_lanzamiento::TEXT, 'N/A');
    RAISE NOTICE 'Año finalización: %', COALESCE(v_titulo_info.anio_finalizacion::TEXT, 'N/A');
    RAISE NOTICE 'Duración: % minutos', COALESCE(v_titulo_info.duracion_minutos::TEXT, 'N/A');
    RAISE NOTICE '';
    
    -- Géneros del título
    RAISE NOTICE 'GÉNEROS:';
    FOR v_genero_nombre IN
        SELECT g.nombre
        FROM Genero_Titulo gt
        JOIN Genero g ON gt.id_genero = g.id_genero
        WHERE gt.tconst = p_tconst
        ORDER BY g.nombre
    LOOP
        RAISE NOTICE '  - %', v_genero_nombre;
    END LOOP;
    
    -- Verificar si hay géneros
    IF NOT EXISTS (SELECT 1 FROM Genero_Titulo WHERE tconst = p_tconst) THEN
        RAISE NOTICE '  - No hay géneros registrados';
    END IF;
    RAISE NOTICE '';
    
    -- Títulos alternativos
    RAISE NOTICE 'TÍTULOS ALTERNATIVOS:';
    FOR v_alternativo_record IN
        SELECT 
            ta.nombre_titulo, 
            r.codigo as region_codigo, 
            i.codigo as idioma_codigo,
            ta.es_original
        FROM Titulo_Alternativo ta
        LEFT JOIN Region r ON ta.id_region = r.id_region
        LEFT JOIN Idioma i ON ta.id_idioma = i.id_idioma
        WHERE ta.tconst = p_tconst
        ORDER BY ta.orden
    LOOP
        -- Convertir booleano a texto
        IF v_alternativo_record.es_original THEN
            v_es_original_text := 'Verdadero';
        ELSE
            v_es_original_text := 'Falso';
        END IF;
        
        RAISE NOTICE '  - % (Región: %, Idioma: %, Original: %)', 
                     COALESCE(v_alternativo_record.nombre_titulo, 'N/A'), 
                     COALESCE(v_alternativo_record.region_codigo, 'N/A'), 
                     COALESCE(v_alternativo_record.idioma_codigo, 'N/A'),
                     v_es_original_text;
    END LOOP;
    
    -- Verificar si hay títulos alternativos
    IF NOT EXISTS (SELECT 1 FROM Titulo_Alternativo WHERE tconst = p_tconst) THEN
        RAISE NOTICE '  - No hay títulos alternativos registrados';
    END IF;
    RAISE NOTICE '';
    
    -- Información de puntuación
    SELECT promedio, votos INTO v_puntuacion_record
    FROM Puntuacion WHERE tconst = p_tconst;
    
    IF FOUND THEN
        RAISE NOTICE 'PUNTUACIÓN:';
        RAISE NOTICE '  Promedio: %/10', COALESCE(v_puntuacion_record.promedio::TEXT, 'N/A');
        RAISE NOTICE '  Votos: %', COALESCE(v_puntuacion_record.votos::TEXT, 'N/A');
        RAISE NOTICE '';
    ELSE
        RAISE NOTICE 'PUNTUACIÓN: No disponible';
        RAISE NOTICE '';
    END IF;
    
    -- Información del reparto (solo principales)
    RAISE NOTICE 'REPARTO PRINCIPAL:';
    FOR v_reparto_record IN
        SELECT 
            p.nombre_artistico, 
            pr.nombre as profesion, 
            r.personaje,
            r.relevancia
        FROM Reparto r
        JOIN Persona p ON r.nconst = p.nconst
        JOIN Profesion pr ON r.id_profesion = pr.id_profesion
        WHERE r.tconst = p_tconst
        ORDER BY r.relevancia NULLS LAST, pr.nombre, p.nombre_artistico
        LIMIT 15
    LOOP
        IF v_reparto_record.personaje IS NOT NULL THEN
            RAISE NOTICE '  - % (%): % (Relevancia: %)', 
                         COALESCE(v_reparto_record.nombre_artistico, 'N/A'), 
                         COALESCE(v_reparto_record.profesion, 'N/A'), 
                         COALESCE(v_reparto_record.personaje, 'N/A'),
                         COALESCE(v_reparto_record.relevancia::TEXT, 'N/A');
        ELSE
            RAISE NOTICE '  - % (%) (Relevancia: %)', 
                         COALESCE(v_reparto_record.nombre_artistico, 'N/A'), 
                         COALESCE(v_reparto_record.profesion, 'N/A'),
                         COALESCE(v_reparto_record.relevancia::TEXT, 'N/A');
        END IF;
    END LOOP;
    
    -- Verificar si hay reparto
    IF NOT EXISTS (SELECT 1 FROM Reparto WHERE tconst = p_tconst) THEN
        RAISE NOTICE '  - No hay reparto registrado';
    END IF;
    RAISE NOTICE '';
    
    -- Información de episodios si es una serie
    SELECT COUNT(*) as total_episodios, 
           MAX(temporada) as max_temporada
    INTO v_episodio_record
    FROM Episodio 
    WHERE id_titulo = p_tconst;
    
    IF v_episodio_record.total_episodios > 0 THEN
        RAISE NOTICE 'INFORMACIÓN DE EPISODIOS:';
        RAISE NOTICE '  Total episodios: %', v_episodio_record.total_episodios;
        RAISE NOTICE '  Temporadas: %', v_episodio_record.max_temporada;
        RAISE NOTICE '';
    END IF;
    
    -- Información de directores y escritores
    IF EXISTS (SELECT 1 FROM Produccion WHERE tconst = p_tconst) THEN
        RAISE NOTICE 'EQUIPO DE PRODUCCIÓN:';
        
        -- Directores
        RAISE NOTICE '  Directores:';
        FOR v_reparto_record IN
            SELECT p.nombre_artistico
            FROM Produccion_Director pd
            JOIN Persona p ON pd.id_persona = p.nconst
            JOIN Produccion pr ON pd.id_produccion = pr.id_produccion
            WHERE pr.tconst = p_tconst
            ORDER BY p.nombre_artistico
        LOOP
            RAISE NOTICE '    - %', COALESCE(v_reparto_record.nombre_artistico, 'N/A');
        END LOOP;
        
        -- Verificar si hay directores
        IF NOT EXISTS (
            SELECT 1 FROM Produccion_Director pd
            JOIN Produccion pr ON pd.id_produccion = pr.id_produccion
            WHERE pr.tconst = p_tconst
        ) THEN
            RAISE NOTICE '    - No hay directores registrados';
        END IF;
        
        -- Escritores
        RAISE NOTICE '  Escritores:';
        FOR v_reparto_record IN
            SELECT p.nombre_artistico
            FROM Produccion_Escritor pe
            JOIN Persona p ON pe.id_persona = p.nconst
            JOIN Produccion pr ON pe.id_produccion = pr.id_produccion
            WHERE pr.tconst = p_tconst
            ORDER BY p.nombre_artistico
        LOOP
            RAISE NOTICE '    - %', COALESCE(v_reparto_record.nombre_artistico, 'N/A');
        END LOOP;
        
        -- Verificar si hay escritores
        IF NOT EXISTS (
            SELECT 1 FROM Produccion_Escritor pe
            JOIN Produccion pr ON pe.id_produccion = pr.id_produccion
            WHERE pr.tconst = p_tconst
        ) THEN
            RAISE NOTICE '    - No hay escritores registrados';
        END IF;
        
        RAISE NOTICE '';
    END IF;
    
    RAISE NOTICE '========================================';
    
END;
$$;

-- Ejemplo 1: Consultar información de un título específico
-- CALL sp_mostrar_informacion_titulo('tt0111161');
-- CALL sp_mostrar_informacion_titulo('tt0468569');
-- CALL sp_mostrar_informacion_titulo('tt0120338');