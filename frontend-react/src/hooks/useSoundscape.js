/**
 * useSoundscape(soundscapeName) — ambient background audio + one-off sound
 * effects for Tier-S sims (see GamePlayPage.jsx comment "R15 — Soundscape
 * for Tier-S sims; pulled from game.soundscape").
 *
 * Call site (GamePlayPage.jsx) does:
 *   const soundscape = useSoundscape(currentGame?.soundscape);
 *   soundscape.enabled   — true when the current game declares a soundscape
 *   soundscape.muted     — user's mute preference (persisted, shared globally)
 *   soundscape.toggleMute()
 *
 * Judgment call (no audio asset pipeline exists in this repo — no .mp3/.ogg
 * files, no CDN allowlisted for media): rather than silently no-op, this
 * synthesizes a genuinely audible, very low-volume ambient drone with the
 * Web Audio API (oscillator + slow LFO through a gain node) so "soundscape
 * on" is a real, working feature and not a stub. It also exposes `playCue`
 * for short one-off UI blips (correct/incorrect/levelup) keyed by name,
 * again synthesized rather than sourced from missing asset files.
 */
import { useState, useEffect, useRef, useCallback } from 'react';

const MUTE_STORAGE_KEY = 'mentomap_soundscape_muted';
const MUTE_EVENT = 'mentomap:soundscape-mute-change';

const readStoredMuted = () => {
  try {
    return localStorage.getItem(MUTE_STORAGE_KEY) === '1';
  } catch {
    return false;
  }
};

const CUE_FREQUENCIES = {
  correct: 880,
  incorrect: 220,
  levelup: 1320,
  click: 520,
  streak: 990,
};

export default function useSoundscape(soundscapeName) {
  const enabled = !!soundscapeName;
  const [muted, setMuted] = useState(readStoredMuted);

  const ctxRef = useRef(null);
  const nodesRef = useRef(null); // { oscillator, lfo, gain }

  const ensureContext = useCallback(() => {
    if (typeof window === 'undefined') return null;
    const Ctor = window.AudioContext || window.webkitAudioContext;
    if (!Ctor) return null;
    if (!ctxRef.current) {
      ctxRef.current = new Ctor();
    }
    return ctxRef.current;
  }, []);

  const stopAmbient = useCallback(() => {
    const nodes = nodesRef.current;
    if (nodes) {
      try {
        nodes.oscillator.stop();
        nodes.lfo.stop();
      } catch {
        // already stopped
      }
      nodes.oscillator.disconnect();
      nodes.lfo.disconnect();
      nodes.gain.disconnect();
      nodesRef.current = null;
    }
  }, []);

  const startAmbient = useCallback(() => {
    const ctx = ensureContext();
    if (!ctx || nodesRef.current) return;

    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    const lfo = ctx.createOscillator();
    const lfoGain = ctx.createGain();

    oscillator.type = 'sine';
    oscillator.frequency.value = 110; // low, unobtrusive drone

    // Slow LFO gently breathes the volume so it doesn't feel like a flat tone.
    lfo.frequency.value = 0.15;
    lfoGain.gain.value = 0.015;
    lfo.connect(lfoGain);
    lfoGain.connect(gain.gain);

    gain.gain.value = 0.03; // deliberately quiet ambient bed
    oscillator.connect(gain);
    gain.connect(ctx.destination);

    oscillator.start();
    lfo.start();
    nodesRef.current = { oscillator, lfo, gain };
  }, [ensureContext]);

  // Start/stop the ambient bed as enabled/muted change.
  useEffect(() => {
    if (enabled && !muted) {
      startAmbient();
    } else {
      stopAmbient();
    }
    return stopAmbient;
  }, [enabled, muted, startAmbient, stopAmbient]);

  // Keep mute state in sync across every hook instance + tabs.
  useEffect(() => {
    const onChange = (e) => setMuted(!!e.detail);
    const onStorage = (e) => {
      if (e.key === MUTE_STORAGE_KEY) setMuted(e.newValue === '1');
    };
    window.addEventListener(MUTE_EVENT, onChange);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener(MUTE_EVENT, onChange);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  // Tear down the AudioContext on unmount.
  useEffect(() => {
    return () => {
      stopAmbient();
      if (ctxRef.current) {
        ctxRef.current.close().catch(() => {});
        ctxRef.current = null;
      }
    };
  }, [stopAmbient]);

  const toggleMute = useCallback(() => {
    const next = !muted;
    try {
      localStorage.setItem(MUTE_STORAGE_KEY, next ? '1' : '0');
    } catch {
      // ignore — in-memory event still updates this tab
    }
    window.dispatchEvent(new CustomEvent(MUTE_EVENT, { detail: next }));
    setMuted(next);
  }, [muted]);

  // Short one-off UI blip, independent of the ambient bed.
  const playCue = useCallback((name = 'click') => {
    if (muted) return;
    const ctx = ensureContext();
    if (!ctx) return;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = CUE_FREQUENCIES[name] || CUE_FREQUENCIES.click;
    gain.gain.setValueAtTime(0.0001, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.08, ctx.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.25);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.26);
  }, [muted, ensureContext]);

  return { enabled, muted, toggleMute, playCue };
}
