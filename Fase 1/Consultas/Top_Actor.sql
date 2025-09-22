DROP VIEW IF EXISTS imdb_schema.vw_top10_actores_mas_peliculas;

CREATE OR REPLACE VIEW imdb_schema.vw_top10_actores_mas_peliculas AS
SELECT 
    p.nconst as "ID Artista",
    p.nombre_artistico as "Nombre Artista",
    p.anio_nacimiento as "Año Nacimiento",
    p.anio_fallecimiento as "Año Fallecimiento",
    COUNT(DISTINCT r.tconst) as "Total Películas",
    pr.nombre as "Profesión"
FROM imdb_schema.Reparto r
JOIN imdb_schema.Titulo t ON r.tconst = t.tconst
JOIN imdb_schema.Categoria c ON t.id_categoria = c.id_categoria
JOIN imdb_schema.Persona p ON r.nconst = p.nconst
JOIN imdb_schema.Profesion pr ON r.id_profesion = pr.id_profesion
WHERE c.nombre = 'short'
AND t.duracion_minutos >= 100
AND t.anio_lanzamiento IS NOT NULL
AND pr.nombre IN ('actor', 'actress')
GROUP BY p.nconst, p.nombre_artistico, p.anio_nacimiento, p.anio_fallecimiento, pr.nombre
ORDER BY COUNT(DISTINCT r.tconst) DESC
LIMIT 10;

SELECT * FROM imdb_schema.vw_top10_actores_mas_peliculas;