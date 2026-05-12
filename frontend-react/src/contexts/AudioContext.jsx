import React, { createContext, useContext, useRef, useState, useCallback } from "react";

const AudioCtx = createContext(null);

export function AudioProvider({ children }) {
  const audioRef = useRef(null);
  const [src, setSrc] = useState(null);
  const [playing, setPlaying] = useState(false);
  const [rate, setRate] = useState(1);

  const play = useCallback((url) => {
    if (!audioRef.current) return;
    if (url !== src) {
      audioRef.current.src = url;
      setSrc(url);
    }
    audioRef.current.playbackRate = rate;
    audioRef.current.play().catch(() => {});
  }, [src, rate]);

  const pause = useCallback(() => {
    audioRef.current?.pause();
  }, []);

  const setSpeed = useCallback((r) => {
    setRate(r);
    if (audioRef.current) audioRef.current.playbackRate = r;
  }, []);

  return (
    <AudioCtx.Provider value={{ src, playing, rate, play, pause, setSpeed, audioRef }}>
      {children}
      <audio
        ref={audioRef}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        preload="metadata"
      />
    </AudioCtx.Provider>
  );
}

export function useAudio() {
  const ctx = useContext(AudioCtx);
  if (!ctx) {
    // Safe no-op fallback for components rendered outside provider
    return {
      src: null, playing: false, rate: 1,
      play: () => {}, pause: () => {}, setSpeed: () => {},
      audioRef: { current: null },
    };
  }
  return ctx;
}
