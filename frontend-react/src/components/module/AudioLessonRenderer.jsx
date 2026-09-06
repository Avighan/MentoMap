// frontend-react/src/components/module/AudioLessonRenderer.jsx
import React, { useState } from "react";
import { useModuleAudio } from "../../contexts/ModuleAudioContext";

const LANG_LABELS = { en: "EN", hi: "हिं", hi_mix: "Hinglish" };

export default function AudioLessonRenderer({ lesson, onComplete }) {
  const [lang, setLang] = useState("en");
  const { play, pause, playing, src } = useModuleAudio();

  const audioUrls = lesson.audio_urls || {};
  const url = audioUrls[lang] || audioUrls.en;
  const isThisPlaying = playing && src === url;

  const toggle = () => {
    if (!url) return;
    if (isThisPlaying) pause();
    else play(url);
  };

  return (
    <article className="space-y-4">
      {lesson.image_url && (
        <img
          src={lesson.image_url}
          alt={lesson.title}
          onError={(e) => { if (lesson.image_url_fallback) e.currentTarget.src = lesson.image_url_fallback; }}
          className="w-full rounded-2xl"
        />
      )}
      <h2 className="text-2xl font-bold">{lesson.title}</h2>
      {url && (
        <div className="flex items-center gap-3 p-3 bg-sky-50 rounded-xl border border-sky-200">
          <button onClick={toggle} className="px-3 py-2 bg-sky-600 text-white rounded-lg" aria-label={isThisPlaying ? "Pause narration" : "Play narration"}>
            {isThisPlaying ? "⏸ Pause" : "▶ Listen"}
          </button>
          <div className="flex gap-1 ml-auto">
            {Object.entries(LANG_LABELS).filter(([k]) => audioUrls[k]).map(([k, label]) => (
              <button key={k} onClick={() => setLang(k)} className={`px-2 py-1 text-xs rounded ${lang === k ? "bg-sky-600 text-white" : "bg-white border"}`}>
                {label}
              </button>
            ))}
          </div>
        </div>
      )}
      {/* Body: prefer rich HTML `content`, otherwise fall back to plain `body` / `transcript` */}
      {lesson.content ? (
        <div className="prose max-w-none" dangerouslySetInnerHTML={{ __html: lesson.content }} />
      ) : (lesson.body || lesson.transcript) ? (
        <div className="prose max-w-none whitespace-pre-line text-slate-800 leading-relaxed">
          {lesson.body || lesson.transcript}
        </div>
      ) : null}

      {!url && (lesson.transcript || lesson.body) && (
        <details className="mt-2 text-sm text-slate-600">
          <summary className="cursor-pointer">Show transcript</summary>
          <div className="mt-2 whitespace-pre-line text-slate-700">
            {lesson.transcript || lesson.body}
          </div>
        </details>
      )}

      <button onClick={onComplete} className="px-4 py-2 bg-emerald-600 text-white rounded-lg">
        Mark complete
      </button>
    </article>
  );
}
