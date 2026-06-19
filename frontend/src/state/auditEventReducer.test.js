import { describe, it, expect } from 'vitest';
import { auditEventReducer } from './auditEventReducer';

describe('auditEventReducer', () => {
  const initialMessage = {
    role: 'assistant',
    stage1: [],
    stage2: null,
    stage3: null,
    metadata: null,
    loading: {
      search: false,
      stage1: false,
      stage2: false,
      stage3: false,
      stage4: false,
      stage2a: false,
      stage2b: false,
      stage2c: false,
    },
    timers: {
      stage1Start: null,
      stage1End: null,
      stage2Start: null,
      stage2End: null,
      stage3Start: null,
      stage3End: null,
      stage4Start: null,
      stage4End: null,
      stage2aStart: null,
      stage2aEnd: null,
      stage2bStart: null,
      stage2bEnd: null,
      stage2cStart: null,
      stage2cEnd: null,
    },
    progress: {
      stage1: { count: 0, total: 0, currentModel: null },
      stage2: { count: 0, total: 0, currentModel: null },
      stage2a: { count: 0, total: 0, currentModel: null },
      stage2b: { count: 0, total: 0, currentModel: null },
    }
  };

  const councilModels = ['modelA', 'modelB'];

  it('handles stage2a_start event correctly', () => {
    const event = { type: 'stage2a_start' };
    const nextState = auditEventReducer(initialMessage, event, councilModels);

    expect(nextState.loading.stage2).toBe(true);
    expect(nextState.loading.stage2a).toBe(true);
    expect(nextState.timers.stage2Start).not.toBeNull();
    expect(nextState.timers.stage2aStart).not.toBeNull();
  });

  it('handles stage2a_init event correctly', () => {
    const event = { type: 'stage2a_init', total: 2 };
    const nextState = auditEventReducer(initialMessage, event, councilModels);

    expect(nextState.progress.stage2.total).toBe(2);
    expect(nextState.progress.stage2a.total).toBe(2);
    expect(nextState.stage2).toHaveLength(2);
    expect(nextState.stage2[0].model).toBe('modelA');
    expect(nextState.stage2[0].pending).toBe(true);
    expect(nextState.stage2a).toHaveLength(2);
  });

  it('handles stage2a_progress event correctly', () => {
    const event = {
      type: 'stage2a_progress',
      count: 1,
      total: 2,
      data: { model: 'modelA', response: 'Evaluated' }
    };
    const nextState = auditEventReducer(initialMessage, event, councilModels);

    expect(nextState.progress.stage2.count).toBe(1);
    expect(nextState.progress.stage2a.count).toBe(1);
    expect(nextState.progress.stage2.currentModel).toBe('modelA');
    expect(nextState.stage2[0].response).toBe('Evaluated');
    expect(nextState.stage2a[0].response).toBe('Evaluated');
  });

  it('handles stage2a_complete event correctly', () => {
    const event = {
      type: 'stage2a_complete',
      data: [{ model: 'modelA' }, { model: 'modelB' }],
      metadata: { label_to_model: { A: 'modelA' } }
    };
    const nextState = auditEventReducer(initialMessage, event, councilModels);

    expect(nextState.loading.stage2a).toBe(false);
    expect(nextState.loading.stage2).toBe(false); // stage2 loading flag for 2a is preserved or false depending on how next stages run
    expect(nextState.timers.stage2aEnd).not.toBeNull();
    expect(nextState.metadata.label_to_model).toEqual({ A: 'modelA' });
  });

  it('handles stage2b_start, progress, and complete events correctly', () => {
    // 2b_start
    let state = auditEventReducer(initialMessage, { type: 'stage2b_start' }, councilModels);
    expect(state.loading.stage2b).toBe(true);
    expect(state.timers.stage2bStart).not.toBeNull();

    // 2b_init
    state = auditEventReducer(state, { type: 'stage2b_init', total: 2 }, councilModels);
    expect(state.progress.stage2b.total).toBe(2);
    expect(state.stage2b).toHaveLength(2);

    // 2b_progress
    state = auditEventReducer(state, {
      type: 'stage2b_progress',
      count: 1,
      total: 2,
      data: { model: 'modelA', claim_verdicts: {} }
    }, councilModels);
    expect(state.progress.stage2b.count).toBe(1);
    expect(state.stage2b[0].model).toBe('modelA');

    // 2b_complete
    state = auditEventReducer(state, {
      type: 'stage2b_complete',
      data: [{ model: 'modelA' }]
    }, councilModels);
    expect(state.loading.stage2b).toBe(false);
    expect(state.timers.stage2bEnd).not.toBeNull();
  });

  it('handles stage2c_start and complete events correctly', () => {
    // 2c_start
    let state = auditEventReducer(initialMessage, { type: 'stage2c_start' }, councilModels);
    expect(state.loading.stage2c).toBe(true);
    expect(state.timers.stage2cStart).not.toBeNull();

    // 2c_complete
    state = auditEventReducer(state, {
      type: 'stage2c_complete',
      data: { adopt: ['C-001'] },
      aggregated: { claims: [] }
    }, councilModels);

    expect(state.loading.stage2c).toBe(false);
    expect(state.loading.stage2).toBe(false); // stage 2 fully complete now
    expect(state.timers.stage2cEnd).not.toBeNull();
    expect(state.timers.stage2End).not.toBeNull();
    expect(state.metadata.aggregated_2b).toEqual({ claims: [] });
    expect(state.metadata.stage2c_result).toEqual({ adopt: ['C-001'] });
  });

  it('handles stage2a_error event correctly', () => {
    const event = { type: 'stage2a_error', message: 'Quorum failed' };
    const nextState = auditEventReducer(initialMessage, event, councilModels);

    expect(nextState.loading.stage2).toBe(false);
    expect(nextState.loading.stage2a).toBe(false);
    expect(nextState.error).toBe('Quorum failed');
  });
});
