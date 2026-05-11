/**
 * AgeBandedReflectionPrompt — fetches a band-appropriate reflection prompt
 * (kids/tweens/teens/adults) and renders it with optional response capture.
 *
 * Props:
 *   - age: number  (required for band selection)
 *   - choiceIndex?: number  (rotate through prompts; default 0)
 *   - onSubmit?: (response: string) => void
 *   - autoFetch?: boolean (default true)
 */
import React, { useEffect, useState } from 'react';
import { getReflectionPrompts } from '../../api/retention';

const _btn = (bg) => ({
  padding: '8px 14px', borderRadius: 8, fontWeight: 700, background: bg,
  color: '#052e16', border: 'none', cursor: 'pointer', fontSize: 13,
});

export default function AgeBandedReflectionPrompt({ age, choiceIndex = 0, onSubmit, autoFetch = true }) {
  const [prompt, setPrompt] = useState(null);
  const [band, setBand] = useState(null);
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(autoFetch);

  useEffect(() => {
    if (!autoFetch || age === undefined || age === null) return;
    let cancelled = false;
    setLoading(true);
    getReflectionPrompts(age, choiceIndex)
      .then((data) => {
        if (cancelled) return;
        setPrompt(data?.prompt || (Array.isArray(data?.prompts) ? data.prompts[0] : null));
        setBand(data?.band);
      })
      .catch(() => { if (!cancelled) { setPrompt(null); setBand(null); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [age, choiceIndex, autoFetch]);

  if (loading) return <div style={{ color: '#9CA3AF', padding: 12 }}>Loading reflection…</div>;
  if (!prompt) return null;

  // Band-tinted accent
  const bandColor = {
    kids: '#FCD34D',
    tweens: '#34D399',
    teens: '#60A5FA',
    adults: '#A78BFA',
  }[band] || '#9CA3AF';

  return (
    <div style={{ background: '#1F2937', border: `1px solid ${bandColor}`,
                  borderRadius: 12, padding: 16, color: '#F9FAFB' }}>
      <div style={{ fontSize: 11, color: bandColor, fontWeight: 700,
                    textTransform: 'uppercase', letterSpacing: 0.5,
                    marginBottom: 6 }}>
        {band ? `${band} reflection` : 'Reflect'}
      </div>
      <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 10 }}>
        {prompt}
      </div>
      <textarea value={response} onChange={(e) => setResponse(e.target.value)}
        placeholder={band === 'kids' ? 'How did it feel?' : 'Your thoughts…'}
        style={{ width: '100%', minHeight: 80, padding: 10, borderRadius: 8,
                 border: '1px solid #4B5563', background: '#111827',
                 color: '#F9FAFB', fontSize: 14 }} />
      <button onClick={() => onSubmit && onSubmit(response)}
        disabled={!response.trim()}
        style={{ ..._btn(bandColor), marginTop: 10,
                 opacity: response.trim() ? 1 : 0.5 }}>
        Save reflection
      </button>
    </div>
  );
}
