import { useState } from 'react';
import ModelVisualIcon from './ModelVisualIcon';
import StageTimer from './StageTimer';
import { getModelVisuals, getShortModelName } from '../utils/modelHelpers';
import { copyToClipboard } from '../utils/clipboard';
import { buildAuditViewModel } from '../utils/auditResults';
import './AuditResults.css';

/**
 * Dedicated completed-results presentation for Audit critique mode.
 * Renders Stage 2A (holistic evaluation), Stage 2B (claim audit), and
 * Stage 2C (chairman adjudication) as distinct labeled sections rather
 * than routing all three through the generic Stage2 component.
 *
 * Data is normalized at the boundary via buildAuditViewModel so the JSX
 * only consumes canonical view-model fields (live-streamed and restored
 * conversation shapes are both handled there).
 */
export default function AuditResults({ stage2a, stage2b, stage2c, metadata, loading, timers }) {
  const vm = buildAuditViewModel({ stage2a, stage2b, stage2c, metadata, loading, timers });

  return (
    <div className="audit-results">
      <Stage2aPanel stage2a={vm.stage2a} />
      <Stage2bPanel stage2b={vm.stage2b} />
      <Stage2cPanel stage2c={vm.stage2c} />
    </div>
  );
}

function Stage2aPanel({ stage2a }) {
  const { heading, evaluators, coverage, aggregateRankings, labelToModel, loading, duration } = stage2a;
  if (loading && evaluators.length === 0) {
    return (
      <section className="audit-panel audit-panel--2a" aria-label={heading}>
        <PanelHeader heading={heading} duration={duration} />
        <p className="audit-loading-text">Stage 2A evaluations in progress…</p>
      </section>
    );
  }
  if (evaluators.length === 0) return null;

  return (
    <section className="audit-panel audit-panel--2a" aria-label={heading}>
      <PanelHeader heading={heading} duration={duration} />
      <p className="audit-panel-description">
        Each evaluator produced a holistic evaluation and ranked all responses.
        Below, aggregate ranking combines the per-evaluator rankings.
      </p>

      <div className="audit-coverage" role="status">
        <span className="audit-coverage-stat">{coverage.completed} completed</span>
        {coverage.failed > 0 && (
          <span className="audit-coverage-stat audit-coverage-stat--warn">{coverage.failed} failed</span>
        )}
        <span className="audit-coverage-stat">{coverage.total} total</span>
      </div>

      {evaluators.map((ev) => (
        <EvaluatorRow key={ev.model} evaluator={ev} labelToModel={labelToModel} />
      ))}

      {aggregateRankings && aggregateRankings.length > 0 && (
        <AggregateRankings aggregateRankings={aggregateRankings} labelToModel={labelToModel} />
      )}
    </section>
  );
}

