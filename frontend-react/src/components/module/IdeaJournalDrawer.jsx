import { useEffect, useState } from "react";
import {
  listIdeaJournal,
  addIdeaJournalEntry,
  patchIdeaJournalEntry,
  ideaJournalExportUrl,
} from "../../api/modules";

export default function IdeaJournalDrawer({ moduleId, open, onClose }) {
  const [entries, setEntries] = useState([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    listIdeaJournal(moduleId)
      .then((d) => {
        if (!cancelled) setEntries(d?.entries || []);
      })
      .catch(() => {
        if (!cancelled) setEntries([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, moduleId]);

  const add = async () => {
    const text = draft.trim();
    if (!text) return;
    const e = await addIdeaJournalEntry(moduleId, {
      content: text,
      type: "free_form",
    });
    setEntries((cur) => [...cur, e]);
    setDraft("");
  };

  const toggleStar = async (entry) => {
    const updated = await patchIdeaJournalEntry(moduleId, entry.entry_id, {
      starred: !entry.starred,
    });
    setEntries((cur) =>
      cur.map((e) => (e.entry_id === updated.entry_id ? updated : e))
    );
  };

  const exportPdf = () => {
    window.open(ideaJournalExportUrl(moduleId), "_blank");
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex" role="dialog" aria-label="Idea Journal">
      <div className="flex-1 bg-black/40" onClick={onClose} />
      <aside className="w-full max-w-md bg-white shadow-xl flex flex-col">
        <header className="px-4 py-3 border-b flex items-center justify-between">
          <div className="font-semibold">📒 My Idea Journal</div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-800">✕</button>
        </header>
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
          {loading && <div className="text-slate-500">Loading…</div>}
          {!loading && entries.length === 0 && (
            <div className="text-slate-500 text-sm">No entries yet. Worksheets and quests auto-save here.</div>
          )}
          {entries.map((e) => (
            <div key={e.entry_id} className="rounded border border-slate-200 p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="text-xs text-slate-500">
                  {e.lesson_title || e.type} · {new Date(e.timestamp).toLocaleString()}
                </div>
                <button onClick={() => toggleStar(e)} className="text-lg">
                  {e.starred ? "⭐" : "☆"}
                </button>
              </div>
              <div className="mt-2 text-sm whitespace-pre-wrap">{e.content}</div>
            </div>
          ))}
        </div>
        <div className="border-t p-3 space-y-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Capture a quick idea…"
            className="w-full border rounded p-2 text-sm"
            rows={3}
          />
          <div className="flex gap-2">
            <button onClick={add} className="flex-1 bg-indigo-600 text-white rounded py-2 text-sm">
              Add entry
            </button>
            <button onClick={exportPdf} className="bg-emerald-600 text-white rounded px-3 text-sm">
              📥 Pitch Deck PDF
            </button>
          </div>
        </div>
      </aside>
    </div>
  );
}
