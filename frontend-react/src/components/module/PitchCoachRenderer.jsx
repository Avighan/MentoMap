import React, { useState } from "react";
import VoiceRecorder from "./audio/VoiceRecorder";
import PitchRubricChart from "./audio/PitchRubricChart";
import { submitPitchCoach } from "../../api/modules";

export default function PitchCoachRenderer({ lesson, moduleId, onComplete }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const onRecorded = async (blob) => {
    setBusy(true);
    setError(null);
    try {
      const r = await submitPitchCoach(moduleId, lesson.lesson_id, blob);
      setResult(r);
    } catch (e) {
      if (e?.code === "cap_reached" || e?.message === "cap_reached") {
        setError("You've used all 3 attempts for this module.");
      } else {
        setError("Couldn't score your pitch. Try again.");
      }
    } finally {
      setBusy(false);
    }
  };

  const prompt = lesson.schema?.prompt || "Hook · Problem · Solution · Customer · Ask";

  return (
    <article className="space-y-4">
      <h2 className="text-2xl font-bold">{lesson.title}</h2>
      <div className="p-4 bg-amber-50 border-l-4 border-amber-400">
        <p className="font-medium">🎤 Record your 60-second pitch:</p>
        <p className="text-sm">{prompt}</p>
      </div>
      <VoiceRecorder maxSeconds={60} onRecorded={onRecorded} />
      {busy && <p className="text-sm text-gray-600">Scoring your pitch…</p>}
      {error && <p className="text-sm text-rose-600">{error}</p>}
      {result && (
        <div className="space-y-4 border-t pt-4">
          <div>
            <h3 className="font-semibold mb-2">Your transcript</h3>
            <p className="text-sm italic bg-gray-50 rounded-lg p-3">{result.transcript}</p>
          </div>
          <div>
            <h3 className="font-semibold mb-2">Rubric</h3>
            <PitchRubricChart scores={result.scores} />
          </div>
          <div>
            <h3 className="font-semibold mb-2">Mento's verdict</h3>
            <p className="text-sm">{result.summary}</p>
            {result.voice_reply_url && (
              <audio controls src={result.voice_reply_url} className="mt-2 w-full" />
            )}
          </div>
          <details>
            <summary className="cursor-pointer font-semibold">See per-axis feedback</summary>
            <div className="mt-2 space-y-2 text-sm">
              {Object.keys(result.scores || {}).map((a) => (
                <div key={a} className="border rounded-lg p-2">
                  <div className="capitalize font-medium">{a}</div>
                  <div className="text-emerald-700">✓ {result.strengths?.[a]}</div>
                  <div className="text-amber-700">→ {result.improvements?.[a]}</div>
                </div>
              ))}
            </div>
          </details>
          <button
            onClick={() => onComplete?.(result)}
            className="px-4 py-2 bg-emerald-600 text-white rounded-lg"
          >
            Save & continue
          </button>
        </div>
      )}
    </article>
  );
}