function EvaluatorRow({ evaluator, labelToModel }) {
  const [copied, setCopied] = useState(false);
  const visuals = getModelVisuals(evaluator.model);
  const shortName = getShortModelName(evaluator.model);
  const hasError = evaluator.status === 'failed';

  const handleCopy = async () => {
    const ok = await copyToClipboard(evaluator.rawOutput || '');
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className={`audit-evaluator ${hasError ? 'audit-evaluator--error' : ''}`}>
      <div className="audit-evaluator-head">
        <span className="audit-model-avatar" style={{ backgroundColor: hasError ? '#ef4444' : visuals.color }}>
          <ModelVisualIcon visuals={visuals} scale={0.6} />
        </span>
        <span className="audit-model-name" title={evaluator.model || ''}>{shortName}</span>
        <span className={`audit-status-badge audit-status-badge--${evaluator.status}`}>
          {evaluator.status === 'failed' ? 'Failed' : 'Completed'}
        </span>
        {evaluator.rawOutput && (
          <button
            className="audit-copy-btn"
            onClick={handleCopy}
            aria-label={`Copy ${shortName} holistic evaluation`}
          >
            {copied ? '✓ Copied' : '📋 Copy'}
          </button>
        )}
      </div>
      {hasError && evaluator.errorMessage && (
        <p className="audit-error-text" role="alert">{evaluator.errorMessage}</p>
      )}
      {evaluator.parsedRanking && evaluator.parsedRanking.length > 0 && (
        <div className="audit-parsed-ranking">
          <span className="audit-ranking-label">Ranking:</span>
          <ol className="audit-ranking-list">
            {evaluator.parsedRanking.map((label, i) => (
              <li key={`${label}-${i}`}>
                <span className="audit-ranking-label-label">{label}</span>
                {labelToModel[label] && (
                  <span className="audit-ranking-model">{getShortModelName(labelToModel[label])}</span>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}
      {evaluator.rawOutput && (
        <details className="audit-raw-collapse">
          <summary className="audit-raw-toggle">Show raw holistic evaluation</summary>
          <pre className="audit-raw-output">{evaluator.rawOutput}</pre>
        </details>
      )}
    </div>
  );
}

function AggregateRankings({ aggregateRankings }) {
  const maxRank = aggregateRankings.length || 1;
  return (
    <div className="audit-aggregate-rankings">
      <h5 className="audit-subheading">Aggregate Ranking</h5>
      <ol className="audit-aggregate-list">
        {aggregateRankings.map((agg, i) => {
          const visuals = getModelVisuals(agg.model);
          const scorePct = Math.max(5, Math.min(100, ((agg.average_rank || 0) / maxRank) * 100));
          return (
            <li key={i} className="audit-aggregate-item">
              <span className="audit-rank-pos">#{i + 1}</span>
              <span className="audit-rank-bar" style={{ width: `${scorePct}%`, ['--bar-color']: visuals.color }}>
                <span className="audit-rank-bar-model">{getShortModelName(agg.model)}</span>
                <span className="audit-rank-bar-score">{(agg.average_rank || 0).toFixed(2)}</span>
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function Stage2bPanel({ stage2b }) {
  const { heading, claims, contestedCount, strongCount, claimsEvaluated, validEvaluators, expectedEvaluators, auditStatus, quorumMet, partialCoverage, evaluatorAudits, loading, duration } = stage2b;
  if (loading && claims.length === 0 && evaluatorAudits.length === 0) {
    return (
      <section className="audit-panel audit-panel--2b" aria-label={heading}>
        <PanelHeader heading={heading} duration={duration} />
        <p className="audit-loading-text">Stage 2B claim audits in progress…</p>
      </section>
    );
  }
  if (claims.length === 0 && evaluatorAudits.length === 0) return null;

  return (
    <section className="audit-panel audit-panel--2b" aria-label={heading}>
      <PanelHeader heading={heading} duration={duration} />
      <p className="audit-panel-description">
        Each canonical claim received per-support and per-assessment verdicts from the evaluators.
        Contested claims surface first; strong claims fold below.
      </p>

      <div className="audit-coverage" role="status">
        <span className="audit-coverage-stat">{claimsEvaluated} claims</span>
        <span className="audit-coverage-stat">{validEvaluators}/{expectedEvaluators} evaluators</span>
        {partialCoverage && (
          <span className="audit-coverage-stat audit-coverage-stat--warn">partial coverage</span>
        )}
        <span className={`audit-coverage-stat audit-coverage-stat--${quorumMet ? 'ok' : 'warn'}`}>
          {quorumMet ? 'quorum met' : 'quorum failed'}
        </span>
        {contestedCount > 0 && (
          <span className="audit-coverage-stat audit-coverage-stat--contested">{contestedCount} contested</span>
        )}
        <span className="audit-coverage-stat audit-coverage-stat--strong">{strongCount} strong</span>
      </div>

      {auditStatus === 'failed' && (
        <div className="audit-error-banner" role="alert">
          Stage 2B failed quorum — insufficient valid evaluator audits.
        </div>
      )}

      {claims.length > 0 && (
        <div className="audit-claims-grid">
          {claims.map((claim) => <ClaimRow key={claim.claimId} claim={claim} />)}
        </div>
      )}

      {evaluatorAudits.length > 0 && (
        <details className="audit-raw-collapse">
          <summary className="audit-raw-toggle">Raw evaluator audits ({evaluatorAudits.length})</summary>
          <div className="audit-raw-audits">
            {evaluatorAudits.map((ea) => (
              <div key={ea.model} className={`audit-evaluator ${ea.status === 'failed' ? 'audit-evaluator--error' : ''}`}>
                <div className="audit-evaluator-head">
                  <span className="audit-model-name">{getShortModelName(ea.model)}</span>
                  <span className={`audit-status-badge audit-status-badge--${ea.status}`}>
                    {ea.status === 'failed' ? 'Failed' : 'Completed'}
                  </span>
                </div>
                {ea.errorMessage && <p className="audit-error-text" role="alert">{ea.errorMessage}</p>}
                {Object.keys(ea.claimVerdicts).length > 0 && (
                  <pre className="audit-raw-output">{JSON.stringify(ea.claimVerdicts, null, 2)}</pre>
                )}
              </div>
            ))}
          </div>
        </details>
      )}
    </section>
  );
}

function ClaimRow({ claim }) {
  const isContested = claim.status === 'contested';
  return (
    <div className={`audit-claim ${isContested ? 'audit-claim--contested' : 'audit-claim--strong'}`}>
      <div className="audit-claim-head">
        <span className="audit-claim-id">{claim.claimId}</span>
        <span className={`audit-claim-status audit-claim-status--${claim.status}`}>
          {isContested ? 'Contested' : 'Strong'}
        </span>
      </div>
      <p className="audit-claim-text">&ldquo;{claim.canonicalText}&rdquo;</p>
      <CountsTable title="Support" counts={claim.supportCounts} />
      <CountsTable title="Assessment" counts={claim.assessmentCounts} />
    </div>
  );
}

function CountsTable({ title, counts }) {
  const keys = Object.keys(counts || {});
  if (keys.length === 0) return null;
  return (
    <dl className="audit-counts">
      <dt>{title}</dt>
      <dd>
        {keys.map((k) => (
          <span key={k} className={`audit-count audit-count--${k}`}>{k}: {counts[k]}</span>
        ))}
      </dd>
    </dl>
  );
}

function Stage2cPanel({ stage2c }) {
  const { heading, record, model, rawOutput, error, errorMessage, sections, loading, duration } = stage2c;
  if (loading && !record && !error) {
    return (
      <section className="audit-panel audit-panel--2c" aria-label={heading}>
        <PanelHeader heading={heading} duration={duration} />
        <p className="audit-loading-text">Stage 2C chairman adjudication in progress…</p>
      </section>
    );
  }
  if (!record && !error) return null;

  return (
    <section className="audit-panel audit-panel--2c" aria-label={heading}>
      <PanelHeader heading={heading} duration={duration} />
      {model && (
        <p className="audit-chairman">Chairman: <span className="audit-chairman-model">{getShortModelName(model)}</span></p>
      )}
      {error && (
        <div className="audit-error-banner" role="alert">
          Stage 2C adjudication failed: {errorMessage || 'unknown error'}
        </div>
      )}

      {sections.map((sec) => (
        <CorrectionSection key={sec.key} section={sec} />
      ))}

      {rawOutput && (
        <details className="audit-raw-collapse">
          <summary className="audit-raw-toggle">Raw Stage 2C output</summary>
          <pre className="audit-raw-output">{rawOutput}</pre>
        </details>
      )}
    </section>
  );
}

function CorrectionSection({ section }) {
  const empty = !section.items || section.items.length === 0;
  return (
    <div className={`audit-correction-section ${empty ? 'audit-correction-section--empty' : ''}`}>
      <h5 className="audit-correction-heading">{section.label}</h5>
      {empty ? (
        <p className="audit-empty-state">No {section.label.toLowerCase()} were recorded.</p>
      ) : (
        <ul className="audit-correction-items">
          {section.items.map((item, i) => (
            <li key={`${section.key}-${i}`} className="audit-correction-item">{String(item)}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function PanelHeader({ heading, duration }) {
  return (
    <div className="audit-panel-header">
      <h4 className="audit-panel-heading">{heading}</h4>
      <StageTimer startTime={duration.start} endTime={duration.end} label="Duration" />
    </div>
  );
}