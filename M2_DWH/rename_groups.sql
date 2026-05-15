-- ============================================================
-- Rename the 5 mixed-content category groups to names that
-- better reflect all their members. Wrapped in a transaction
-- so it's all-or-nothing.
-- Apply: psql -d olist_dwh -f dwh/rename_groups.sql
-- ============================================================

BEGIN;

UPDATE dim_category_group
SET    group_name = 'fashion_apparel'
WHERE  group_id   = 1;        -- was: fashion_roupa_feminina (women's apparel + sportswear)

UPDATE dim_category_group
SET    group_name = 'electronics_misc'
WHERE  group_id   = 7;        -- was: cool_stuff (catch-all + tablets + pc_gamer)

UPDATE dim_category_group
SET    group_name = 'gifts_household'
WHERE  group_id   = 8;        -- was: ferramentas_jardim (tools + toys + babies)

UPDATE dim_category_group
SET    group_name = 'music_homecomfort'
WHERE  group_id   = 9;        -- was: instrumentos_musicais (instruments + casa_conforto_2)

UPDATE dim_category_group
SET    group_name = 'personal_care_acc'
WHERE  group_id   = 10;       -- was: beleza_saude (beauty + sports + IT accessories)

COMMIT;

-- Sanity check — show all 10 final names
SELECT group_id, group_name, description
FROM   dim_category_group
ORDER  BY group_id;
