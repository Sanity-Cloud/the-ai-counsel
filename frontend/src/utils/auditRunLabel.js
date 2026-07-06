export function getCouncilRunLabel({
  knownMode,
  critique,
  rounds = 1,
  failedEmptyRun = false,
  pipelineError = null,
  convergenceStatus = null,
  claimAuditStatus = null,
  hasStage3 = false,
}) {
  if (failedEmptyRun) {
    return critique === 'audit' ? '⚠️ Audit Failed' : '⚠️ Run Failed';
  }

  if (pipelineError && critique === 'audit') {
    return '⚠️ Audit Failed';
  }

  if (knownMode === 'chat_only') return '💬 Chat Only';
  if (knownMode === 'chat_ranking') return '⚖️ Chat + Ranking';

  if (knownMode === 'full') {
    if (critique === 'audit') {
      if (convergenceStatus === 'partial') {
        if (claimAuditStatus === 'unavailable') {
          return hasStage3
            ? '⚠️ Partial Audit (synthesis-only fallback)'
            : '⚠️ Partial Audit (claim audit unavailable)';
        }
        return '⚠️ Partial Audit';
      }
      if (hasStage3 && claimAuditStatus !== 'unavailable') {
        return '🏛️ Full Audit';
      }
      if (hasStage3) {
        return '⚠️ Partial Audit (synthesis-only fallback)';
      }
      return '🏛️ Full Deliberation';
    }

    if (rounds > 1) {
      return `🏛️ Full Debate (${rounds} Rds)`;
    }
    return '🏛️ Full Deliberation';
  }

  return '🏛️ Deliberation';
}
