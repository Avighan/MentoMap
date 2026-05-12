import React, { useState } from "react";
export default function MicroQuestRenderer({ lesson, onComplete }) {
  const [answer, setAnswer] = useState("");
  const prompt = lesson.schema?.prompt || lesson.content || "Apply what you just learned.";
  return (
    <article className="space-y-4">
      <h2 className="text-2xl font-bold">{lesson.title}</h2>
      <div className="p-4 bg-amber-50 border-l-4 border-amber-400 rounded-r-lg">
        <p className="text-sm font-medium">⚡ Quick Quest ({lesson.estimated_minutes || 3} min)</p>
        <p className="mt-1">{prompt}</p>
      </div>
      <textarea
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        rows={4}
        className="w-full border rounded-lg p-3"
        placeholder="Type your answer here..."
      />
      <button
        onClick={() => onComplete({ answer })}
        disabled={!answer.trim()}
        className="px-4 py-2 bg-emerald-600 text-white rounded-lg disabled:opacity-50"
      >
        Submit
      </button>
    </article>
  );
}
