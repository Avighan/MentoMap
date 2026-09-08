/**
 * ShareCard — renders a v2-engine share card (engines/v2_engine.py's
 * build_share_card output). Only mounted for games flagged as v2, which
 * return {v2: true, card: {...}} from /api/v2/run/<id>/share-card.
 */
export default function ShareCard({ shareCard }) {
  if (!shareCard) return null;
  return (
    <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-4 mb-4">
      {shareCard.title && <div className="text-sm font-bold text-indigo-900 mb-1">{shareCard.title}</div>}
      {shareCard.subtitle && <div className="text-xs text-indigo-700">{shareCard.subtitle}</div>}
    </div>
  );
}
