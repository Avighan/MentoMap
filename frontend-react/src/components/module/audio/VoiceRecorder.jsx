// frontend-react/src/components/module/audio/VoiceRecorder.jsx
import React, { useRef, useState } from "react";

export default function VoiceRecorder({ maxSeconds = 60, onRecorded }) {
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [blob, setBlob] = useState(null);
  const recRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  const stop = () => {
    if (recRef.current && recRef.current.state !== "inactive") recRef.current.stop();
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    setRecording(false);
  };

  const start = async () => {
    chunksRef.current = [];
    setBlob(null);
    setElapsed(0);
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const rec = new MediaRecorder(stream);
    rec.ondataavailable = (e) => chunksRef.current.push(e.data);
    rec.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      const b = new Blob(chunksRef.current, { type: "audio/webm" });
      setBlob(b);
      onRecorded?.(b);
    };
    rec.start();
    recRef.current = rec;
    setRecording(true);
    timerRef.current = setInterval(() => {
      setElapsed((s) => {
        if (s + 1 >= maxSeconds) { stop(); return maxSeconds; }
        return s + 1;
      });
    }, 1000);
  };

  return (
    <div className="border rounded-xl p-4 space-y-3">
      <div className="flex items-center gap-3">
        {!recording ? (
          <button onClick={start} className="px-4 py-2 bg-rose-600 text-white rounded-lg">🎙 Record</button>
        ) : (
          <button onClick={stop} className="px-4 py-2 bg-gray-800 text-white rounded-lg">⏹ Stop</button>
        )}
        <div className="text-sm text-gray-600">
          {elapsed}s / {maxSeconds}s
        </div>
      </div>
      {blob && (
        <audio controls src={URL.createObjectURL(blob)} className="w-full" />
      )}
    </div>
  );
}
