/**
 * ExecutivePanel — single composer that takes the full `ux_executive` payload
 * (from `executive_ux.build_executive_payload`) and renders only the widgets
 * whose subsystem is active for the current game.
 *
 * Layout: a tabbed dock. Each active subsystem becomes a tab, only one widget
 * is visible at a time. This collapses what was a 13-widget vertical sprawl
 * into a single tabbed surface, keeping scenario + choices closer to the top.
 *
 * The crisis banner is rendered FIRST and as a separate sticky element above
 * the dock; framework artifacts are kept full-width below.
 *
 * Props:
 *   payload: ux_executive  // may be null / dormant
 *   currency?: "USD" | "INR" | "EUR"
 *   bands?: industry benchmark bands for the active business model
 *   className?: string
 *   runId?: string — when present, framework artifacts get an Author/Edit CTA
 *   onArtifactGraded?: (fid, artifact, grade) => void
 */
import React, { useState, useMemo } from 'react';

import CapTableWidget from './CapTableWidget';
import UnitEconomicsStrip from './UnitEconomicsStrip';
import MarketFunnelWidget from './MarketFunnelWidget';
import OrgChartWidget from './OrgChartWidget';
import BoardPulseWidget from './BoardPulseWidget';
import DecisionJournalWidget from './DecisionJournalWidget';
import StakeholderMatrixWidget from './StakeholderMatrixWidget';
import CrisisBanner from './CrisisBanner';
import ComplianceWidget from './ComplianceWidget';
import IntrapreneurWidget from './IntrapreneurWidget';
import FrameworkArtifacts from './FrameworkArtifacts';
import ProjectDashboardWidget from './ProjectDashboardWidget';
import ScorecardWidget from './ScorecardWidget';
import CalibrationStrip from './CalibrationStrip';
import MarketActorsTimeline from './MarketActorsTimeline';
import CompetitorBoardWidget from './CompetitorBoardWidget';
import IndustryReportWidget from './IndustryReportWidget';
import DecisionPanelWidget from './DecisionPanelWidget';

// ── Content-presence predicates ──────────────────────────────────────────
// Each widget has its own internal "return null when sparse" guard. To avoid
// adding a tab that opens to an empty pane, we mirror those rules here so
// tabs only appear when their widget will render something.
const hasFinanceContent = (finance) => {
  if (!finance) return false;
  if (finance.unit_economics) return true;
  if (finance.cap_table) return true;
  return false;
};

const hasMarketContent = (market) => {
  if (!market) return false;
  const f = market.funnel || market.market_funnel;
  if (!f) return false;
  // Show if any stage has data
  const stages = f.stages || f.steps || [];
  return Array.isArray(stages) && stages.length > 0;
};

const hasActorsContent = (actors) => {
  if (!actors) return false;
  const tl = Array.isArray(actors.timeline) ? actors.timeline : [];
  const ac = Array.isArray(actors.actors) ? actors.actors : [];
  return tl.length > 0 || ac.length > 0;
};

const hasOrgContent = (org) => {
  if (!org || typeof org !== 'object') return false;
  const chart = org.org_chart || org.chart || {};
  const leaders = Array.isArray(chart.leaders) ? chart.leaders
                 : Array.isArray(chart.nodes) ? chart.nodes : [];
  const pipeline = org.talent_pipeline || org.pipeline || {};
  const culture = org.culture_radar || org.culture || {};
  return leaders.length > 0
    || (pipeline && Object.keys(pipeline).length > 0)
    || (culture && Object.keys(culture).length > 0);
};

const hasBoardContent = (board) => {
  if (!board || typeof board !== 'object') return false;
  const pulseObj = board.board_pulse || board.pulse || {};
  const members = Array.isArray(pulseObj.members) ? pulseObj.members : [];
  return members.length > 0 || !!board.dd_status || board.last_term_sheet_score != null;
};

const hasStakeholderContent = (map) => {
  if (!map) return false;
  return Array.isArray(map.stakeholders) && map.stakeholders.length > 0;
};

const hasComplianceContent = (compliance) => {
  if (!compliance || typeof compliance !== 'object') return false;
  const status = compliance.compliance_status || compliance;
  const findings = Array.isArray(status.open_findings) ? status.open_findings
                 : Array.isArray(status.findings) ? status.findings : [];
  const score = status.compliance_risk_score ?? compliance.risk_score;
  return findings.length > 0 || score != null;
};

const hasIntraContent = (intra) => {
  if (!intra || typeof intra !== 'object') return false;
  const budget = intra.budget_status || intra.budget || null;
  const sponsorObj = intra.sponsor_status || intra.sponsors || {};
  const sponsors = Array.isArray(sponsorObj.list) ? sponsorObj.list
                : Array.isArray(sponsorObj.sponsors) ? sponsorObj.sponsors : [];
  const pc = sponsorObj.political_capital ?? intra.political_capital;
  const coal = intra.coalition_map || intra.coalition || null;
  return !!budget || sponsors.length > 0 || pc != null || !!coal;
};

