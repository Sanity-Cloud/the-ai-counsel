const numberFormatter = new Intl.NumberFormat(undefined);

function round8(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return 0;
  return Math.round(value * 1e8) / 1e8;
}

function round2(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return 0;
  return Math.round(value * 100) / 100;
}

function emptyReport() {
  return {
    currency: 'USD',
    total_cost: 0,
    input_tokens: 0,
    output_tokens: 0,
    total_tokens: 0,
    total_calls: 0,
    known_cost_calls: 0,
    unknown_cost_calls: 0,
    estimated_calls: 0,
    free_calls: 0,
    has_unknown_costs: false,
    has_estimates: false,
    by_model: [],
    message_count: 0,
  };
}

export function summarizeConversationCost(messages) {
  if (!Array.isArray(messages) || messages.length === 0) {
    return emptyReport();
  }

  const report = emptyReport();
  const byModel = new Map();

  for (const msg of messages) {
    if (!msg || msg.role !== 'assistant') continue;
    const cr = msg.metadata && msg.metadata.cost_report;
    if (!cr || typeof cr !== 'object') continue;

    report.message_count += 1;
    report.total_cost += typeof cr.total_cost === 'number' ? cr.total_cost : 0;
    report.input_tokens += typeof cr.input_tokens === 'number' ? cr.input_tokens : 0;
    report.output_tokens += typeof cr.output_tokens === 'number' ? cr.output_tokens : 0;
    report.total_tokens += typeof cr.total_tokens === 'number' ? cr.total_tokens : 0;
    report.total_calls += typeof cr.total_calls === 'number' ? cr.total_calls : 0;
    report.known_cost_calls += typeof cr.known_cost_calls === 'number' ? cr.known_cost_calls : 0;
    report.unknown_cost_calls += typeof cr.unknown_cost_calls === 'number' ? cr.unknown_cost_calls : 0;
    report.estimated_calls += typeof cr.estimated_calls === 'number' ? cr.estimated_calls : 0;
    report.free_calls += typeof cr.free_calls === 'number' ? cr.free_calls : 0;

    if (Array.isArray(cr.by_model)) {
      for (const row of cr.by_model) {
        if (!row || !row.name) continue;
        const existing = byModel.get(row.name) || {
          name: row.name,
          calls: 0,
          input_tokens: 0,
          output_tokens: 0,
          total_tokens: 0,
          total_cost: 0,
          known_cost_calls: 0,
          unknown_cost_calls: 0,
          estimated_calls: 0,
          free_calls: 0,
        };
        existing.calls += row.calls || 0;
        existing.input_tokens += row.input_tokens || 0;
        existing.output_tokens += row.output_tokens || 0;
        existing.total_tokens += row.total_tokens || 0;
        existing.total_cost += typeof row.total_cost === 'number' ? row.total_cost : 0;
        existing.known_cost_calls += row.known_cost_calls || 0;
        existing.unknown_cost_calls += row.unknown_cost_calls || 0;
        existing.estimated_calls += row.estimated_calls || 0;
        existing.free_calls += row.free_calls || 0;
        byModel.set(row.name, existing);
      }
    }
  }

  report.total_cost = round8(report.total_cost);
  report.has_unknown_costs = report.unknown_cost_calls > 0;
  report.has_estimates = report.estimated_calls > 0;
  report.by_model = Array.from(byModel.values())
    .map((row) => ({ ...row, total_cost: round8(row.total_cost) }))
    .sort((a, b) => b.total_cost - a.total_cost);

  return report;
}

export function formatConversationCostSummary(report) {
  if (!report || report.total_calls === 0) return 'No spend yet';
  const usd = formatUsd(report.total_cost, report.unknown_cost_calls > 0 && report.known_cost_calls === 0);
  const calls = `${numberFormatter.format(report.total_calls)} calls`;
  return `${usd} · ${calls}`;
}

function formatUsd(value, unknown = false) {
  if (unknown || typeof value !== 'number' || Number.isNaN(value)) return 'Unknown';
  if (value === 0) return '$0.00';
  if (value < 0.000001) return '<$0.000001';
  if (value < 0.01) return `$${value.toFixed(6)}`;
  return `$${value.toFixed(4)}`;
}
