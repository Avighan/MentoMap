import React from "react";
export default function FailureCardRenderer({ lesson, onComplete }) {
  const c = lesson.schema || {};
  return (
    <article className="max-w-2xl mx-auto">
      <div className="rounded-3xl overflow-hidden shadow-xl bg-gradient-to-br from-rose-50 to-white border">
        <div className="p-6 space-y-3">
          <div className="text-xs uppercase tracking-wider text-rose-600 font-semibold">Failure Museum</div>
          <h2 className="text-2xl font-bold">{c.company_name}</h2>
          <p className="text-sm text-gray-500">{c.years || ""}</p>
          <div>
            <p className="text-sm font-semibold">What they tried:</p>
            <p className="text-sm">{c.what_they_tried}</p>
          </div>
          <div>
            <p className="text-sm font-semibold">Why it failed:</p>
            <p className="text-sm">{c.why_it_failed}</p>
          </div>
          <div className="p-3 bg-rose-50 rounded-lg border border-rose-200">
            <p className="text-sm font-semibold">📚 Lesson</p>
            <p className="text-sm">{c.lesson_learned}</p>
          </div>
          <button onClick={onComplete} className="mt-2 px-4 py-2 bg-emerald-600 text-white rounded-lg">
            Understood
          </button>
        </div>
      </div>
    </article>
  );
}
