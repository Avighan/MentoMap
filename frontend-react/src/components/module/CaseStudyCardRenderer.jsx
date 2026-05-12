import React from "react";
export default function CaseStudyCardRenderer({ lesson, onComplete }) {
  const c = lesson.schema || {};
  return (
    <article className="max-w-2xl mx-auto">
      <div className="rounded-3xl overflow-hidden shadow-xl bg-gradient-to-br from-indigo-50 to-white border">
        {c.portrait_url && <img src={c.portrait_url} alt={c.founder_name} className="w-full" />}
        <div className="p-6 space-y-3">
          <h2 className="text-2xl font-bold">{c.founder_name}</h2>
          <p className="text-sm text-gray-500">{c.role}</p>
          <p>{c.backstory}</p>
          <div className="p-3 bg-indigo-50 rounded-lg border border-indigo-200">
            <p className="text-sm font-semibold">💡 Takeaway</p>
            <p className="text-sm">{c.takeaway}</p>
          </div>
          {c.reflection_prompt && (
            <p className="italic text-gray-700">✏️ {c.reflection_prompt}</p>
          )}
          <button onClick={onComplete} className="mt-2 px-4 py-2 bg-emerald-600 text-white rounded-lg">
            Got it
          </button>
        </div>
      </div>
    </article>
  );
}
