-- ============================================================================
-- ZEOPY — conservation des comparaisons (chantier Apple, lot A1, décision L)
--
-- Deux vecteurs psychométriques — ceux de DEUX personnes — vivaient sans
-- limite de durée dans `comparisons` : `cleanup_old_requests` n'a jamais
-- touché cette table, et `expires_at` ne sert qu'à refuser une acceptation
-- tardive, il n'efface rien.
--
-- Après ce lot : les vecteurs ne vivent que le temps de l'analyse, et la
-- ligne disparaît dès que les deux téléphones ont pris le résultat.
--
-- À appliquer sur Supabase (SQL Editor), une seule fois, AVANT de déployer
-- le code qui écrit ces colonnes :
--
--   psql "$SUPABASE_DB_URL" -f migrations/2026-09-17-comparisons-conservation.sql
--
-- ou, dans l'éditeur SQL de Supabase, coller le contenu et exécuter.
-- Ré-exécutable sans risque (IF NOT EXISTS).
-- ============================================================================

ALTER TABLE comparisons
  ADD COLUMN IF NOT EXISTS from_fetched_at timestamptz,
  ADD COLUMN IF NOT EXISTS to_fetched_at   timestamptz;

COMMENT ON COLUMN comparisons.from_fetched_at IS
  'Quand l''initiateur a pris le résultat sur son téléphone (POST /compare/ack). Quand les deux sont posés, la ligne est supprimée.';
COMMENT ON COLUMN comparisons.to_fetched_at IS
  'Quand le répondant a pris le résultat sur son téléphone (POST /compare/ack). Quand les deux sont posés, la ligne est supprimée.';

-- Le nettoyage quotidien balaie par statut et par date : un index sur les
-- deux évite de parcourir toute la table chaque jour.
CREATE INDEX IF NOT EXISTS idx_comparisons_statut_date
  ON comparisons (status, created_at);
