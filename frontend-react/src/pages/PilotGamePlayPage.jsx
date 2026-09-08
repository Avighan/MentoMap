/**
 * PilotGamePlayPage — real play-through UI for the three Phase 1 pilot
 * games (dealcraft, mumbai_manufacturer, heliogrid). These have a
 * different backend contract than the legacy generic engine GamePlayPage.jsx
 * uses (routes/grader_routes.py's per-game /choose, /quarter, /complete
 * endpoints — see that file's docstring), and GamePlayPage.jsx itself
 * depends on ~50 other components/contexts that were never committed to
 * this repo (a much larger gap than the "restore the bootstrap files"
 * scope this page fills) — so this is a new, focused page rather than an
 * attempt to route pilot games through that page.
 *
 * Design is grounded in two references, not invented:
 *   1. MentoMap's own visual language (HomePage.jsx's `colors`, framer-motion,
 *      react-icons, card layouts).
 *   2. reference/simulok-source/index.html — the original Simulok app these
 *      three games were ported from. Its renderRound()/renderOutcome()
 *      functions establish the real shape this needed: a sticky KPI
 *      dashboard with delta flashes, a per-choice cost/impact preview, and
 *      — the piece an earlier pass of this page skipped entirely — a
 *      "Decision Outcome" interstitial after every choice (feedback text +
 *      KPI deltas + a learning takeaway) before advancing, not an instant
 *      jump to the next round. That interstitial is the actual substance of
 *      these being *educational* simulations rather than a quiz, so it's
 *      reproduced here using MentoMap's own game JSON fields (each choice's
 *      `effects` + `feedback`) rather than inventing new content.
 *
 * HelioGrid has no full implementation in the Simulok reference (only a
 * catalog teaser — see that file's README) — its lever form here is built
 * directly from backend/games/heliogrid_engine.py's validate_action(),
 * which is the real, authoritative contract.
 *
 * Backend routes exercised here, all real (see backend/routes/grader_routes.py):
 *   POST /api/run/start                          -> { run_id, game_data, ... }
 *   POST /api/run/<id>/dealcraft/choose           { round_id, choice_id }
 *   POST /api/run/<id>/mumbai_manufacturer/choose { round_id, choice_id, event_choice_id? }
 *   POST /api/run/<id>/heliogrid/quarter          { action }
 *   POST /api/run/<id>/complete                   -> { summary: { score, band, dimension_scores } }
 */
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  FaArrowLeft, FaTrophy, FaChartLine, FaGamepad, FaSpinner, FaExclamationTriangle,
  FaLightbulb, FaArrowRight, FaTag, FaUsers, FaBullhorn, FaFlask, FaSlidersH,
  FaPercent, FaChartPie, FaWallet, FaBoxOpen, FaRupeeSign, FaSmile,
  FaQuoteLeft, FaListOl, FaCheckCircle, FaBuilding, FaGraduationCap,
} from 'react-icons/fa';
import { startGame, dealcraftChoose, mumbaiManufacturerChoose, heliogridQuarter, completePilotRun } from '../api/games';
import { LoadingState } from '../components/ui/LoadingSpinner';
import RobotGuide from '../assets/robo.png';
import dealcraftImg from '../assets/games/dealcraft.jpg';
import mumbaiImg from '../assets/games/mumbai_manufacturer.jpg';
import heliogridImg from '../assets/games/heliogrid.jpg';

// Real Simulok cover photography (reference/simulok-source/assets/sim/) —
// the actual hero images each game's original implementation shipped with,
// not stock placeholders.
const HERO_IMAGES = {
  dealcraft: dealcraftImg,
  mumbai_manufacturer: mumbaiImg,
  heliogrid: heliogridImg,
};

const colors = {
  primary: '#FFD166',
  primaryLight: '#FFE8A5',
  primaryDark: '#FFC145',
  background: '#FFFDF7',
  card: '#FFFFFF',
  text: '#2D3047',
  textLight: '#6D7286',
  purple: '#6C5CE7',
  teal: '#4ECDC4',
  green: '#1E8A5A',
  red: '#C0392B',
};

const GAME_META = {
  dealcraft: {
    icon: '🤝', accent: colors.purple, label: 'Negotiation Simulation',
    headlineKpis: ['cash', 'reputation', 'skills', 'energy', 'integrity'],
  },
  mumbai_manufacturer: {
    icon: '🏭', accent: colors.teal, label: 'Operations & Manufacturing',
    headlineKpis: ['cash', 'current_inventory', 'customer_satisfaction', 'reputation', 'bank_debt'],
  },
  heliogrid: {
    icon: '☀️', accent: colors.primaryDark, label: 'Marketing Strategy Simulation',
    headlineKpis: [],
  },
};

const PILOT_GAME_IDS = new Set(Object.keys(GAME_META));

// Reused from Simulok's own outcome-screen labelMap (reference/simulok-source/index.html,
// renderOutcome()) — the same field names, since these games were ported from there.
const KPI_LABELS = {
  cash: 'Cash', reputation: 'Reputation', skills: 'Skill', energy: 'Energy', integrity: 'Integrity',
  current_inventory: 'Inventory', wip_inventory: 'WIP Inventory', safety_stock: 'Safety Stock',
  customer_satisfaction: 'Customer Satisfaction', working_capital_efficiency: 'WC Efficiency',
  quality_score: 'Quality', supplier_reliability: 'Supplier Reliability',
  tata_relationship: 'Tata Relationship', bajaj_relationship: 'Bajaj Relationship',
  mahindra_relationship: 'Mahindra Relationship', production_capacity: 'Capacity Index',
  supply_chain_cost_ratio: 'SC Cost Ratio', ev_readiness: 'EV Readiness',
  digital_maturity: 'Digital Maturity', sustainability_score: 'Sustainability',
  bullwhip_index: 'Bullwhip Pressure', bank_debt: 'Bank Debt',
};

