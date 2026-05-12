import React, { useState, useEffect } from "react";
import VoiceRecorder from "./audio/VoiceRecorder";
import {
  listInterviewPersonas,
  startInterview,
  takeInterviewTurn,
  endInterview,
} from "../../api/modules";

export default function InterviewSimRenderer({ lesson, moduleId, onComplete }) {
  const [personas, setPersonas] = useState([]);
  const [selected, setSelected] = useState(null);
  const [conv, setConv] = useState(null);
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState(false);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    listInterviewPersonas(moduleId, lesson.lesson_id)
      .then((r) => { if (!cancelled) setPersonas(r.personas || []); })
      .catch(() => { if (!cancelled) setError("Couldn't load personas."); });
    return () => { cancelled = true; };
  }, [moduleId, lesson.lesson_id]);

  const begin = async () => {
    setError(null);
    try {
      const r = await startInterview(moduleId, lesson.lesson_id, selected);
      setConv(r);
    } catch (e) {
      setError(e?.code === "cap_reached"
        ? "You've used all 3 interviews for this module."
        : "Couldn't start interview. Try again.");
    }
  };

  const onTurn = async (blob) => {
    setBusy(true);
    setError(null);
    try {
      const r = await takeInterviewTurn(moduleId, lesson.lesson_id, conv.conv_id, blob);
      setHistory((h) => [
        ...h,
        { role: "user", text: r.user_text },
        { role: "persona", text: r.persona_text, audio: r.persona_audio_url },
      ]);
    } catch (e) {
      setError(e?.code === "cap_reached"
        ? "You've used all 15 turns."
        : "Turn failed. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const finish = async () => {
    try {
      const r = await endInterview(moduleId, lesson.lesson_id, conv.conv_id);
      setSummary(r);
    } catch {
      setError("Couldn't finish interview.");
    }
  };

  if (summary) {
    return (
      <article className="space-y-3">
        <h2 className="text-2xl font-bold">Interview summary</h2>
        <p><strong>Depth score:</strong> {summary.depth_score}/5 WHYs</p>
        <p className="p-3 bg-amber-50 rounded-lg border-l-4 border-amber-400">{summary.missed_note}</p>
        <button onClick={() => onComplete?.(summary)} className="px-4 py-2 bg-emerald-600 text-white rounded-lg">
          Save & continue
        </button>
      </article>
    );
  }

  if (!conv) {
    return (
      <article className="space-y-4">
        <h2 className="text-2xl font-bold">{lesson.title}</h2>
        <p>Pick a customer to interview. Ask them WHY at least 3 times.</p>
        {error && <p className="text-sm text-rose-600">{error}</p>}
        <div className="grid grid-cols-2 gap-3">
          {personas.map((p) => (
            <button
              key={p.persona_id}
              onClick={() => setSelected(p.persona_id)}
              className={`p-4 border-2 rounded-xl text-left ${selected === p.persona_id ? "border-sky-600 bg-sky-50" : "border-gray-200"}`}
              aria-pressed={selected === p.persona_id}
            >
              <div className="font-medium">{p.display_name}</div>
            </button>
          ))}
        </div>
        <button
          disabled={!selected}
          onClick={begin}
          className="px-4 py-2 bg-sky-600 text-white rounded-lg disabled:opacity-50"
        >
          Start interview
        </button>
      </article>
    );
  }

  return (
    <article className="space-y-3">
      <h2 className="text-xl font-bold">Talking to {conv.persona?.display_name}</h2>
      <div className="space-y-2 max-h-72 overflow-y-auto bg-gray-50 p-3 rounded-lg">
        {history.map((h, i) => (
          <div key={i} className={h.role === "user" ? "text-right" : ""}>
            <span className={`inline-block px-3 py-2 rounded-2xl ${h.role === "user" ? "bg-sky-600 text-white" : "bg-white border"}`}>
              {h.text}
            </span>
            {h.audio && <audio controls src={h.audio} className="mt-1 w-full" />}
          </div>
        ))}
      </div>
      <VoiceRecorder maxSeconds={20} onRecorded={onTurn} />
      {busy && <p className="text-sm text-gray-500">Persona is thinking…</p>}
      {error && <p className="text-sm text-rose-600">{error}</p>}
      <button onClick={finish} className="px-4 py-2 bg-gray-700 text-white rounded-lg">End interview</button>
    </article>
  );
}
