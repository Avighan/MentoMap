// frontend-react/src/components/module/CaseStudyCardRenderer.jsx
import { useState } from "react";
import { addIdeaJournalEntry, completeLesson } from "../../api/modules";

export default function CaseStudyCardRenderer({ lesson, moduleId, onComplete }) {
  const schema = lesson.schema || {};
  const portrait_url = lesson.portrait_url || schema.portrait_url;
  const founder_name = lesson.founder_name || schema.founder_name;
  const founder_origin = lesson.founder_origin || schema.founder_origin;
  const backstory = lesson.backstory || schema.backstory;
  const takeaway = lesson.takeaway || schema.takeaway;
  const reflection_prompt = lesson.reflection_prompt || schema.reflection_prompt;
  const company = lesson.company || schema.company;

  const lessonId = lesson.lesson_id || lesson.id;
  const [answer, setAnswer] = useState("");
  const [saved, setSaved] = useState(false);

  const submit = async () => {
    const text = answer.trim();
    try {
      if (text) {
        await addIdeaJournalEntry(moduleId, {
          content: `${reflection_prompt}\n\u2192 ${text}`,
          type: "reflection",
          lesson_id: lessonId,
          lesson_title: lesson.title,
        });
      }
      await completeLesson(moduleId, lessonId, { score: 100 });
    } catch (err) {
      // Surface failure silently; user can retry.
      // eslint-disable-next-line no-console
      console.error("CaseStudyCardRenderer submit failed", err);
    }
    setSaved(true);
    if (onComplete) onComplete();
  };

  return (
    <article className="rounded-2xl overflow-hidden border bg-white shadow-sm">
      <div className="bg-gradient-to-br from-amber-100 to-rose-100 p-6 flex gap-4 items-center">
        {portrait_url && (
          <img
            src={portrait_url}
            alt={founder_name}
            className="w-24 h-24 rounded-full object-cover border-2 border-white shadow"
          />
        )}
        <div>
          <div className="text-xs uppercase tracking-wide text-rose-700">
            Indian Founder · 60–90 sec read
          </div>
          <h2 className="text-2xl font-bold">{founder_name}</h2>
          {company && <div className="text-sm text-slate-700">{company}</div>}
          {founder_origin && (
            <div className="text-xs text-slate-500">{founder_origin}</div>
          )}
        </div>
      </div>
      <div className="p-6 space-y-4">
        {backstory && (
          <p className="text-slate-800 whitespace-pre-line leading-relaxed">
            {backstory}
          </p>
        )}
        {takeaway && (
          <div className="bg-amber-50 border-l-4 border-amber-400 p-3 text-sm">
            <strong>One thing to take away: </strong>
            {takeaway}
          </div>
        )}
        {reflection_prompt && !saved && (
          <div>
            <label className="text-sm font-medium">{reflection_prompt}</label>
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              rows={3}
              className="mt-1 w-full border rounded p-2 text-sm"
            />
          </div>
        )}
        {saved ? (
          <div className="text-emerald-700 text-sm">
            ✓ Saved to your Idea Journal.
          </div>
        ) : (
          <button
            onClick={submit}
            className="bg-rose-600 text-white rounded px-4 py-2 text-sm"
          >
            Mark complete
          </button>
        )}
      </div>
    </article>
  );
}