const hasProjectContent = (pm) => {
  if (!pm) return false;
  const tasks = pm.tasks || [];
  const cp = pm.critical_path || {};
  const burndown = pm.burndown || {};
  return tasks.length > 0
    || (Array.isArray(cp.path) && cp.path.length > 0)
    || (burndown.total_days || 0) > 0
    || pm.schedule_health != null;
};

const hasDecisionContent = (decision) => {
  if (!decision || typeof decision !== 'object') return false;
  const log = decision.decision_ledger || decision.ledger || [];
  return (Array.isArray(log) && log.length > 0) || !!decision.calibration;
};

const hasForecastContent = (stochastic) => {
  if (!stochastic) return false;
  return !!(stochastic.calibration_enabled || stochastic.stochastic_enabled);
};

const hasScorecardContent = (scorecard) => {
  if (!scorecard || typeof scorecard !== 'object') return false;
  return Array.isArray(scorecard.dimensions) && scorecard.dimensions.length > 0;
};

const hasCompetitorBoardContent = (cb) => {
  if (!cb || typeof cb !== 'object') return false;
  return Array.isArray(cb.competitors) && cb.competitors.length > 0;
};

const hasIndustryReportContent = (ir) => {
  if (!ir || typeof ir !== 'object') return false;
  // Show as soon as the game opts in — the widget itself handles empty tables
  return !!ir.business_model || !!ir.title || !!ir.report;
};

const hasDecisionPanelContent = (dp) => {
  if (!dp || typeof dp !== 'object') return false;
  return Array.isArray(dp.controls) && dp.controls.length > 0;
};

// Empty-state fallback for any tab whose widget unexpectedly renders nothing.
const TabEmpty = ({ label }) => (
  <div
    className="rounded-xl px-4 py-6 text-center"
    style={{ background: '#FFFBF2', border: '1px dashed #F0E6D2', color: '#888780' }}
  >
    <div className="text-2xl mb-1.5">📭</div>
    <div className="text-xs font-semibold" style={{ color: '#5B3A1E' }}>
      No {label.toLowerCase()} data yet
    </div>
    <div className="text-[11px] mt-0.5">
      Make a few decisions — this view populates as the simulation runs.
    </div>
  </div>
);

