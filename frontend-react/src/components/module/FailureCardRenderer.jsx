// frontend-react/src/components/module/FailureCardRenderer.jsx
import { useState } from "react";
import { completeLesson } from "../../api/modules";

export default function FailureCardRenderer({ lesson, moduleId, onComplete }) {
  const schema = lesson.schema || {};
  const company_name = lesson.company_name || schema.company_name;
  const headline = lesson.headline || schema.headline;
  const what_they_tried = lesson.what_they_tried || schema.what_they_tried;
  const why_they_failed =
    lesson.why_they_failed || schema.why_they_failed || schema.why_it_failed;
  const lesson_text =
    lesson.lesson_text || schema.lesson_text || schema.lesson_learned;
  const year = lesson.year || schema.year || schema.years;
  const image_url = lesson.image_url || schema.image_url;

  const lessonId = lesson.lesson_id || lesson.id;
  const [done, setDone] = useState(false);

  const submit = async () => {
    try {
      await completeLesson(moduleId, lessonId, { score: 100 });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("FailureCardRenderer submit failed", err);
    }
    setDone(true);
    if (onComplete) onComplete();
  };

  return (
    <article className="rounded-2xl overflow-hidden border-2 border-slate-200 bg-slate-50">
      <div className="bg-slate-900 text-white p-4">
        <div className="text-xs uppercase tracking-wide text-rose-300">
          Failure Museum · 60 sec read
        </div>
        <h2 className="text-xl font-bold mt-1">
          {company_name}{" "}
          {year && (
            <span className="text-slate-400 text-base">· {year}</span>
          )}
        </h2>
        {headline && (
          <div className="text-sm text-slate-200 mt-1">{headline}</div>
        )}
      </div>
      {image_url && (
        <img
          src={image_url}
          alt={company_name}
          className="w-full max-h-48 object-cover"
        />
      )}
      <div className="p-4 space-y-3 text-sm">
        {what_they_tried && (
          <div>
            <strong>What they tried: </strong>
            {what_they_tried}
          </div>
        )}
        {why_they_failed && (
          <div>
            <strong>Why it didn't work: </strong>
            {why_they_failed}
          </div>
        )}
        {lesson_text && (
          <div className="bg-rose-50 border-l-4 border-rose-400 p-3">
            <strong>One lesson: </strong>
            {lesson_text}
          </div>
        )}
        {done ? (
          <div className="text-emerald-700">✓ Lesson noted.</div>
        ) : (
          <button
            onClick={submit}
            className="bg-slate-800 text-white rounded px-4 py-2 text-sm"
          >
            Got it
          </button>
        )}
      </div>
    </article>
  );
}
