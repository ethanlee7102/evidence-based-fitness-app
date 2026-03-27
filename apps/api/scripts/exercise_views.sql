-- Exercise Library Overview Queries
-- Run these in the Supabase SQL Editor

-- ============================================================================
-- 1. SUMMARY STATS
-- ============================================================================
SELECT
  (SELECT count(*) FROM muscle_groups) AS muscle_groups,
  (SELECT count(*) FROM exercises WHERE is_global = true) AS exercises,
  (SELECT count(*) FROM exercise_muscles) AS muscle_mappings,
  (SELECT round(count(*)::numeric / nullif((SELECT count(DISTINCT exercise_id) FROM exercise_muscles), 0), 1)) AS avg_muscles_per_exercise
FROM exercise_muscles
LIMIT 1;

-- ============================================================================
-- 2. ALL EXERCISES WITH THEIR MUSCLES (grouped, readable)
-- ============================================================================
SELECT
  e.name AS exercise,
  e.equipment,
  e.body_region,
  CASE WHEN e.is_compound THEN 'compound' ELSE 'isolation' END AS type,
  string_agg(
    mg.name || ' (' || em.activation_level || ')',
    ', '
    ORDER BY
      CASE em.activation_level
        WHEN 'maximum' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'partial' THEN 4
      END,
      mg.display_order
  ) AS muscles
FROM exercises e
JOIN exercise_muscles em ON em.exercise_id = e.id
JOIN muscle_groups mg ON mg.id = em.muscle_group_id
WHERE e.is_global = true
GROUP BY e.id, e.name, e.equipment, e.body_region, e.is_compound
ORDER BY e.name;

-- ============================================================================
-- 3. EXERCISES BY EQUIPMENT
-- ============================================================================
SELECT
  equipment,
  count(*) AS exercise_count,
  string_agg(name, ', ' ORDER BY name) AS exercises
FROM exercises
WHERE is_global = true
GROUP BY equipment
ORDER BY count(*) DESC;

-- ============================================================================
-- 4. EXERCISES BY BODY REGION
-- ============================================================================
SELECT
  body_region,
  count(*) AS exercise_count
FROM exercises
WHERE is_global = true
GROUP BY body_region
ORDER BY count(*) DESC;

-- ============================================================================
-- 5. MUSCLE GROUP USAGE (which muscles are mapped most)
-- ============================================================================
SELECT
  mg.category,
  mg.name AS muscle_group,
  count(*) AS total_exercises,
  count(*) FILTER (WHERE em.activation_level = 'maximum') AS "max",
  count(*) FILTER (WHERE em.activation_level = 'high') AS "high",
  count(*) FILTER (WHERE em.activation_level = 'medium') AS "med",
  count(*) FILTER (WHERE em.activation_level = 'partial') AS "part"
FROM muscle_groups mg
JOIN exercise_muscles em ON em.muscle_group_id = mg.id
JOIN exercises e ON e.id = em.exercise_id AND e.is_global = true
GROUP BY mg.category, mg.name, mg.display_order
ORDER BY mg.display_order;

-- ============================================================================
-- 6. TOP EXERCISES PER MUSCLE GROUP (maximum activation only)
-- ============================================================================
SELECT
  mg.category,
  mg.name AS muscle_group,
  string_agg(e.name, ', ' ORDER BY e.name) AS "maximum_activation_exercises",
  count(*) AS count
FROM muscle_groups mg
JOIN exercise_muscles em ON em.muscle_group_id = mg.id AND em.activation_level = 'maximum'
JOIN exercises e ON e.id = em.exercise_id AND e.is_global = true
GROUP BY mg.category, mg.name, mg.display_order
ORDER BY mg.display_order;

-- ============================================================================
-- 7. EXERCISES WITH NO MAXIMUM ACTIVATION (broad load spread)
-- ============================================================================
SELECT
  e.name,
  e.equipment,
  e.body_region,
  string_agg(
    mg.name || ' (' || em.activation_level || ')',
    ', '
    ORDER BY
      CASE em.activation_level
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'partial' THEN 3
      END
  ) AS muscles
FROM exercises e
JOIN exercise_muscles em ON em.exercise_id = e.id
LEFT JOIN exercise_muscles em_max ON em_max.exercise_id = e.id AND em_max.activation_level = 'maximum'
JOIN muscle_groups mg ON mg.id = em.muscle_group_id
WHERE e.is_global = true
  AND em_max.exercise_id IS NULL
GROUP BY e.id, e.name, e.equipment, e.body_region
ORDER BY e.name;

-- ============================================================================
-- 8. ACTIVATION LEVEL DISTRIBUTION
-- ============================================================================
SELECT
  activation_level,
  count(*) AS mapping_count,
  round(count(*)::numeric / (SELECT count(*) FROM exercise_muscles) * 100, 1) AS pct
FROM exercise_muscles
GROUP BY activation_level
ORDER BY
  CASE activation_level
    WHEN 'maximum' THEN 1
    WHEN 'high' THEN 2
    WHEN 'medium' THEN 3
    WHEN 'partial' THEN 4
  END;

-- ============================================================================
-- 9. SEARCH: Find exercises targeting a specific muscle
--    Change the muscle name below to search
-- ============================================================================
SELECT
  e.name AS exercise,
  em.activation_level,
  e.equipment,
  e.body_region
FROM exercises e
JOIN exercise_muscles em ON em.exercise_id = e.id
JOIN muscle_groups mg ON mg.id = em.muscle_group_id
WHERE e.is_global = true
  AND mg.name = 'Gluteus Maximus'  -- << CHANGE THIS
ORDER BY
  CASE em.activation_level
    WHEN 'maximum' THEN 1
    WHEN 'high' THEN 2
    WHEN 'medium' THEN 3
    WHEN 'partial' THEN 4
  END,
  e.name;

-- ============================================================================
-- 10. MUSCLE GROUPS TABLE
-- ============================================================================
SELECT
  category,
  name,
  display_order
FROM muscle_groups
ORDER BY display_order;
