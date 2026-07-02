import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import AuditResults from './AuditResults';
import { shouldRenderAuditResults } from '../utils/auditResults';

const stage2a = [
  { model: 'notion2api:openai:oatmeal-cookie', raw_output: 'Holistic eval text', parsed_ranking: ['Response B', 'Response A'], attempts: [] },
];
const stage2bResults = [
  { model: 'notion2api:openai:oatmeal-cookie', claim_verdicts: { 'C-001': { source_support: 'supported', substantive_assessment: 'sound' } } },
];
const twoBAggregate = {
  audit_status: 'complete',
  valid_evaluators: 2,
  expected_evaluators: 2,
  claims_evaluated: 3,
  aggregated_claims: [
    { claim_id: 'C-001', canonical_text: 'Water boils at 100C at sea level.', support_counts: { supported: 2 }, assessment_counts: { sound: 2 } },
    { claim_id: 'C-002', canonical_text: 'Water boils at 99C.', support_counts: { supported: 1, unsupported: 1 }, assessment_counts: { sound: 1, unsound: 1 } },
    { claim_id: 'C-003', canonical_text: 'Perhaps pressure matters.', support_counts: { supported: 2 }, assessment_counts: { sound: 1, requires_qualification: 1 } },
  ],
};
const stage2c = {
  record: { adopt: ['C-001'], reject: ['C-002'], qualify: ['C-003'], authority_gaps: [], record_gaps: ['gap-1'], stage3_constraints: [] },
  model: 'notion2api:anthropic:ambrosia-tart-high',
  raw_output: '{ "adopt": ["C-001"] }',
  attempts: [],
};
const metadata = {
  critique_mode: 'audit',
  aggregated_2b: twoBAggregate,
  label_to_model: { A: 'notion2api:openai:oatmeal-cookie', B: 'notion2api:anthropic:ambrosia-tart-high' },
};

function render(props) {
  return renderToStaticMarkup(
    <AuditResults
      stage2a={props.stage2a !== undefined ? props.stage2a : stage2a}
      stage2b={props.stage2b !== undefined ? props.stage2b : stage2bResults}
      stage2c={props.stage2c !== undefined ? props.stage2c : stage2c}
      metadata={props.metadata !== undefined ? props.metadata : metadata}
      loading={props.loading !== undefined ? props.loading : {}}
      timers={props.timers !== undefined ? props.timers : {}}
    />
  );
}

