const ROUND_SCOPED_METADATA_KEYS = [
  'label_to_model',
  'aggregate_rankings',
  'canonical_claims',
  'aggregate_claim_verdicts',
  'ranking_status',
  'valid_ranking_count',
  'invalid_ranking_count',
  'claim_decomposition',
];

export function buildRoundStartMetadata(metadata = {}, round = 1, totalRounds = 1) {
  const next = { ...metadata };
  ROUND_SCOPED_METADATA_KEYS.forEach((key) => {
    delete next[key];
  });

  next.current_round = Math.max(1, Number(round) || 1);
  next.debate_rounds_configured = Math.max(
    next.current_round,
    Number(totalRounds) || 1,
  );
  return next;
}

export function resolveRoundPresentation(metadata = {}, selectedRound = null) {
  const completedRounds = Array.isArray(metadata.rounds) ? metadata.rounds : [];
  const currentActiveRound = Math.max(1, Number(metadata.current_round) || 1);
  const configuredRounds = Math.max(1, Number(metadata.debate_rounds_configured) || 1);
  const totalRounds = Math.max(configuredRounds, currentActiveRound, completedRounds.length);
  const selected = Number(selectedRound);
  const safeSelectedRound = Number.isInteger(selected)
    && selected >= 1
    && selected <= totalRounds
    ? selected
    : null;
  const activeRoundNum = safeSelectedRound ?? currentActiveRound;

  return {
    completedRounds,
    hasRounds: completedRounds.length > 0,
    currentActiveRound,
    totalRounds,
    activeRoundNum,
    archivedRound: completedRounds[activeRoundNum - 1] || null,
  };
}
