/**
 * IndustryReportWidget — between-rounds Atlas Industry Pulse for HBR sims.
 *
 * Renders `payload.ux_executive.industry_report` (built by
 * backend/engines/industry_report_engine.build_industry_report_payload).
 *
 * Shape:
 *   {
 *     title: "Atlas Industry Pulse",
 *     business_model: "saas_smb",
 *     period_index?: 2,
 *     report: {
 *       period_label: "Q2",
 *       market_share_table: [{firm, share_pct, delta_vs_prior}, ...],
 *       financial_summary:  {revenue, revenue_delta, gross_margin, ...},
 *       kpi_grid:           [{id, label, value, vs_prior, sentiment, format}, ...],
 *       segment_growth:     [{segment, current_size, prior_size, growth_pct}, ...],
 *       exec_quote?:        string
 *     }
 *   }
 *
 * Returns null when payload is null (no industry_report config on the game).
 */
import React from 'react';

const SENTIMENT_COLOR = {
  positive: 'text-emerald-400',
  negative: 'text-rose-400',
  neutral: 'text-gray-400',
};

const SENTIMENT_ARROW = {
  positive: '▲',
  negative: '▼',
  neutral: '•',
};

const fmtDelta = (n, prefix = '') => {
  if (n === null || n === undefined || isNaN(n) || n === 0) return '—';
  const sign = n > 0 ? '+' : '';
  return `${sign}${prefix}${typeof n === 'number' ? n.toFixed(1) : n}`;
};

const fmtPct = (n) => {
  if (n === null || n === undefined || isNaN(n)) return '—';
  return `${Number(n).toFixed(1)}%`;
};

