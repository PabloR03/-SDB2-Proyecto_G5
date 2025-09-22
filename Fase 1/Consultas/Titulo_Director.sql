CREATE OR REPLACE PROCEDURE sp_titulos_director(
    p_nconst VARCHAR(20)
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_director_info RECORD;
    v_titulo_record RECORD;
    v_contador INTEGER := 0;
    v_mensaje TEXT;
BEGIN
    -- Obtener información del director
    SELECT nombre_artistico, anio_nacimiento, anio_fallecimiento
    INTO v_director_info
    FROM imdb_schema.Persona
    WHERE nconst = p_nconst;
    
    IF NOT FOUND THEN
        RAISE NOTICE 'No se encontró el director con nconst: %', p_nconst;
        RETURN;
    END IF;
    
    -- Mostrar información del director
    RAISE NOTICE '========================================';
    RAISE NOTICE 'TÍTULOS DEL DIRECTOR: %', p_nconst;
    RAISE NOTICE '========================================';
    v_mensaje := 'Nombre: ' || COALESCE(v_director_info.nombre_artistico, 'N/A');
    RAISE NOTICE '%', v_mensaje;
    v_mensaje := 'Año nacimiento: ' || COALESCE(v_director_info.anio_nacimiento::TEXT, 'N/A');
    RAISE NOTICE '%', v_mensaje;
    v_mensaje := 'Año fallecimiento: ' || COALESCE(v_director_info.anio_fallecimiento::TEXT, 'N/A');
    RAISE NOTICE '%', v_mensaje;
    RAISE NOTICE '';
    RAISE NOTICE 'TÍTULOS DIRIGIDOS:';
    RAISE NOTICE '========================================';
    
    -- Obtener todos los títulos dirigidos
    FOR v_titulo_record IN
        SELECT 
            t.tconst,
            t.titulo_popular,
            t.titulo_original,
            t.anio_lanzamiento,
            t.anio_finalizacion,
            t.duracion_minutos,
            c.nombre as categoria,
            p.promedio as puntuacion,
            p.votos,
            t.es_contenido_adulto
        FROM imdb_schema.Produccion_Director pd
        JOIN imdb_schema.Produccion pr ON pd.id_produccion = pr.id_produccion
        JOIN imdb_schema.Titulo t ON pr.tconst = t.tconst
        JOIN imdb_schema.Categoria c ON t.id_categoria = c.id_categoria
        LEFT JOIN imdb_schema.Puntuacion p ON t.tconst = p.tconst
        WHERE pd.id_persona = p_nconst
        ORDER BY t.anio_lanzamiento DESC NULLS LAST, p.promedio DESC NULLS LAST
    LOOP
        v_contador := v_contador + 1;
        
        v_mensaje := v_contador::TEXT || '.) ' || COALESCE(v_titulo_record.titulo_popular, v_titulo_record.titulo_original, 'Sin título');
        RAISE NOTICE '%', v_mensaje;
        
        v_mensaje := '   Título: ' || COALESCE(v_titulo_record.titulo_popular, v_titulo_record.titulo_original, 'Sin título');
        RAISE NOTICE '%', v_mensaje;
        
        v_mensaje := '   Año lanzamiento: ' || COALESCE(v_titulo_record.anio_lanzamiento::TEXT, 'N/A');
        RAISE NOTICE '%', v_mensaje;
        
        IF v_titulo_record.anio_finalizacion IS NOT NULL THEN
            v_mensaje := '   Año finalización: ' || v_titulo_record.anio_finalizacion::TEXT;
            RAISE NOTICE '%', v_mensaje;
        END IF;
        
        v_mensaje := '   Duración: ' || COALESCE(v_titulo_record.duracion_minutos::TEXT, 'N/A') || ' minutos';
        RAISE NOTICE '%', v_mensaje;
        
        v_mensaje := '   Categoría: ' || COALESCE(v_titulo_record.categoria, 'N/A');
        RAISE NOTICE '%', v_mensaje;
        
        v_mensaje := '   Contenido adulto: ' || CASE WHEN v_titulo_record.es_contenido_adulto THEN 'Sí' ELSE 'No' END;
        RAISE NOTICE '%', v_mensaje;
        
        -- Preparar mensaje de puntuación
        IF v_titulo_record.puntuacion IS NOT NULL THEN
            v_mensaje := '   Puntuación: ' || v_titulo_record.puntuacion::TEXT || '/10 (' || COALESCE(v_titulo_record.votos::TEXT, '0') || ' votos)';
        ELSE
            v_mensaje := '   Puntuación: No disponible';
        END IF;
        RAISE NOTICE '%', v_mensaje;
        
        v_mensaje := '   tconst: ' || v_titulo_record.tconst;
        RAISE NOTICE '%', v_mensaje;
        RAISE NOTICE '';
    END LOOP;
    
    -- Si no hay títulos
    IF v_contador = 0 THEN
        RAISE NOTICE 'No se encontraron títulos dirigidos por este director';
        RAISE NOTICE '';
    ELSE
        v_mensaje := 'Total de títulos: ' || v_contador::TEXT;
        RAISE NOTICE '%', v_mensaje;
        RAISE NOTICE '';
    END IF;
    
    RAISE NOTICE '========================================';
    
END;
$$;
-- Ejemplos
-- CALL sp_titulos_director('nm0000233'); 
-- CALL sp_titulos_director('nm0634240'); 
-- CALL sp_titulos_director('nm3227090'); 