const RANK_STYLES = {
  A: { bg: '#D1FAE5', text: '#065F46' },
  B: { bg: '#DBEAFE', text: '#1E40AF' },
  C: { bg: '#FEF3C7', text: '#92400E' },
  D: { bg: '#FFE4E6', text: '#9F1239' },
  F: { bg: '#FEE2E2', text: '#991B1B' },
};

const SEGMENT_LABELS = {
  campus_estates: 'Campus Estates', process_plants: 'Process Plants',
  retail_chains: 'Retail Chains', installer_guild: 'Installer Guild',
};

function kpiLabel(key) {
  return KPI_LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function fmtNum(n) {
  if (typeof n !== 'number') return n;
  if (Math.abs(n) >= 1000) return n.toLocaleString('en-IN');
  return Math.round(n * 10) / 10;
}

// Reused from Simulok's own quarterDataRows() label map (reference/simulok-source/
// index.html) — the "Key data this stage" table shown per round, e.g. Dealcraft's
// negotiation deadline/target value or Mumbai's demand/holding-cost figures.
const QUARTER_DATA_LABELS = {
  deadline: 'Deadline', target_value: 'Target Value', known_alternatives: 'Known Alternatives',
  demand: 'Quarterly Demand', variance: 'Demand Variance', setup_cost: 'Setup Cost / Order',
  holding_cost: 'Holding Cost / Unit', stockout_cost: 'Stockout Cost / Unit', lead_time_days: 'Lead Time',
  customer_stated_demand: 'Customer Stated Demand', market_actual_demand: 'Market Actual Demand',
  production_capacity_max: 'Max Production Capacity', overtime_capacity: 'Overtime Capacity',
  overtime_cost_per_unit: 'Overtime Cost / Unit', total_demand: 'Total Demand',
  production_capacity: 'Current Capacity', capacity_gap: 'Capacity Gap',
  q4_demand: 'Q4 Peak Demand', q1_demand: 'Q1 Trough Demand', regular_capacity: 'Regular Capacity',
  storage_capacity_max: 'Max Storage', peak_trough_ratio: 'Peak / Trough Ratio',
  storage_cost_per_unit: 'Storage Cost / Unit',
};

function quarterDataRows(data) {
  return Object.entries(data || {}).map(([k, v]) => {
    let shown = v;
    if (k === 'variance' && typeof v === 'number') shown = `${v * 100}%`;
    else if (typeof v === 'number' && /cost|value/i.test(k)) shown = `₹${fmtNum(v)}`;
    else if (typeof v === 'number' && k.includes('days')) shown = `${v} days`;
    else if (typeof v === 'number') shown = v.toLocaleString('en-IN');
    const label = QUARTER_DATA_LABELS[k] || k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
    return [label, shown];
  });
}

function TopBar({ title, icon, heroImage, onBack }) {
  return (
    <div className="sticky top-0 z-20 bg-white/90 backdrop-blur-sm border-b shadow-sm">
      <div className="max-w-3xl mx-auto px-4 py-2.5 flex items-center gap-3">
        <button
          onClick={onBack}
          className="flex items-center justify-center w-9 h-9 rounded-lg hover:bg-gray-100 transition-colors flex-shrink-0"
          aria-label="Back to games"
        >
          <FaArrowLeft style={{ color: colors.text }} />
        </button>
        {heroImage ? (
          <img src={heroImage} alt="" className="w-10 h-10 rounded-lg object-cover flex-shrink-0 shadow" />
        ) : (
          <span className="text-2xl">{icon}</span>
        )}
        <h1 className="text-lg font-bold truncate" style={{ color: colors.text }}>{title}</h1>
      </div>
    </div>
  );
}

function ProgressBar({ current, total, accent }) {
  const pct = Math.min(100, Math.round((current / total) * 100));
  return (
    <div className="max-w-3xl mx-auto px-4 pt-4">
      <div className="flex justify-between text-xs font-semibold mb-1" style={{ color: colors.textLight }}>
        <span>Step {current} of {total}</span>
        <span>{pct}%</span>
      </div>
      <div className="w-full h-2 rounded-full bg-gray-100 overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: accent }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4 }}
        />
      </div>
    </div>
  );
}

/** Sticky KPI dashboard — mirrors Simulok's .kpi-bar (renderKpis()): a row of
 * cards that flash green/red briefly when a value moves. */
function KpiBar({ keys, state, prevState }) {
  if (!keys.length) return null;
  return (
    <div className="sticky top-[57px] z-10 bg-white border-b shadow-sm">
      <div className="max-w-3xl mx-auto px-4 py-2.5 grid gap-2" style={{ gridTemplateColumns: `repeat(${keys.length}, 1fr)` }}>
        {keys.map((key) => {
          const value = state?.[key] ?? 0;
          const prev = prevState?.[key];
          const delta = typeof prev === 'number' ? value - prev : 0;
          const flash = delta > 0 ? 'bg-green-50' : delta < 0 ? 'bg-red-50' : 'bg-gray-50';
          return (
            <motion.div
              key={key}
              className={`rounded-lg px-2 py-1.5 text-center ${flash}`}
              animate={{ scale: delta !== 0 ? [1, 1.06, 1] : 1 }}
              transition={{ duration: 0.4 }}
            >
              <div className="text-[10px] font-bold uppercase tracking-wide truncate" style={{ color: colors.textLight }}>
                {kpiLabel(key)}
              </div>
              <div className="text-sm font-extrabold" style={{ color: colors.text }}>{fmtNum(value)}</div>
              {delta !== 0 && (
                <div className="text-[10px] font-bold" style={{ color: delta > 0 ? colors.green : colors.red }}>
                  {delta > 0 ? '+' : ''}{fmtNum(delta)}
                </div>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

/** Post-choice "Decision Outcome" screen — feedback text + KPI deltas + a
 * learning takeaway, matching Simulok's renderOutcome(). Advances only when
 * the player clicks Continue, rather than auto-skipping to the next round. */
function OutcomeScreen({ title, feedback, deltas, learning, concepts, onContinue, isLast }) {
  const deltaEntries = Object.entries(deltas || {}).filter(([, v]) => v !== 0);
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-2xl shadow-md p-6"
    >
      <div className="text-xs font-bold uppercase tracking-wide mb-2" style={{ color: colors.textLight }}>
        Decision Outcome
      </div>
      <h2 className="text-lg font-bold mb-3" style={{ color: colors.text }}>{title}</h2>

      <div className="flex gap-3 p-4 rounded-xl mb-4" style={{ backgroundColor: colors.primaryLight + '40' }}>
        <FaLightbulb className="flex-shrink-0 mt-0.5" style={{ color: colors.primaryDark }} />
        <p className="text-sm" style={{ color: colors.text }}>{feedback}</p>
      </div>

      {deltaEntries.length > 0 && (
        <div className="mb-5">
          <div className="text-xs font-bold uppercase tracking-wide mb-2" style={{ color: colors.textLight }}>
            Impact
          </div>
          <ul className="grid grid-cols-2 gap-x-4 gap-y-1.5">
            {deltaEntries.map(([key, val]) => (
              <li key={key} className="flex justify-between text-sm">
                <span style={{ color: colors.textLight }}>{kpiLabel(key)}</span>
                <span className="font-bold" style={{ color: val > 0 ? colors.green : colors.red }}>
                  {val > 0 ? '+' : ''}{fmtNum(val)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {learning && (
        <div className="mb-5 rounded-xl p-4 border-l-4" style={{ borderColor: colors.teal, backgroundColor: colors.teal + '0D' }}>
          <div className="flex items-center gap-1.5 text-sm font-extrabold mb-1.5" style={{ color: colors.text }}>
            <FaGraduationCap style={{ color: colors.teal }} /> {learning.key_concept || 'Key Learning'}
          </div>
          <div className="text-xs space-y-1" style={{ color: colors.textLight }}>
            {learning.formula && <p><strong style={{ color: colors.text }}>Formula:</strong> {learning.formula}</p>}
            {learning.principle && <p><strong style={{ color: colors.text }}>Principle:</strong> {learning.principle}</p>}
            {learning.application && <p><strong style={{ color: colors.text }}>Application:</strong> {learning.application}</p>}
            {learning.trade_offs && <p><strong style={{ color: colors.text }}>Trade-offs:</strong> {learning.trade_offs}</p>}
            {concepts?.length > 0 && <p><strong style={{ color: colors.text }}>Concepts:</strong> {concepts.join(', ')}</p>}
          </div>
        </div>
      )}

      <button
        onClick={onContinue}
        className="w-full py-3 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg"
        style={{ backgroundColor: colors.primary, color: colors.text }}
      >
        {isLast ? 'See Final Results' : 'Continue'} <FaArrowRight />
      </button>
    </motion.div>
  );
}

// heliogrid's real lever schema, from backend/games/heliogrid_engine.py's
// validate_action(): listPrice/headcount/commsSpend/researchSpend required;
// discounts per segment in [0,20]; salesAlloc per segment must sum to ~100;
// featureSpend optional; total spend must not exceed initial_state.budget.
function HeliogridLeverForm({ game, onSubmit, submitting }) {
  const segments = Object.keys(game.segments || {});
  const budget = game.initial_state?.budget || 420000;
  const rivalPrice = game.initial_state?.rival?.price || 160000;

  const [listPrice, setListPrice] = useState(game.initial_state?.listPrice || rivalPrice);
  const [headcount, setHeadcount] = useState(game.initial_state?.headcount || 10);
  const [commsSpend, setCommsSpend] = useState(40000);
  const [researchSpend, setResearchSpend] = useState(20000);
  const [discounts, setDiscounts] = useState(() => Object.fromEntries(segments.map((s) => [s, 5])));
  const [allocRaw, setAllocRaw] = useState(() => Object.fromEntries(segments.map((s) => [s, 25])));
  const [featureSpend, setFeatureSpend] = useState({ efficiency: 5000, mass: 0, latency: 5000 });

  const allocTotal = Object.values(allocRaw).reduce((a, b) => a + b, 0) || 1;
  const normalizedAlloc = Object.fromEntries(
    segments.map((s) => [s, Math.round((allocRaw[s] / allocTotal) * 1000) / 10])
  );
  const totalSpend = commsSpend + researchSpend + Object.values(featureSpend).reduce((a, b) => a + b, 0);
  const overBudget = totalSpend > budget;

  const handleSubmit = () => {
    if (overBudget) return;
    onSubmit({
      listPrice,
      headcount,
      commsSpend,
      researchSpend,
      discounts,
      salesAlloc: normalizedAlloc,
      featureSpend,
    });
  };

  const Slider = ({ label, value, onChange, min, max, step = 1, suffix = '', accent = colors.primaryDark }) => (
    <div className="mb-4 last:mb-0">
      <div className="flex justify-between text-xs font-semibold mb-1.5" style={{ color: colors.text }}>
        <span>{label}</span>
        <span className="font-extrabold" style={{ color: accent }}>{fmtNum(value)}{suffix}</span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-2 rounded-full appearance-none cursor-pointer"
        style={{ accentColor: accent, backgroundColor: '#F0EFE9' }}
      />
    </div>
  );

  const Section = ({ icon, title, subtitle, accent, children }) => (
    <div className="mb-5 rounded-xl p-4 border-l-4" style={{ borderColor: accent, backgroundColor: accent + '0D' }}>
      <div className="flex items-center gap-2 mb-1">
        <span className="flex items-center justify-center w-7 h-7 rounded-lg text-white text-xs flex-shrink-0" style={{ backgroundColor: accent }}>
          {icon}
        </span>
        <div className="text-sm font-extrabold" style={{ color: colors.text }}>{title}</div>
      </div>
      {subtitle && <p className="text-xs mb-3 ml-9" style={{ color: colors.textLight }}>{subtitle}</p>}
      <div className="mt-3">{children}</div>
    </div>
  );

  const spendPct = Math.min(100, Math.round((totalSpend / budget) * 100));

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-2xl shadow-md p-6">
      <div className="flex items-center gap-2 mb-4">
        <FaSlidersH style={{ color: colors.primaryDark }} />
        <div className="text-sm font-extrabold uppercase tracking-wide" style={{ color: colors.text }}>
          This Quarter's Levers
        </div>
      </div>

      <Section icon={<FaTag />} title="Pricing & Team" subtitle="Your headline price vs. the rival, and how many people are selling it." accent={colors.purple}>
        <Slider label="List Price (₹)" value={listPrice} onChange={setListPrice} min={100000} max={250000} step={1000} accent={colors.purple} />
        <Slider label="Headcount" value={headcount} onChange={setHeadcount} min={5} max={30} accent={colors.purple} />
      </Section>

      <Section icon={<FaBullhorn />} title="Marketing & R&D Spend" subtitle="Comms drives awareness this quarter; R&D compounds product quality over time." accent={colors.teal}>
        <Slider label="Marketing / Comms Spend (₹)" value={commsSpend} onChange={setCommsSpend} min={0} max={150000} step={1000} accent={colors.teal} />
        <Slider label="R&D Spend (₹)" value={researchSpend} onChange={setResearchSpend} min={0} max={150000} step={1000} accent={colors.teal} />
      </Section>

      <Section icon={<FaFlask />} title="Feature Investment" subtitle="Where R&D actually goes: efficiency, weight, or response latency." accent={colors.primaryDark}>
        <Slider label="Efficiency" value={featureSpend.efficiency} onChange={(v) => setFeatureSpend((f) => ({ ...f, efficiency: v }))} min={0} max={50000} step={1000} accent={colors.primaryDark} />
        <Slider label="Mass Reduction" value={featureSpend.mass} onChange={(v) => setFeatureSpend((f) => ({ ...f, mass: v }))} min={0} max={50000} step={1000} accent={colors.primaryDark} />
        <Slider label="Latency" value={featureSpend.latency} onChange={(v) => setFeatureSpend((f) => ({ ...f, latency: v }))} min={0} max={50000} step={1000} accent={colors.primaryDark} />
      </Section>

      <Section icon={<FaPercent />} title="Per-Segment Discount" subtitle="0–20% off list price, set independently for each customer segment." accent={colors.red}>
        {segments.map((s) => (
          <Slider key={s} label={SEGMENT_LABELS[s] || s} value={discounts[s]} onChange={(v) => setDiscounts((d) => ({ ...d, [s]: v }))} min={0} max={20} suffix="%" accent={colors.red} />
        ))}
      </Section>

      <Section icon={<FaChartPie />} title="Sales Allocation" subtitle="Where your sales team focuses effort — auto-normalized to 100%." accent={colors.green}>
        {segments.map((s) => (
          <Slider key={s} label={`${SEGMENT_LABELS[s] || s} — ${normalizedAlloc[s]}%`} value={allocRaw[s]} onChange={(v) => setAllocRaw((a) => ({ ...a, [s]: v }))} min={0} max={100} suffix=" raw" accent={colors.green} />
        ))}
      </Section>

      <div className="mb-5">
        <div className="flex justify-between items-center text-sm font-bold mb-1.5">
          <span className="flex items-center gap-1.5" style={{ color: colors.text }}><FaWallet style={{ color: overBudget ? colors.red : colors.green }} /> Quarterly Spend</span>
          <span style={{ color: overBudget ? colors.red : colors.green }}>₹{fmtNum(totalSpend)} / ₹{fmtNum(budget)}</span>
        </div>
        <div className="w-full h-3 rounded-full bg-gray-100 overflow-hidden">
          <motion.div
            className="h-full rounded-full"
            style={{ backgroundColor: overBudget ? colors.red : colors.green }}
            initial={{ width: 0 }}
            animate={{ width: `${spendPct}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
        {overBudget && <p className="text-xs font-bold mt-1.5" style={{ color: colors.red }}>Over budget — reduce spend to lock in this quarter.</p>}
      </div>

      <button
        onClick={handleSubmit}
        disabled={submitting || overBudget}
        className="w-full py-3.5 rounded-xl font-bold text-white disabled:opacity-60 shadow-lg flex items-center justify-center gap-2"
        style={{ backgroundColor: colors.primaryDark, color: colors.text }}
      >
        {submitting ? <><FaSpinner className="animate-spin" /> Resolving quarter…</> : <>Lock In This Quarter <FaArrowRight /></>}
      </button>
    </motion.div>
  );
}

const HELIOGRID_METRIC_META = {
  units_sold: { label: 'Units Sold', icon: <FaBoxOpen />, accent: '#118AB2' },
  revenue: { label: 'Revenue', icon: <FaRupeeSign />, accent: '#4ECDC4', money: true },
  profit: { label: 'Profit', icon: <FaChartLine />, accent: '#1E8A5A', money: true },
  market_share_pct: { label: 'Market Share', icon: <FaChartPie />, accent: '#6C5CE7', pct: true },
  csat: { label: 'Customer Satisfaction', icon: <FaSmile />, accent: '#FFC145' },
};

function HeliogridOutcome({ result, prevResult, segmentLabel, onContinue, isLast }) {
  if (!result) return null;
  const rows = [
    ['units_sold', result.units_sold],
    ['revenue', result.revenue],
    ['profit', result.profit],
    ['market_share_pct', result.market_share_pct],
    ['csat', result.csat],
  ];
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-2xl shadow-md p-6">
      <div className="text-xs font-bold uppercase tracking-wide mb-2" style={{ color: colors.textLight }}>
        Quarter {result.quarter_index + 1} Results
      </div>
      <h2 className="text-lg font-bold mb-4" style={{ color: colors.text }}>
        Focus segment: {segmentLabel}
      </h2>
      <div className="grid grid-cols-2 gap-3 mb-5">
        {rows.map(([key, raw]) => {
          const meta = HELIOGRID_METRIC_META[key];
          const prev = prevResult?.[key];
          const delta = typeof prev === 'number' ? raw - prev : null;
          const value = meta.money ? `₹${fmtNum(raw)}` : meta.pct ? `${fmtNum(raw)}%` : fmtNum(raw);
          return (
            <div key={key} className="p-3 rounded-xl" style={{ backgroundColor: meta.accent + '14' }}>
              <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase mb-1" style={{ color: meta.accent }}>
                {meta.icon} {meta.label}
              </div>
              <div className="text-lg font-extrabold" style={{ color: key === 'profit' && raw < 0 ? colors.red : colors.text }}>
                {value}
              </div>
              {delta !== null && Math.abs(delta) > 0.05 && (
                <div className="text-xs font-bold mt-0.5" style={{ color: delta > 0 ? colors.green : colors.red }}>
                  {delta > 0 ? '▲' : '▼'} {delta > 0 ? '+' : ''}{fmtNum(delta)} vs last quarter
                </div>
              )}
            </div>
          );
        })}
      </div>
      <button
        onClick={onContinue}
        className="w-full py-3 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg"
        style={{ backgroundColor: colors.primary, color: colors.text }}
      >
        {isLast ? 'See Final Results' : 'Next Quarter'} <FaArrowRight />
      </button>
    </motion.div>
  );
}

export default function PilotGamePlayPage() {
  const { gameId } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [runId, setRunId] = useState(null);
  const [game, setGame] = useState(null);
  const [showBriefing, setShowBriefing] = useState(true);
  const [roundIndex, setRoundIndex] = useState(0);
  const [quarterIndex, setQuarterIndex] = useState(0);
  const [state, setState] = useState(null);
  const [prevState, setPrevState] = useState(null);
  const [phase, setPhase] = useState('choice'); // 'choice' | 'outcome' | 'complete'
  const [pendingOutcome, setPendingOutcome] = useState(null);
  const [prevQuarterResult, setPrevQuarterResult] = useState(null);
  const [summary, setSummary] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const meta = GAME_META[gameId] || { icon: '🎮', accent: colors.primaryDark, label: 'Simulation', headlineKpis: [] };

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    startGame(gameId)
      .then((data) => {
        if (cancelled) return;
        setRunId(data.run_id);
        setGame(data.game_data);
        setState(data.game_data?.initial_state || null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err?.response?.data?.error || 'Could not start this game.');
      })
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [gameId]);

  const totalQuarters = game?.quarters || 8;
  const focusRotation = game?.segment_focus_rotation || [];

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4" style={{ backgroundColor: colors.background }}>
        <FaSpinner className="animate-spin text-3xl" style={{ color: colors.purple }} />
        <LoadingState label="Starting your run…" />
      </div>
    );
  }

  if (error && !game) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4" style={{ backgroundColor: colors.background }}>
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md text-center">
          <FaExclamationTriangle className="text-3xl mx-auto mb-3 text-red-500" />
          <p className="text-gray-700 mb-4">{error}</p>
          <button onClick={() => navigate('/games')} className="px-4 py-2 rounded-lg font-bold shadow-lg" style={{ backgroundColor: colors.primary, color: colors.text }}>
            Back to games
          </button>
        </div>
      </div>
    );
  }

  if (!PILOT_GAME_IDS.has(gameId)) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4" style={{ backgroundColor: colors.background }}>
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-lg text-center">
          <img src={RobotGuide} alt="" className="w-16 h-16 mx-auto mb-4" />
          <p className="text-gray-700 mb-2">
            <strong>"{game?.title || gameId}"</strong> isn't wired into the rebuilt UI yet — only
            Dealcraft, Mumbai Manufacturer, and HelioGrid have a play screen so far.
          </p>
          <p className="text-sm text-gray-400 mb-4">A run was started for it on the backend (run id: {runId}).</p>
          <button onClick={() => navigate('/games')} className="px-4 py-2 rounded-lg font-bold shadow-lg" style={{ backgroundColor: colors.primary, color: colors.text }}>
            Back to games
          </button>
        </div>
      </div>
    );
  }

  // ---------- Briefing screen (once, before Round 1 / Quarter 1) ----------
  if (showBriefing) {
    const hero = HERO_IMAGES[gameId];
    const briefing = game.briefing || {};
    const profileRows = briefing.profile || [];
    const companyProfileRows = briefing.company_profile || [];
    const resourceRows = briefing.starting_resources || [];
    return (
      <div className="min-h-screen flex items-center justify-center px-4 py-10" style={{ backgroundColor: colors.background }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-3xl shadow-2xl overflow-hidden max-w-2xl w-full bg-white"
        >
          <div
            className="h-56 relative flex flex-col justify-end p-6"
            style={{
              backgroundImage: hero
                ? `linear-gradient(to top, rgba(0,0,0,0.85) 10%, rgba(0,0,0,0.15)), url(${hero})`
                : `linear-gradient(135deg, ${meta.accent}, ${colors.purple})`,
              backgroundSize: 'cover',
              backgroundPosition: 'center',
            }}
          >
            <span
              className="self-start mb-2 text-[11px] font-bold uppercase tracking-wide px-2.5 py-1 rounded-full text-white"
              style={{ backgroundColor: meta.accent }}
            >
              {meta.icon} {meta.label}
            </span>
            <h1 className="text-2xl font-extrabold text-white drop-shadow-lg leading-tight">{game.title}</h1>
          </div>

          <div className="p-7 max-h-[65vh] overflow-y-auto">
            <p className="text-sm leading-relaxed mb-4" style={{ color: colors.text }}>
              {briefing.narrative || game.description}
            </p>

            {briefing.quote && (
              <div className="flex gap-3 p-4 rounded-xl mb-5" style={{ backgroundColor: meta.accent + '14' }}>
                <FaQuoteLeft className="flex-shrink-0 mt-0.5" style={{ color: meta.accent }} />
                <p className="text-sm italic font-medium" style={{ color: colors.text }}>{briefing.quote}</p>
              </div>
            )}

            {profileRows.length > 0 && (
              <div className="grid grid-cols-2 gap-2.5 mb-5">
                {profileRows.map((p) => (
                  <div key={p.label} className="rounded-lg px-3 py-2 bg-gray-50">
                    <div className="text-[10px] font-bold uppercase tracking-wide" style={{ color: colors.textLight }}>{p.label}</div>
                    <div className="text-sm font-bold" style={{ color: colors.text }}>{p.value}</div>
                  </div>
                ))}
              </div>
            )}

            {companyProfileRows.length > 0 && (
              <div className="mb-5">
                <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide mb-2" style={{ color: colors.textLight }}>
                  <FaBuilding /> Company Profile
                </div>
                <div className="grid grid-cols-2 gap-2.5">
                  {companyProfileRows.map((p) => (
                    <div key={p.label} className="rounded-lg px-3 py-2 bg-gray-50">
                      <div className="text-[10px] font-bold uppercase tracking-wide" style={{ color: colors.textLight }}>{p.label}</div>
                      <div className="text-sm font-bold" style={{ color: colors.text }}>{p.value}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {resourceRows.length > 0 && (
              <div className="mb-5">
                <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide mb-2" style={{ color: colors.textLight }}>
                  <FaWallet /> Starting Resources
                </div>
                <div className="rounded-lg overflow-hidden border border-gray-100">
                  {resourceRows.map((p, idx) => (
                    <div key={p.label} className={`flex justify-between px-3 py-2 text-sm ${idx % 2 ? 'bg-gray-50' : 'bg-white'}`}>
                      <span style={{ color: colors.textLight }}>{p.label}</span>
                      <span className="font-bold" style={{ color: colors.text }}>{p.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {(briefing.steps?.length > 0 || briefing.rules?.length > 0) && (
              <div className="grid sm:grid-cols-2 gap-4 mb-6">
                {briefing.steps?.length > 0 && (
                  <div>
                    <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide mb-2" style={{ color: colors.textLight }}>
                      <FaListOl /> Your Steps
                    </div>
                    <ol className="space-y-1.5">
                      {briefing.steps.map((s, i) => (
                        <li key={i} className="flex gap-2 text-sm" style={{ color: colors.text }}>
                          <span className="flex-shrink-0 w-4 h-4 rounded-full text-white text-[10px] font-bold flex items-center justify-center mt-0.5" style={{ backgroundColor: meta.accent }}>
                            {i + 1}
                          </span>
                          {s}
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
                {briefing.rules?.length > 0 && (
                  <div>
                    <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide mb-2" style={{ color: colors.textLight }}>
                      <FaCheckCircle /> Rules
                    </div>
                    <ul className="space-y-1.5">
                      {briefing.rules.map((r, i) => (
                        <li key={i} className="flex gap-2 text-sm" style={{ color: colors.textLight }}>
                          <FaCheckCircle className="flex-shrink-0 mt-1 text-[10px]" style={{ color: colors.green }} />
                          {r}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {!briefing.narrative && (
              <div className="rounded-xl p-4 mb-6" style={{ backgroundColor: colors.primaryLight + '40' }}>
                <div className="text-xs font-bold uppercase tracking-wide mb-1" style={{ color: colors.textLight }}>Format</div>
                <p className="text-sm" style={{ color: colors.text }}>
                  {gameId === 'heliogrid'
                    ? `${totalQuarters} quarters of continuous lever decisions — no single right answer, only trade-offs across four customer segments.`
                    : `${game.rounds?.length || 0} rounds — each choice trades off multiple KPIs, and you'll see the impact and a short takeaway after every decision.`}
                </p>
              </div>
            )}

            <button
              onClick={() => setShowBriefing(false)}
              className="w-full py-3.5 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg sticky bottom-0"
              style={{ backgroundColor: colors.primary, color: colors.text }}
            >
              Begin Simulation <FaArrowRight />
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  // ---------- Dealcraft / Mumbai Manufacturer: choice handling ----------
  const handleChoice = async (choiceId) => {
    const rounds = game.rounds;
    const round = rounds[roundIndex];
    const choice = round.choices.find((c) => c.id === choiceId);
    setSubmitting(true);
    setError('');
    try {
      let res;
      if (gameId === 'dealcraft') {
        res = await dealcraftChoose(runId, round.id, choiceId);
      } else {
        // mumbai_manufacturer schedules a crisis event after some rounds —
        // the route 400s with the event payload when one is due and no
        // event_choice_id was sent. Auto-picking the first event option
        // keeps this page's flow to one click per round rather than adding
        // a second modal step for the ~1/3 of rounds that have one.
        try {
          res = await mumbaiManufacturerChoose(runId, round.id, choiceId);
        } catch (err) {
          const event = err?.response?.data?.event;
          if (err?.response?.status === 400 && event?.choices?.length) {
            res = await mumbaiManufacturerChoose(runId, round.id, choiceId, event.choices[0].id);
          } else {
            throw err;
          }
        }
      }
      setPrevState(state);
      setState(res.state);
      setPendingOutcome({
        title: round.title, feedback: choice.feedback, deltas: choice.effects || {},
        learning: choice.learning, concepts: choice.concepts,
      });
      setPhase('outcome');
    } catch (err) {
      setError(err?.response?.data?.error || 'Choice failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleContinueAfterOutcome = async () => {
    const rounds = game.rounds;
    if (roundIndex + 1 >= rounds.length) {
      setSubmitting(true);
      try {
        const done = await completePilotRun(runId);
        setSummary(done.summary);
        setPhase('complete');
      } catch (err) {
        setError(err?.response?.data?.error || 'Could not finalize the run.');
      } finally {
        setSubmitting(false);
      }
    } else {
      setRoundIndex((i) => i + 1);
      setPhase('choice');
      setPendingOutcome(null);
    }
  };

  // ---------- HelioGrid: quarter handling ----------
  const handleHeliogridQuarter = async (action) => {
    setSubmitting(true);
    setError('');
    try {
      const res = await heliogridQuarter(runId, action);
      setPrevState(state);
      setState(res.state);
      setPendingOutcome(res.quarter_result || res.state?._last_quarter_result);
      setPhase('outcome');
    } catch (err) {
      setError(err?.response?.data?.error || 'Quarter simulation failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleContinueAfterQuarter = async () => {
    if (quarterIndex + 1 >= totalQuarters) {
      setSubmitting(true);
      try {
        const done = await completePilotRun(runId);
        setSummary(done.summary);
        setPhase('complete');
      } catch (err) {
        setError(err?.response?.data?.error || 'Could not finalize the run.');
      } finally {
        setSubmitting(false);
      }
    } else {
      setQuarterIndex((i) => i + 1);
      setPhase('choice');
      setPrevQuarterResult(pendingOutcome);
      setPendingOutcome(null);
    }
  };

  // ---------- Final score screen ----------
  if (phase === 'complete' && summary) {
    const rankLetter = (summary.band || summary.rank || '?')[0]?.toUpperCase();
    const rankStyle = RANK_STYLES[rankLetter] || RANK_STYLES.C;
    const hero = HERO_IMAGES[gameId];
    return (
      <div className="min-h-screen flex items-center justify-center px-4 py-10" style={{ backgroundColor: colors.background }}>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-3xl shadow-2xl overflow-hidden max-w-lg w-full">
          {hero && (
            <div
              className="h-28 relative"
              style={{
                backgroundImage: `linear-gradient(to top, rgba(255,255,255,1), rgba(0,0,0,0.15)), url(${hero})`,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
              }}
            />
          )}
        <div className="p-8 pt-4 text-center">
          <img src={RobotGuide} alt="" className="w-14 h-14 mx-auto mb-3 -mt-8 relative bg-white rounded-full p-1 shadow-lg" />
          <div className="flex items-center justify-center gap-2 mb-1">
            <FaTrophy style={{ color: colors.primaryDark }} />
            <h1 className="text-xl font-bold" style={{ color: colors.text }}>Run Complete!</h1>
          </div>
          <p className="text-sm mb-6" style={{ color: colors.textLight }}>{game.title}</p>

          <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.15, type: 'spring' }}
            className="text-6xl font-extrabold mb-2"
            style={{ color: colors.purple }}
          >
            {Math.round(summary.score ?? 0)}
          </motion.div>

          <span className="inline-block px-4 py-1 rounded-full text-sm font-bold mb-2" style={{ backgroundColor: rankStyle.bg, color: rankStyle.text }}>
            Rank {summary.band || summary.rank}
          </span>
          {summary.label && <p className="text-sm font-medium mt-1" style={{ color: colors.text }}>{summary.label}</p>}

          {summary.dimension_scores && (
            <div className="mt-6 space-y-3 text-left">
              <div className="flex items-center gap-2 text-sm font-bold" style={{ color: colors.text }}>
                <FaChartLine style={{ color: colors.teal }} />
                Skill Breakdown
              </div>
              {Object.entries(summary.dimension_scores).map(([dim, val]) => (
                <div key={dim}>
                  <div className="flex justify-between text-xs mb-1" style={{ color: colors.textLight }}>
                    <span>{dim}</span>
                    <span className="font-semibold">{Math.round(val)}</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-gray-100 overflow-hidden">
                    <motion.div
                      className="h-full rounded-full"
                      style={{ backgroundColor: colors.teal }}
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min(100, val)}%` }}
                      transition={{ duration: 0.6, delay: 0.2 }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {game.reflection_prompt && (
            <div className="mt-6 text-left rounded-xl p-4 border-l-4" style={{ borderColor: colors.primaryDark, backgroundColor: colors.primaryLight + '40' }}>
              <div className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wide mb-1.5" style={{ color: colors.text }}>
                <FaLightbulb style={{ color: colors.primaryDark }} /> Reflect
              </div>
              <p className="text-sm" style={{ color: colors.textLight }}>{game.reflection_prompt}</p>
            </div>
          )}

          <div className="flex gap-3 mt-8">
            <button onClick={() => window.location.reload()} className="flex-1 px-4 py-2.5 rounded-xl font-bold border-2" style={{ borderColor: colors.primary, color: colors.text, backgroundColor: colors.card }}>
              Play Again
            </button>
            <button onClick={() => navigate('/games')} className="flex-1 px-4 py-2.5 rounded-xl font-bold shadow-lg" style={{ backgroundColor: colors.primary, color: colors.text }}>
              Back to Games
            </button>
          </div>
        </div>
        </motion.div>
      </div>
    );
  }

  // ---------- Round / quarter play screen ----------
  const currentRound = gameId !== 'heliogrid' ? game.rounds[roundIndex] : null;
  const totalSteps = gameId === 'heliogrid' ? totalQuarters : game.rounds.length;
  const currentStep = gameId === 'heliogrid' ? quarterIndex + 1 : roundIndex + 1;
  const focusSegment = gameId === 'heliogrid' ? focusRotation[quarterIndex % (focusRotation.length || 1)] : null;

  return (
    <div className="min-h-screen pb-16" style={{ backgroundColor: colors.background }}>
      <TopBar title={game.title} icon={meta.icon} heroImage={HERO_IMAGES[gameId]} onBack={() => navigate('/games')} />
      {gameId !== 'heliogrid' && <KpiBar keys={meta.headlineKpis} state={state} prevState={prevState} />}
      <ProgressBar current={currentStep} total={totalSteps} accent={meta.accent} />

      <div className="max-w-3xl mx-auto px-4 mt-6">
        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 text-red-700 text-sm flex items-center gap-2">
            <FaExclamationTriangle /> {error}
          </div>
        )}

        <AnimatePresence mode="wait">
          {phase === 'outcome' && gameId === 'heliogrid' && (
            <HeliogridOutcome
              key={`hg-outcome-${quarterIndex}`}
              result={pendingOutcome}
              prevResult={prevQuarterResult}
              segmentLabel={SEGMENT_LABELS[pendingOutcome?.focus_segment] || pendingOutcome?.focus_segment}
              onContinue={handleContinueAfterQuarter}
              isLast={quarterIndex + 1 >= totalQuarters}
            />
          )}

          {phase === 'outcome' && gameId !== 'heliogrid' && (
            <OutcomeScreen
              key={`outcome-${roundIndex}`}
              title={pendingOutcome?.title}
              feedback={pendingOutcome?.feedback}
              deltas={pendingOutcome?.deltas}
              learning={pendingOutcome?.learning}
              concepts={pendingOutcome?.concepts}
              onContinue={handleContinueAfterOutcome}
              isLast={roundIndex + 1 >= game.rounds.length}
            />
          )}

          {phase === 'choice' && gameId === 'heliogrid' && (
            <div key="hg-form">
              <div className="rounded-xl p-3.5 mb-3 flex items-start gap-2" style={{ backgroundColor: meta.accent + '14' }}>
                <FaUsers className="flex-shrink-0 mt-0.5" style={{ color: meta.accent }} />
                <div>
                  <p className="text-xs font-bold uppercase tracking-wide" style={{ color: meta.accent }}>
                    Quarter {quarterIndex + 1} focus: {SEGMENT_LABELS[focusSegment] || focusSegment}
                  </p>
                  {game.segments?.[focusSegment]?.blurb && (
                    <p className="text-sm mt-0.5" style={{ color: colors.text }}>{game.segments[focusSegment].blurb}</p>
                  )}
                </div>
              </div>
              <HeliogridLeverForm game={game} submitting={submitting} onSubmit={handleHeliogridQuarter} />
            </div>
          )}

          {phase === 'choice' && gameId !== 'heliogrid' && (
            <motion.div
              key={`round-${roundIndex}`}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="bg-white rounded-2xl shadow-md p-6"
            >
              <div className="flex items-center gap-2 mb-2" style={{ color: colors.textLight }}>
                <FaGamepad />
                <span className="text-xs font-bold uppercase tracking-wide">
                  {meta.label}{currentRound.scenario ? ` · ${currentRound.scenario}` : ''}
                </span>
              </div>
              <h2 className="text-xl font-bold mb-2" style={{ color: colors.text }}>{currentRound.title}</h2>

              {currentRound.narrative && (
                <div className="rounded-xl p-4 mb-3" style={{ backgroundColor: '#F5F4EF' }}>
                  <p className="text-sm whitespace-pre-line leading-relaxed" style={{ color: colors.text }}>{currentRound.narrative}</p>
                  {currentRound.dialogue && (
                    <p className="text-sm mt-2 italic leading-relaxed" style={{ color: colors.textLight }}>&ldquo;{currentRound.dialogue}&rdquo;</p>
                  )}
                </div>
              )}

              {currentRound.quarter_data && Object.keys(currentRound.quarter_data).length > 0 && (
                <div className="mb-4 rounded-xl border border-gray-100 overflow-hidden">
                  <div className="text-xs font-bold uppercase tracking-wide px-3 py-2 bg-gray-50" style={{ color: colors.textLight }}>
                    Key data this stage
                  </div>
                  {quarterDataRows(currentRound.quarter_data).map(([label, value], idx) => (
                    <div key={label} className={`flex justify-between px-3 py-1.5 text-sm ${idx % 2 ? 'bg-gray-50/60' : ''}`}>
                      <span style={{ color: colors.textLight }}>{label}</span>
                      <span className="font-semibold" style={{ color: colors.text }}>{value}</span>
                    </div>
                  ))}
                </div>
              )}

              <p className="text-sm font-semibold mb-5" style={{ color: colors.text }}>{currentRound.prompt}</p>

              <div className="flex flex-col gap-3">
                {currentRound.choices.map((c, idx) => {
                  const topEffect = Object.entries(c.effects || {}).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))[0];
                  return (
                    <motion.button
                      key={c.id}
                      disabled={submitting}
                      onClick={() => handleChoice(c.id)}
                      whileHover={{ scale: submitting ? 1 : 1.01 }}
                      whileTap={{ scale: submitting ? 1 : 0.99 }}
                      className="text-left p-4 rounded-xl border-2 border-gray-100 hover:border-current disabled:opacity-60 transition-colors"
                      style={{ color: meta.accent }}
                    >
                      <div className="flex items-start gap-3">
                        <span className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white" style={{ backgroundColor: meta.accent }}>
                          {String.fromCharCode(65 + idx)}
                        </span>
                        <div className="flex-1">
                          <div className="flex items-center justify-between gap-2">
                            <div className="font-bold" style={{ color: colors.text }}>{c.label}</div>
                            {topEffect && (
                              <span
                                className="text-xs font-bold px-2 py-0.5 rounded-full flex-shrink-0"
                                style={{
                                  backgroundColor: topEffect[1] > 0 ? '#D1FAE5' : '#FEE2E2',
                                  color: topEffect[1] > 0 ? colors.green : colors.red,
                                }}
                              >
                                {topEffect[1] > 0 ? '+' : ''}{fmtNum(topEffect[1])} {kpiLabel(topEffect[0])}
                              </span>
                            )}
                          </div>
                          {c.description && <div className="text-sm mt-0.5" style={{ color: colors.textLight }}>{c.description}</div>}
                        </div>
                      </div>
                    </motion.button>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