describe('AuditResults SSR', () => {
  it('renders the three audit stage headings', () => {
    const html = render({});
    expect(html).toContain('Stage 2A: Holistic Evaluation');
    expect(html).toContain('Stage 2B: Claim Audit');
    expect(html).toContain('Stage 2C: Chairman Adjudication');
  });

  it('renders Stage 2A evaluator data', () => {
    const html = render({});
    expect(html).toContain('Holistic eval text');
    expect(html).toContain('1 completed');
  });

  it('renders Stage 2B aggregate claim counts and does not label contested as strong', () => {
    const html = render({});
    expect(html).toContain('3 claims');
    expect(html).toContain('2 contested');
    expect(html).toContain('1 strong');
    // C-002 is contested
    expect(html).toContain('Water boils at 99C.');
    expect(html).toMatch(/C-002[\s\S]*Contested/);
    // No claim should be mislabeled strong when it carries an adverse count
    expect(html).not.toMatch(/C-002[\s\S]*audit-claim-status--strong/);
  });

  it('renders Stage 2C adopt, reject, and qualify sections', () => {
    const html = render({});
    expect(html).toContain('Adopt');
    expect(html).toContain('Reject');
    expect(html).toContain('Qualify');
    expect(html).toContain('C-001');
    expect(html).toContain('C-002');
    expect(html).toContain('C-003');
  });

  it('renders a clear empty state for empty correction-record sections', () => {
    const html = render({});
    // authority_gaps and stage3_constraints are empty
    expect(html).toContain('Authority Gaps');
    expect(html).toMatch(/Authority Gaps[\s\S]*No authority gaps were recorded/);
    expect(html).toContain('Stage 3 Constraints');
    expect(html).toMatch(/Stage 3 Constraints[\s\S]*No stage 3 constraints were recorded/);
  });

  it('renders raw output inside collapsed details sections (not open by default)', () => {
    const html = render({});
    // details elements should be present and NOT carry the open attribute
    expect(html).toContain('<details ');
    expect(html).not.toContain('<details open');
    expect(html).toContain('Show raw holistic evaluation');
    expect(html).toContain('Raw Stage 2C output');
  });

  it('renders Stage 2C provider errors visibly', () => {
    const html = render({
      stage2c: { error: true, error_message: 'Stage 2C API Failure', model: 'notion2api:anthropic:ambrosia-tart-high' },
      loading: {},
    });
    expect(html).toContain('Stage 2C adjudication failed');
    expect(html).toContain('Stage 2C API Failure');
  });

  it('does not prematurely present a loading stage as completed', () => {
    const html = render({
      stage2a: null,
      stage2b: null,
      stage2c: null,
      metadata: { critique_mode: 'audit' },
      loading: { stage2a: true, stage2b: false, stage2c: false },
      timers: {},
    });
    // Only Stage 2A is loading; 2B/2C have no data and no loading => they render nothing.
    expect(html).toContain('Stage 2A: Holistic Evaluation');
    expect(html).toContain('Stage 2A evaluations in progress');
    expect(html).not.toContain('Stage 2B: Claim Audit');
    expect(html).not.toContain('Stage 2C: Chairman Adjudication');
  });

  it('renders Stage 2A queued and running badges without claiming completion', () => {
    const html = render({
      stage2a: [
        { model: 'model-a', status: 'queued' },
        { model: 'model-b', status: 'running' },
      ],
      stage2b: null,
      stage2c: null,
      metadata: { critique_mode: 'audit' },
      loading: { stage2a: true },
    });

    expect(html).toContain('Queued');
    expect(html).toContain('Running');
    expect(html).toContain('0 completed');
    expect(html).not.toContain('2 completed');
  });

  it('keeps Stage 2B in its loading state while every evaluator is pending', () => {
    const html = render({
      stage2a: null,
      stage2b: [
        { model: 'model-a', status: 'queued' },
        { model: 'model-b', status: 'running' },
      ],
      stage2c: null,
      metadata: { critique_mode: 'audit' },
      loading: { stage2b: true },
    });

    expect(html).toContain('Stage 2B claim audits in progress');
    expect(html).not.toContain('quorum met');
    expect(html).not.toContain('quorum failed');
  });

  it('renders mixed Stage 2B terminal and running statuses as quorum pending', () => {
    const html = render({
      stage2a: null,
      stage2b: [
        { model: 'model-a', status: 'completed', claim_verdicts: {} },
        { model: 'model-b', status: 'running' },
      ],
      stage2c: null,
      metadata: { critique_mode: 'audit' },
      loading: { stage2b: true },
    });

    expect(html).toContain('Completed');
    expect(html).toContain('Running');
    expect(html).toContain('quorum pending');
    expect(html).not.toContain('quorum failed');
  });

  it('terminates Stage 2C loading after an error event (no perpetual spinner)', () => {
    const html = render({
      stage2c: { error: true, error_message: 'API Failure', model: 'notion2api:anthropic:ambrosia-tart-high' },
      loading: { stage2c: false, stage2: false },
      timers: {},
    });
    expect(html).toContain('Stage 2C: Chairman Adjudication');
    expect(html).not.toContain('Stage 2C chairman adjudication in progress');
    expect(html).toContain('Stage 2C adjudication failed');
  });

  it('renders from restored metadata shape without requiring live events', () => {
    const html = render({
      stage2a: null,
      stage2b: null,
      stage2c: null,
      metadata: {
        critique_mode: 'audit',
        stage2a_results: stage2a,
        stage2b_results: stage2bResults,
        stage2c_result: stage2c,
        aggregated_2b: twoBAggregate,
        label_to_model: metadata.label_to_model,
      },
      loading: {},
      timers: {},
    });
    expect(html).toContain('Stage 2A: Holistic Evaluation');
    expect(html).toContain('Stage 2B: Claim Audit');
    expect(html).toContain('Stage 2C: Chairman Adjudication');
    expect(html).toContain('Holistic eval text');
  });
});

describe('shouldRenderAuditResults (routing)', () => {
  it('routes only audit mode to the dedicated component', () => {
    expect(shouldRenderAuditResults('audit')).toBe(true);
    ['freeform', 'paragraph', 'claim'].forEach((m) => {
      expect(shouldRenderAuditResults(m)).toBe(false);
    });
  });
});