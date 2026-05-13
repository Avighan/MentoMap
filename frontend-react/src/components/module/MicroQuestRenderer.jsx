import { useState } from "react";
import { addIdeaJournalEntry } from "../../api/modules";

export default function MicroQuestRenderer({ lesson, moduleId, onComplete }) {
  const { prompt, input_type = "text", placeholder, completion_message } = lesson;
  const [value, setValue] = useState("");
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    const text = value.trim();
    if (!text) return;
    setSubmitting(true);
    try {
      // Save to Idea Journal first so the worksheet/quest answer is always captured.
      try {
        await addIdeaJournalEntry(moduleId, {
          content: text,
          type: "micro_quest",
          lesson_id: lesson.id || lesson.lesson_id,
          lesson_title: lesson.title,
        });
      } catch (_err) {
        // Non-fatal — don't block completion if the journal write fails.
      }
      // Lesson completion is owned by the parent dispatcher (handleComplete in
      // ModuleDetailPage). Pass score + the answer through so it ends up in
      // progress.reflections/answers like other lesson types.
      if (onComplete) {
        await onComplete({ score: 100, answer: text });
      }
      setDone(true);
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
    return (
      <div className="rounded-xl border-2 border-emerald-200 bg-emerald-50 p-6 text-center">
        <div className="text-4xl">🎯</div>
        <div className="mt-2 font-semibold text-emerald-900">Quest complete</div>
        <div className="mt-1 text-sm text-emerald-800">
          {completion_message || "Saved to your Idea Journal."}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border-2 border-amber-200 bg-amber-50 p-6">
      <div className="text-xs uppercase tracking-wide text-amber-800">2–3 minute quest</div>
      <h3 className="mt-1 text-lg font-semibold">{lesson.title}</h3>
      <p className="mt-3 text-slate-800">{prompt}</p>
      {input_type === "text" && (
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder || "Your answer…"}
          rows={4}
          className="mt-3 w-full border rounded p-2 text-sm"
        />
      )}
      <button
        onClick={submit}
        disabled={submitting || !value.trim()}
        className="mt-3 bg-amber-600 disabled:bg-amber-300 text-white rounded px-4 py-2 text-sm"
      >
        {submitting ? "Saving…" : "Mark complete"}
      </button>
    </div>
  );
}
