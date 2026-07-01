import { describe, expect, it } from 'vitest';
import {
  buildRoundStartMetadata,
  resolveRoundPresentation,
} from './roundState';

describe('round state helpers', () => {
  it('shows the live active round instead of the last archived round', () => {
    const roundOne = { round_number: 1, stage2: [{ model: 'old' }] };
    const state = resolveRoundPresentation({
      current_round: 2,
      debate_rounds_configured: 2,
      rounds: [roundOne],
    });

    expect(state.totalRounds).toBe(2);
    expect(state.activeRoundNum).toBe(2);
    expect(state.archivedRound).toBeNull();
  });

  it('allows an explicit selection of an archived round', () => {
    const roundOne = { round_number: 1, stage2: [{ model: 'old' }] };
    const state = resolveRoundPresentation({
      current_round: 2,
      debate_rounds_configured: 2,
      rounds: [roundOne],
    }, 1);

    expect(state.activeRoundNum).toBe(1);
    expect(state.archivedRound).toBe(roundOne);
  });

  it('clears prior-round ranking metadata while preserving the archive', () => {
    const rounds = [{ round_number: 1 }];
    const metadata = buildRoundStartMetadata({
      rounds,
      search_context: 'retained',
      ranking_status: 'partial',
      valid_ranking_count: 7,
      invalid_ranking_count: 1,
      aggregate_rankings: [{ model: 'old' }],
      label_to_model: { 'Response A': 'old' },
    }, 2, 2);

    expect(metadata.rounds).toBe(rounds);
    expect(metadata.search_context).toBe('retained');
    expect(metadata.current_round).toBe(2);
    expect(metadata.debate_rounds_configured).toBe(2);
    expect(metadata.ranking_status).toBeUndefined();
    expect(metadata.valid_ranking_count).toBeUndefined();
    expect(metadata.invalid_ranking_count).toBeUndefined();
    expect(metadata.aggregate_rankings).toBeUndefined();
    expect(metadata.label_to_model).toBeUndefined();
  });
});
