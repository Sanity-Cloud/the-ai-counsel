import { describe, expect, it } from 'vitest';
import { getCouncilRunLabel } from './auditRunLabel';

describe('getCouncilRunLabel', () => {
  it('labels full audit completion', () => {
    expect(getCouncilRunLabel({
      knownMode: 'full',
      critique: 'audit',
      hasStage3: true,
      claimAuditStatus: 'complete',
    })).toBe('🏛️ Full Audit');
  });

  it('labels synthesis-only partial audit', () => {
    expect(getCouncilRunLabel({
      knownMode: 'full',
      critique: 'audit',
      convergenceStatus: 'partial',
      claimAuditStatus: 'unavailable',
      hasStage3: true,
    })).toBe('⚠️ Partial Audit (synthesis-only fallback)');
  });

  it('labels failed audit runs', () => {
    expect(getCouncilRunLabel({
      knownMode: 'full',
      critique: 'audit',
      pipelineError: { message: 'boom' },
    })).toBe('⚠️ Audit Failed');
  });
});
