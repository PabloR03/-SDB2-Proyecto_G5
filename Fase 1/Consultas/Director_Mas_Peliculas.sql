DROP VIEW IF EXISTS imdb_schema.vw_director_mas_titulos;

CREATE OR REPLACE VIEW imdb_schema.vw_director_mas_titulos AS
SELECT 
    p.nconst as "ID Director",
    p.nombre_artistico as "Nombre Director",
    p.anio_nacimiento as "Año Nacimiento",
    p.anio_fallecimiento as "Año Fallecimiento",
    COUNT(*) as "Total Películas"
FROM imdb_schema.Produccion_Director pd
JOIN imdb_schema.Produccion pr ON pd.id_produccion = pr.id_produccion
JOIN imdb_schema.Titulo t ON pr.tconst = t.tconst
JOIN imdb_schema.Categoria c ON t.id_categoria = c.id_categoria
JOIN imdb_schema.Persona p ON pd.id_persona = p.nconst
WHERE c.nombre = 'short'
AND t.duracion_minutos >= 100
AND t.anio_lanzamiento IS NOT NULL
GROUP BY p.nconst, p.nombre_artistico, p.anio_nacimiento, p.anio_fallecimiento
ORDER BY COUNT(*) DESC
LIMIT 1;

SELECT * FROM imdb_schema.vw_director_mas_titulos;