const ExecutivePanel = ({ payload, currency = 'USD', bands = null, className = '', runId = null, onArtifactGraded = null, onDecisionPanelSubmit = null }) => {
  if (!payload || !payload.any_executive_subsystem_active) return null;

  const finance     = payload.finance || null;
  const market      = payload.market || null;
  const org         = payload.org || null;
  const board       = payload.corporate_board || null;
  const compliance  = payload.compliance || null;
  const decision    = payload.decision_quality || null;
  const crisis      = payload.crisis || null;
  const intra       = payload.intrapreneur || null;
  const projectMgmt = payload.project_management || null;
  const stakeholder = payload.stakeholder_map || null;
  const frameworks  = payload.frameworks || null;
  const stochastic  = payload.stochastic || null;
  const actors      = payload.market_actors || null;
  const scorecard   = payload.scorecard || null;
  const competitorBoard = payload.competitor_board || null;
  const industryReport  = payload.industry_report || null;
  const decisionPanel   = payload.decision_panel || null;

  // Build tabs in priority order — only include subsystems that have content.
  const tabs = useMemo(() => {
    const list = [];
    // Decision panel goes first — it's the round's primary input
    if (hasDecisionPanelContent(decisionPanel)) list.push({ id: 'decision-panel', label: 'Decide', icon: '🎛️' });
    if (hasFinanceContent(finance))         list.push({ id: 'finance',      label: 'Finance',      icon: '💰' });
    if (hasMarketContent(market))           list.push({ id: 'market',       label: 'Market',       icon: '📈' });
    if (hasActorsContent(actors))           list.push({ id: 'competitors',  label: 'Competitors',  icon: '⚔️' });
    if (hasCompetitorBoardContent(competitorBoard)) list.push({ id: 'rivals', label: 'Rivals', icon: '🎯' });
    if (hasIndustryReportContent(industryReport))   list.push({ id: 'industry', label: 'Industry', icon: '📈' });
    if (hasOrgContent(org))                 list.push({ id: 'org',          label: 'Team',         icon: '👥' });
    if (hasBoardContent(board))             list.push({ id: 'board',        label: 'Board',        icon: '🏛️' });
    if (hasStakeholderContent(stakeholder)) list.push({ id: 'stakeholders', label: 'Stakeholders', icon: '🎯' });
    if (hasComplianceContent(compliance))   list.push({ id: 'compliance',   label: 'Risk',         icon: '⚠️' });
    if (hasIntraContent(intra))             list.push({ id: 'intra',        label: 'Innovation',   icon: '🧪' });
    if (hasProjectContent(projectMgmt))     list.push({ id: 'pm',           label: 'Project',      icon: '📋' });
    if (hasDecisionContent(decision))       list.push({ id: 'decisions',    label: 'Decisions',    icon: '🧠' });
    if (hasForecastContent(stochastic))     list.push({ id: 'forecast',     label: 'Forecast',     icon: '🎯' });
    if (hasScorecardContent(scorecard))     list.push({ id: 'scorecard',    label: 'Scorecard',    icon: '📊' });
    return list;
  }, [finance, market, actors, org, board, stakeholder, compliance, intra, projectMgmt, decision, stochastic, scorecard, competitorBoard, industryReport, decisionPanel]);

  const [activeTab, setActiveTab] = useState(tabs[0]?.id || null);
  // Keep activeTab valid as games progress and subsystems light up
  const safeActive = tabs.find(t => t.id === activeTab) ? activeTab : tabs[0]?.id;

  if (!tabs.length) {
    return (
      <div className={`space-y-3 ${className}`}>
        <CrisisBanner crisis={crisis} />
      </div>
    );
  }

  // Render the active widget; if a widget unexpectedly returns null (e.g.
  // shape mismatch), fall back to a friendly empty-state so the tab is never
  // a blank pane. We do this by wrapping the widget in a small helper that
  // checks the rendered output isn't null.
  const renderActive = () => {
    const activeTabDef = tabs.find(t => t.id === safeActive);
    const activeLabel = activeTabDef?.label || 'data';
    let node = null;
    switch (safeActive) {
      case 'finance':
        node = (
          <div className="space-y-3">
            {finance?.unit_economics && (
              <UnitEconomicsStrip ue={finance.unit_economics} bands={bands} currency={currency} />
            )}
            {finance?.cap_table && (
              <CapTableWidget capTable={finance.cap_table} currency={currency} />
            )}
          </div>
        );
        break;
      case 'market':
        node = market?.funnel
          ? <MarketFunnelWidget funnel={market.funnel} />
          : <MarketFunnelWidget funnel={market.market_funnel} />;
        break;
      case 'competitors':
        node = <MarketActorsTimeline actors={actors} />;
        break;
      case 'org':
        node = <OrgChartWidget org={org} />;
        break;
      case 'board':
        node = <BoardPulseWidget board={board} />;
        break;
      case 'stakeholders':
        node = <StakeholderMatrixWidget map={stakeholder} />;
        break;
      case 'compliance':
        node = <ComplianceWidget compliance={compliance} />;
        break;
      case 'intra':
        node = <IntrapreneurWidget intra={intra} />;
        break;
      case 'pm':
        node = <ProjectDashboardWidget pm={projectMgmt} />;
        break;
      case 'decisions':
        node = <DecisionJournalWidget decision={decision} />;
        break;
      case 'forecast':
        node = <CalibrationStrip stochastic={stochastic} />;
        break;
      case 'scorecard':
        node = <ScorecardWidget payload={scorecard} />;
        break;
      case 'rivals':
        node = <CompetitorBoardWidget payload={competitorBoard} />;
        break;
      case 'industry':
        node = <IndustryReportWidget payload={industryReport} />;
        break;
      case 'decision-panel':
        node = <DecisionPanelWidget payload={decisionPanel} onSubmit={onDecisionPanelSubmit} />;
        break;
      default:
        node = null;
    }
    // If widget returned null/false/undefined despite the predicate above,
    // surface a friendly empty-state rather than a blank pane.
    return node || <TabEmpty label={activeLabel} />;
  };

  return (
    <div className={`space-y-3 ${className}`}>
      {/* sticky-ish crisis banner first */}
      <CrisisBanner crisis={crisis} />

      {/* Tabbed dock */}
      <div className="rounded-2xl border" style={{ background: '#FFFFFF', borderColor: '#F0E6D2' }}>
        <div
          className="flex items-center gap-1 overflow-x-auto scrollbar-hide px-2 pt-2 pb-0"
          style={{ borderBottom: '1px solid #F0E6D2' }}
        >
          {tabs.map(tab => {
            const active = tab.id === safeActive;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className="flex items-center gap-1 text-[11px] font-bold whitespace-nowrap transition-all"
                style={{
                  padding: '6px 10px',
                  borderRadius: '8px 8px 0 0',
                  background: active ? '#FFF3DC' : 'transparent',
                  color: active ? '#854F0B' : '#888780',
                  borderBottom: active ? '2px solid #EF9F27' : '2px solid transparent',
                  marginBottom: -1,
                }}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
        <div className="p-3">
          {renderActive()}
        </div>
      </div>

      {/* framework artifacts span full width */}
      {frameworks && (
        <FrameworkArtifacts
          artifacts={frameworks}
          runId={runId}
          onArtifactGraded={onArtifactGraded}
        />
      )}
    </div>
  );
};

export default ExecutivePanel;
