import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { THEME, gainLossColor } from './theme';
import ChartTab from './tabs/ChartTab';
import FundamentalsTab from './tabs/FundamentalsTab';
import TechnicalsTab from './tabs/TechnicalsTab';
import NewsTab from './tabs/NewsTab';
import PeersTab from './tabs/PeersTab';
import AboutTab from './tabs/AboutTab';
import { analystVerdict } from './npcDialog';

const TABS = [
  { id: 'chart', label: 'Chart' },
  { id: 'fundamentals', label: 'Fundamentals' },
  { id: 'technicals', label: 'Technicals' },
  { id: 'news', label: 'News' },
  { id: 'peers', label: 'Peers' },
  { id: 'about', label: 'About' },
];

export default function CompanyDrillDown({
  stock, quote, position, priceHistory = [], news = [], imageUrl, currentTick = 0,
  onClose, onTrade,
}) {
  const { t } = useTranslation();
  const [tab, setTab] = useState('chart');

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose?.(); }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const verdict = analystVerdict({
    pe: stock?.fundamentals?.pe,
    sector_pe: stock?.fundamentals?.sector_pe,
    roe: stock?.fundamentals?.roe,
    debt_equity: stock?.fundamentals?.debt_equity,
  });
  const change = Number.isFinite(quote?.last_change_pct) ? quote.last_change_pct : 0;

  return (
    <div
      data-testid="drilldown-backdrop"
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(60,40,10,0.4)',
        zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: '#fff', borderRadius: 12, padding: 12, maxWidth: 600, width: '100%',
          maxHeight: '90vh', overflowY: 'auto', border: `1px solid ${THEME.borderTile}`,
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
          <div style={{
            width: 80, height: 80, borderRadius: 10,
            background: imageUrl ? `url(${imageUrl}) center/cover` : `linear-gradient(135deg, ${THEME.accentWarm}, ${THEME.textMuted})`,
            flex: '0 0 auto',
          }} />
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontWeight: 800, fontSize: 14, color: THEME.textPrimary }}>{stock?.name} ({stock?.symbol})</div>
                <div style={{ color: THEME.textMuted, fontSize: 11 }}>{stock?.sector}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontWeight: 800, fontSize: 14, color: gainLossColor(change) }}>₹{quote?.mid?.toFixed(2) ?? '—'}</div>
                <div style={{ color: gainLossColor(change), fontSize: 10 }}>{change >= 0 ? '▲' : '▼'} {Math.abs(change).toFixed(2)}%</div>
              </div>
            </div>
            <div style={{ marginTop: 6, fontSize: 11, color: THEME.textPrimary }}>
              🤖 <strong>Analyst:</strong> {t(verdict.key, verdict.props)}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 4, borderBottom: `2px solid ${THEME.borderTile}`, marginBottom: 8 }}>
          {TABS.map(tb => (
            <button
              key={tb.id}
              data-testid={`drilldown-tab-${tb.id}`}
              data-active={tab === tb.id ? 'true' : 'false'}
              onClick={() => setTab(tb.id)}
              style={{
                padding: '4px 10px', border: 'none', cursor: 'pointer',
                background: tab === tb.id ? THEME.bgTile : 'transparent',
                color: tab === tb.id ? THEME.textPrimary : THEME.textMuted,
                fontWeight: tab === tb.id ? 700 : 500,
                borderRadius: '6px 6px 0 0', fontSize: 11,
              }}
            >{tb.label}</button>
          ))}
        </div>

        {/* Body */}
        {tab === 'chart' && <ChartTab priceHistory={priceHistory} indicators={{ rsi: quote?.rsi }} />}
        {tab === 'fundamentals' && <FundamentalsTab fundamentals={stock?.fundamentals} />}
        {tab === 'technicals' && <TechnicalsTab priceHistory={priceHistory} />}
        {tab === 'news' && <NewsTab news={news} symbol={stock?.symbol} currentTick={currentTick} />}
        {tab === 'peers' && <PeersTab peers={stock?.peers} stockCfg={stock} />}
        {tab === 'about' && <AboutTab about={stock?.about} imageUrl={imageUrl} />}

        {/* Trade footer */}
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', background: THEME.bgTile, borderRadius: 8, padding: 8, marginTop: 10 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 9, color: THEME.textMuted }}>YOU OWN</div>
            <div style={{ fontWeight: 700, fontSize: 12, color: THEME.textPrimary }}>
              {position?.qty ? `${position.qty} shares · cost ₹${position.cost_basis?.toFixed?.(2) ?? '—'}` : '—'}
            </div>
          </div>
          <button onClick={() => onTrade?.('buy', { symbol: stock?.symbol })} style={{ background: THEME.gain, color: '#fff', border: 'none', padding: '6px 14px', borderRadius: 18, fontWeight: 700, fontSize: 11, cursor: 'pointer' }}>Buy</button>
          <button onClick={() => onTrade?.('sell', { symbol: stock?.symbol })} style={{ background: THEME.loss, color: '#fff', border: 'none', padding: '6px 14px', borderRadius: 18, fontWeight: 700, fontSize: 11, cursor: 'pointer' }}>Sell</button>
        </div>
      </div>
    </div>
  );
}
