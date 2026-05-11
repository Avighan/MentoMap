import React from 'react';
import { useTranslation } from 'react-i18next';
import { THEME } from '../theme';
import { analystVerdict } from '../npcDialog';

function Cell({ label, value, color }) {
  return (
    <div style={{ background: THEME.bgTile, borderRadius: 6, padding: 6 }}>
      <div style={{ fontSize: 9, color: THEME.textMuted, fontWeight: 600 }}>{label}</div>
      <div style={{ fontWeight: 700, color: color || THEME.textPrimary, fontSize: 12 }}>{value ?? '—'}</div>
    </div>
  );
}

export default function FundamentalsTab({ fundamentals }) {
  const { t } = useTranslation();
  const f = fundamentals || {};
  const verdict = analystVerdict({
    pe: f.pe, sector_pe: f.sector_pe, roe: f.roe, debt_equity: f.debt_equity,
  });
  const grid = { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6 };
  const sectionLabel = { fontSize: 10, color: THEME.textMuted, fontWeight: 700, margin: '8px 0 4px' };

  return (
    <div>
      <div style={sectionLabel}>VALUATION</div>
      <div style={grid}>
        <Cell label="P/E" value={f.pe} />
        <Cell label="P/B" value={f.pb} />
        <Cell label="EV/EBITDA" value={f.ev_ebitda} />
        <Cell label="PEG" value={f.peg} />
      </div>
      <div style={sectionLabel}>PROFITABILITY &amp; HEALTH</div>
      <div style={grid}>
        <Cell label="EPS (TTM)" value={f.eps_ttm != null ? `₹${f.eps_ttm}` : '—'} />
        <Cell label="ROE" value={f.roe != null ? `${f.roe}%` : '—'} color={THEME.gain} />
        <Cell label="ROCE" value={f.roce != null ? `${f.roce}%` : '—'} color={THEME.gain} />
        <Cell label="DEBT/EQ" value={f.debt_equity} />
      </div>
      <div style={sectionLabel}>SIZE &amp; OWNERSHIP</div>
      <div style={grid}>
        <Cell label="MARKET CAP" value={f.market_cap_cr != null ? `₹${(f.market_cap_cr / 100000).toFixed(1)}L Cr` : '—'} />
        <Cell label="FREE FLOAT" value={f.free_float_pct != null ? `${f.free_float_pct}%` : '—'} />
        <Cell label="PROMOTER" value={f.promoter_pct != null ? `${f.promoter_pct}%` : '—'} />
        <Cell label="FII / DII" value={(f.fii_pct != null && f.dii_pct != null) ? `${f.fii_pct}% / ${f.dii_pct}%` : '—'} />
      </div>
      {Array.isArray(f.quarterly_revenue_cr) && f.quarterly_revenue_cr.length === 4 && (
        <>
          <div style={sectionLabel}>QUARTERLY REVENUE (₹ Cr)</div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end', height: 60, background: THEME.bgTile, borderRadius: 6, padding: 6 }}>
            {(() => {
              const maxRev = Math.max(...f.quarterly_revenue_cr);
              return f.quarterly_revenue_cr.map((q, i) => {
                const h = (q / maxRev) * 48;
                const rising = i > 0 && q >= f.quarterly_revenue_cr[i - 1];
                return (
                  <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                    <div style={{ background: rising ? THEME.gain : THEME.textMuted, width: 18, height: h, borderRadius: '3px 3px 0 0' }} />
                    <div style={{ fontSize: 9, color: THEME.textMuted }}>Q{i + 1} · {q}</div>
                  </div>
                );
              });
            })()}
          </div>
        </>
      )}
      <div style={sectionLabel}>RANGES &amp; SIGNALS</div>
      <div style={grid}>
        <Cell label="52W RANGE" value={(f.fifty_two_week_low != null && f.fifty_two_week_high != null) ? `${f.fifty_two_week_low} — ${f.fifty_two_week_high}` : '—'} />
        <Cell label="DIV YIELD" value={f.div_yield_pct != null ? `${f.div_yield_pct}%` : '—'} />
        <Cell label="BETA" value={f.beta} />
        <Cell label="VOLUME (T)" value={f.volume_x_avg != null ? `${f.volume_x_avg}× avg` : '—'} />
      </div>
      <div style={{ background: '#FEF3C7', borderRadius: 6, padding: 8, marginTop: 8, borderLeft: `3px solid ${THEME.accentWarm}` }}>
        <div style={{ fontSize: 9, color: THEME.textMuted, fontWeight: 700 }}>🤖 ANALYST</div>
        <div style={{ fontSize: 11, color: THEME.textPrimary }}>{t(verdict.key, verdict.props)}</div>
      </div>
    </div>
  );
}
