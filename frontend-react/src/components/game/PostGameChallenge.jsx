/**
 * PostGameChallenge — "Challenge a friend" card shown to students after a
 * run. Creates a shareable challenge code via /api/challenge/create so a
 * friend can try to beat this score on the same game.
 */
import { useState } from 'react';
import { FaTrophy, FaCopy, FaCheck } from 'react-icons/fa';
import { createChallenge } from '../../api/challenge';

export default function PostGameChallenge({ runId, score }) {
  const [challenge, setChallenge] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');

  const handleCreate = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await createChallenge(runId);
      setChallenge(data.challenge);
    } catch {
      setError("Couldn't create a challenge right now.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (!challenge) return;
    navigator.clipboard?.writeText(challenge.id).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (!runId) return null;

  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 mb-4">
      <div className="flex items-center gap-2 text-sm font-bold text-amber-800 mb-2">
        <FaTrophy /> Challenge a Friend
      </div>
      {!challenge ? (
        <>
          <p className="text-xs text-amber-700 mb-3">
            Share your score of {score} and see if a friend can beat it.
          </p>
          <button
            onClick={handleCreate}
            disabled={loading}
            className="px-3 py-1.5 text-xs font-bold rounded-lg bg-amber-500 text-white hover:bg-amber-600 disabled:opacity-60"
          >
            {loading ? 'Creating…' : 'Create Challenge'}
          </button>
          {error && <p className="text-[11px] text-red-600 mt-2">{error}</p>}
        </>
      ) : (
        <div className="flex items-center gap-2">
          <code className="text-xs bg-white border border-amber-200 rounded-lg px-2 py-1 font-mono">
            {challenge.id}
          </code>
          <button
            onClick={handleCopy}
            className="text-xs font-semibold text-amber-700 hover:text-amber-900 flex items-center gap-1"
          >
            {copied ? <FaCheck /> : <FaCopy />} {copied ? 'Copied' : 'Copy code'}
          </button>
        </div>
      )}
    </div>
  );
}
