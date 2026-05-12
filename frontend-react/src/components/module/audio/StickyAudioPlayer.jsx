import React from "react";
import { useAudio } from "../../../contexts/AudioContext";

export default function StickyAudioPlayer() {
  const { src, playing, rate, play, pause, setSpeed } = useAudio();
  if (!src) return null;
  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-lg p-3 flex items-center gap-3 z-40">
      <button
        onClick={() => (playing ? pause() : play(src))}
        className="px-3 py-2 bg-sky-600 text-white rounded-lg"
        aria-label={playing ? "Pause narration" : "Resume narration"}
      >
        {playing ? "⏸" : "▶"}
      </button>
      <div className="flex-1 text-xs text-gray-600 truncate">
        Now playing: lesson narration
      </div>
      <div className="flex gap-1">
        {[1, 1.25, 1.5].map((r) => (
          <button
            key={r}
            onClick={() => setSpeed(r)}
            className={`px-2 py-1 text-xs rounded ${rate === r ? "bg-sky-600 text-white" : "bg-gray-100"}`}
            aria-label={`Set speed ${r}x`}
            aria-pressed={rate === r}
          >
            {r}×
          </button>
        ))}
      </div>
    </div>
  );
}
