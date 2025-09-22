CREATE OR REPLACE VIEW imdb_schema.vw_top10_titulos_rating AS
SELECT 
    t.titulo_popular as "Título",
    t.anio_lanzamiento as "Año",
    p.promedio as "Rating",
    p.votos as "Votos",
    c.nombre as "Tipo",
    t.duracion_minutos as "Duración (min)",
    t.tconst,
    t.es_contenido_adulto as "Adulto"
FROM imdb_schema.Titulo t
JOIN imdb_schema.Puntuacion p ON t.tconst = p.tconst
JOIN imdb_schema.Categoria c ON t.id_categoria = c.id_categoria
WHERE p.promedio IS NOT NULL
AND t.duracion_minutos >= 100
AND t.anio_lanzamiento IS NOT NULL
AND p.votos >= 100000
ORDER BY p.promedio DESC, p.votos DESC
LIMIT 10;
-- LLamada de la vista
-- SELECT * FROM imdb_schema.vw_top10_titulos_rating;