const fmtMoney = (n) => {
  if (n === null || n === undefined || isNaN(n)) return '—';
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${Number(n).toFixed(0)}`;
};

const fmtKpiValue = (v, format) => {
  if (v === null || v === undefined) return '—';
  switch (format) {
    case 'percent':
      return typeof v === 'number' ? `${v.toFixed(1)}%` : String(v);
    case 'money':
      return typeof v === 'number' ? fmtMoney(v) : String(v);
    case 'int':
      return typeof v === 'number' ? Math.round(v).toString() : String(v);
    default:
      return String(v);
  }
};

function MarketShareTable({ rows }) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return (
      <p className="text-[11px] text-gray-500 italic">
        Market share data populates as the simulation advances.
      </p>
    );
  }
  // Sort descending by share_pct
  const sorted = [...rows].sort((a, b) => (b.share_pct || 0) - (a.share_pct || 0));
  const max = Math.max(1, ...sorted.map((r) => r.share_pct || 0));
  return (
    <div className="space-y-1.5">
      {sorted.map((r) => {
        const pct = r.share_pct || 0;
        const delta = r.delta_vs_prior || 0;
        const isPlayer = (r.firm || '').toLowerCase().includes('player') || r.is_player;
        return (
          <div key={r.firm} className="flex items-center gap-2 text-xs">
            <div className={`w-24 truncate font-bold ${isPlayer ? 'text-emerald-300' : 'text-gray-200'}`}>
              {isPlayer ? '🎯 ' : ''}{r.firm}
            </div>
            <div className="flex-1 bg-gray-800 rounded h-4 relative overflow-hidden">
              <div
                className={`h-full ${isPlayer ? 'bg-emerald-500' : 'bg-cyan-600'}`}
                style={{ width: `${(pct / max) * 100}%` }}
              />
            </div>
            <div className="w-14 text-right text-white font-mono tabular-nums">
              {pct.toFixed(1)}%
            </div>
            <div
              className={`w-14 text-right text-[10px] font-mono tabular-nums ${
                delta > 0 ? 'text-emerald-400' : delta < 0 ? 'text-rose-400' : 'text-gray-500'
              }`}
            >
              {delta > 0 ? '+' : ''}
              {delta.toFixed(1)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function FinancialSummary({ fin }) {
  if (!fin || typeof fin !== 'object') return null;
  const revenue = fin.revenue || 0;
  const revenueDelta = fin.revenue_delta || 0;
  const gm = fin.gross_margin;
  const gmDelta = fin.gross_margin_delta || 0;
  const ni = fin.net_income;
  const niDelta = fin.net_income_delta || 0;

  return (
    <div className="grid grid-cols-3 gap-2">
      <div className="bg-gray-900/60 rounded p-2">
        <div className="text-[10px] text-gray-500 uppercase">Revenue</div>
        <div className="text-base font-bold text-white tabular-nums">{fmtMoney(revenue)}</div>
        <div
          className={`text-[10px] font-mono tabular-nums ${
            revenueDelta > 0 ? 'text-emerald-400' : revenueDelta < 0 ? 'text-rose-400' : 'text-gray-500'
          }`}
        >
          {revenueDelta > 0 ? '+' : ''}
          {fmtMoney(revenueDelta)}
        </div>
      </div>
      <div className="bg-gray-900/60 rounded p-2">
        <div className="text-[10px] text-gray-500 uppercase">Gross Margin</div>
        <div className="text-base font-bold text-white tabular-nums">
          {typeof gm === 'number' ? `${(gm * 100).toFixed(1)}%` : '—'}
        </div>
        <div
          className={`text-[10px] font-mono tabular-nums ${
            gmDelta > 0 ? 'text-emerald-400' : gmDelta < 0 ? 'text-rose-400' : 'text-gray-500'
          }`}
        >
          {gmDelta > 0 ? '+' : ''}
          {(gmDelta * 100).toFixed(1)}pt
        </div>
      </div>
      <div className="bg-gray-900/60 rounded p-2">
        <div className="text-[10px] text-gray-500 uppercase">Net Income</div>
        <div className="text-base font-bold text-white tabular-nums">{fmtMoney(ni)}</div>
        <div
          className={`text-[10px] font-mono tabular-nums ${
            niDelta > 0 ? 'text-emerald-400' : niDelta < 0 ? 'text-rose-400' : 'text-gray-500'
          }`}
        >
          {niDelta > 0 ? '+' : ''}
          {fmtMoney(niDelta)}
        </div>
      </div>
    </div>
  );
}

function KPIGrid({ kpis }) {
  if (!Array.isArray(kpis) || kpis.length === 0) return null;
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
      {kpis.map((k) => (
        <div key={k.id} className="bg-gray-900/60 rounded p-2 border border-gray-800">
          <div className="text-[10px] text-gray-500 uppercase">{k.label || k.id}</div>
          <div className="text-base font-bold text-white tabular-nums">
            {fmtKpiValue(k.value, k.format)}
          </div>
          <div className={`text-[10px] font-mono tabular-nums ${SENTIMENT_COLOR[k.sentiment] || 'text-gray-400'}`}>
            {SENTIMENT_ARROW[k.sentiment] || '•'}{' '}
            {typeof k.vs_prior === 'number' ? (k.vs_prior > 0 ? '+' : '') + k.vs_prior.toFixed(1) : '—'}
          </div>
        </div>
      ))}
    </div>
  );
}

function SegmentGrowth({ segments }) {
  if (!Array.isArray(segments) || segments.length === 0) return null;
  return (
    <div className="space-y-1">
      {segments.map((s) => (
        <div key={s.segment} className="flex items-center justify-between text-xs">
          <span className="text-gray-300">{s.segment}</span>
          <span
            className={`font-mono tabular-nums ${
              s.growth_pct > 0 ? 'text-emerald-400' : s.growth_pct < 0 ? 'text-rose-400' : 'text-gray-400'
            }`}
          >
            {s.growth_pct > 0 ? '+' : ''}
            {s.growth_pct.toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  );
}

export default function IndustryReportWidget({ payload, className = '' }) {
  if (!payload || typeof payload !== 'object') return null;
  const report = payload.report || {};
  const periodLabel = report.period_label || (payload.period_index ? `Q${payload.period_index}` : null);

  return (
    <div className={`bg-gray-900/60 border border-gray-700 rounded-xl p-5 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-lg font-bold text-white">📈 {payload.title || 'Industry Pulse'}</h3>
          {periodLabel && (
            <div className="text-[11px] text-gray-400 uppercase tracking-wider">{periodLabel}</div>
          )}
        </div>
        {payload.business_model && (
          <span className="text-[10px] text-cyan-300 bg-cyan-900/30 border border-cyan-700/40 rounded px-2 py-0.5 uppercase tracking-wider font-mono">
            {payload.business_model.replace(/_/g, ' ')}
          </span>
        )}
      </div>

      <section className="mb-4">
        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Market Share</h4>
        <MarketShareTable rows={report.market_share_table} />
      </section>

      <section className="mb-4">
        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Financials</h4>
        <FinancialSummary fin={report.financial_summary} />
      </section>

      {Array.isArray(report.kpi_grid) && report.kpi_grid.length > 0 && (
        <section className="mb-4">
          <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">KPIs</h4>
          <KPIGrid kpis={report.kpi_grid} />
        </section>
      )}

      {Array.isArray(report.segment_growth) && report.segment_growth.length > 0 && (
        <section className="mb-4">
          <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Segment Growth</h4>
          <SegmentGrowth segments={report.segment_growth} />
        </section>
      )}

      {report.exec_quote && (
        <div className="mt-3 text-xs italic text-gray-300 border-l-2 border-amber-500 pl-3 py-1">
          “{report.exec_quote}”
        </div>
      )}
    </div>
  );
}
