/**
 * ExecPostGameSummary — executive-role performance rollup shown after
 * games with an active simulation_config executive subsystem (uxExecutive
 * .any_executive_subsystem_active). Placeholder until that dedicated
 * summary UI is built; the raw log is still surfaced so nothing is lost.
 */
export default function ExecPostGameSummary({ execActionsLog, currency = '' }) {
  if (!execActionsLog || execActionsLog.length === 0) return null;
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 mb-4">
      <div className="text-sm font-semibold text-slate-900 mb-2">Executive Actions</div>
      <ul className="text-xs text-slate-600 space-y-1 list-disc list-inside">
        {execActionsLog.map((a, i) => (
          <li key={i}>{typeof a === 'string' ? a : `${a.label || a.action}${a.amount != null ? `: ${currency}${a.amount}` : ''}`}</li>
        ))}
      </ul>
    </div>
  );
}
