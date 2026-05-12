// frontend-react/src/components/module/AudioLessonRenderer.jsx
import React, { useState, useRef } from "react";

const LANG_LABELS = { en: "EN", hi: "हिं", hi_mix: "Hinglish" };

export default function AudioLessonRenderer({ lesson, onComplete }) {
  const [lang, setLang] = useState("en");
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef(null);

  const audioUrls = lesson.audio_urls || {};
  const url = audioUrls[lang] || audioUrls.en;

  const toggle = () => {
    if (!audioRef.current) return;
    if (playing) audioRef.current.pause();
    else audioRef.current.play();
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
          <button onClick={toggle} className="px-3 py-2 bg-sky-600 text-white rounded-lg" aria-label={playing ? "Pause narration" : "Play narration"}>
            {playing ? "⏸ Pause" : "▶ Listen"}
          </button>
          <audio
            ref={audioRef}
            src={url}
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onEnded={() => setPlaying(false)}
          />
          <div className="flex gap-1 ml-auto">
            {Object.entries(LANG_LABELS).filter(([k]) => audioUrls[k]).map(([k, label]) => (
              <button key={k} onClick={() => setLang(k)} className={`px-2 py-1 text-xs rounded ${lang === k ? "bg-sky-600 text-white" : "bg-white border"}`}>
                {label}
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="prose max-w-none" dangerouslySetInnerHTML={{ __html: lesson.content || "" }} />
      <button onClick={onComplete} className="px-4 py-2 bg-emerald-600 text-white rounded-lg">
        Mark complete
      </button>
    </article>
  );
}
