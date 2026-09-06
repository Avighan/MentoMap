/**
 * PilotGamePlayPage — real play-through UI for the three Phase 1 pilot
 * games (dealcraft, mumbai_manufacturer, heliogrid). These have a
 * different backend contract than the legacy generic engine GamePlayPage.jsx
 * uses (routes/grader_routes.py's per-game /choose, /quarter, /complete
 * endpoints — see that file's docstring), and GamePlayPage.jsx itself
 * depends on ~50 other components/contexts that were never committed to
 * this repo (a much larger gap than the "restore the bootstrap files"
 * scope this page fills) — so this is a new, focused page rather than an
 * attempt to route pilot games through that page.
 *
 * Backend routes exercised here, all real (see backend/routes/grader_routes.py):
 *   POST /api/run/start                          -> { run_id, game_data, ... }
 *   POST /api/run/<id>/dealcraft/choose           { round_id, choice_id }
 *   POST /api/run/<id>/mumbai_manufacturer/choose { round_id, choice_id, event_choice_id? }
 *   POST /api/run/<id>/heliogrid/quarter          { action }
 *   POST /api/run/<id>/complete                   -> { summary: { score, band, dimension_scores } }
 */
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { startGame, dealcraftChoose, mumbaiManufacturerChoose, heliogridQuarter, completePilotRun } from '../api/games';
import { LoadingState } from '../components/ui/LoadingSpinner';

const PILOT_GAME_IDS = new Set(['dealcraft', 'mumbai_manufacturer', 'heliogrid']);

// heliogrid's action is a multi-lever pricing/ops form (listPrice, discounts
// per segment, sales allocation per segment, headcount, spend) rather than a
// pick-one-of-four choice — a full lever-by-lever editor is future work, so
// this plays a single reasonable default action each quarter (still a real
// POST to the real endpoint, just not an interactive form for every lever).
const HELIOGRID_DEFAULT_ACTION = {
  listPrice: 162000,
  discounts: { campus_estates: 5, process_plants: 0, retail_chains: 8, installer_guild: 10 },
  salesAlloc: { campus_estates: 30, process_plants: 15, retail_chains: 30, installer_guild: 25 },
  headcount: 12,
  commsSpend: 60000,
  researchSpend: 40000,
};

export default function PilotGamePlayPage() {
  const { gameId } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [runId, setRunId] = useState(null);
  const [game, setGame] = useState(null);
  const [roundIndex, setRoundIndex] = useState(0);
  const [quarterIndex, setQuarterIndex] = useState(0);
  const [log, setLog] = useState([]);
  const [summary, setSummary] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    startGame(gameId)
      .then((data) => {
        if (cancelled) return;
        setRunId(data.run_id);
        setGame(data.game_data);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err?.response?.data?.error || 'Could not start this game.');
      })
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [gameId]);

  if (loading) return <LoadingState label="Starting run…" />;
  if (error) {
    return (
      <div style={{ maxWidth: 600, margin: '80px auto', textAlign: 'center', padding: 16 }}>
        <p style={{ color: '#EF4444' }}>{error}</p>
        <button onClick={() => navigate('/games')}>Back to games</button>
      </div>
    );
  }
  if (!PILOT_GAME_IDS.has(gameId)) {
    return (
      <div style={{ maxWidth: 600, margin: '80px auto', textAlign: 'center', padding: 16 }}>
        <p>
          "{game?.title || gameId}" isn't wired into the rebuilt UI yet — only the three
          Phase 1 pilot games (Dealcraft, Mumbai Manufacturer, HelioGrid) have a play
          screen so far. A run was started for it on the backend (run id: {runId}),
          it just has no frontend renderer here.
        </p>
        <button onClick={() => navigate('/games')}>Back to games</button>
      </div>
    );
  }

  const handleDealMumbaiChoice = async (choiceId) => {
    const rounds = game.rounds;
    const round = rounds[roundIndex];
    setSubmitting(true);
    setError('');
    try {
      let res;
      if (gameId === 'dealcraft') {
        res = await dealcraftChoose(runId, round.id, choiceId);
      } else {
        // mumbai_manufacturer schedules a crisis event after some rounds —
        // the route 400s with the event payload when one is due and no
        // event_choice_id was sent. Auto-picking the first event option
        // keeps this page's flow to one click per round rather than adding
        // a second modal step for the ~1/3 of rounds that have one.
        try {
          res = await mumbaiManufacturerChoose(runId, round.id, choiceId);
        } catch (err) {
          const event = err?.response?.data?.event;
          if (err?.response?.status === 400 && event?.choices?.length) {
            res = await mumbaiManufacturerChoose(runId, round.id, choiceId, event.choices[0].id);
          } else {
            throw err;
          }
        }
      }
      setLog((prev) => [...prev, { round: round.title, choice: choiceId, state: res.state }]);
      if (roundIndex + 1 >= rounds.length) {
        const done = await completePilotRun(runId);
        setSummary(done.summary);
      } else {
        setRoundIndex((i) => i + 1);
      }
    } catch (err) {
      setError(err?.response?.data?.error || 'Choice failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleHeliogridQuarter = async () => {
    setSubmitting(true);
    setError('');
    try {
      const res = await heliogridQuarter(runId, HELIOGRID_DEFAULT_ACTION);
      setLog((prev) => [...prev, { quarter: quarterIndex + 1, result: res.quarter_result }]);
      const totalQuarters = (game.simulation_config?.quarters) || 4;
      if (quarterIndex + 1 >= totalQuarters) {
        const done = await completePilotRun(runId);
        setSummary(done.summary);
      } else {
        setQuarterIndex((i) => i + 1);
      }
    } catch (err) {
      setError(err?.response?.data?.error || 'Quarter simulation failed.');
    } finally {
      setSubmitting(false);
    }
  };

  if (summary) {
    return (
      <div style={{ maxWidth: 600, margin: '60px auto', textAlign: 'center', padding: 16 }}>
        <h1>Run complete!</h1>
        <div style={{ fontSize: 48, fontWeight: 'bold', color: '#6C5CE7' }}>{summary.score}</div>
        <div style={{ fontSize: 20 }}>Band: {summary.band}</div>
        {summary.label && <p>{summary.label}</p>}
        {summary.dimension_scores && (
          <ul style={{ listStyle: 'none', padding: 0, textAlign: 'left', maxWidth: 300, margin: '16px auto' }}>
            {Object.entries(summary.dimension_scores).map(([dim, val]) => (
              <li key={dim} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
                <span>{dim}</span><strong>{val}</strong>
              </li>
            ))}
          </ul>
        )}
        <button onClick={() => navigate('/games')}>Back to games</button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 700, margin: '40px auto', padding: 16 }}>
      <h1>{game.title}</h1>
      {error && <p style={{ color: '#EF4444' }}>{error}</p>}

      {gameId === 'heliogrid' ? (
        <div>
          <p>Quarter {quarterIndex + 1}</p>
          <p>Playing a default balanced strategy each quarter (full lever controls are a future enhancement).</p>
          <button disabled={submitting} onClick={handleHeliogridQuarter}>
            {submitting ? 'Resolving…' : 'Run quarter'}
          </button>
        </div>
      ) : (
        <div>
          <p>Round {roundIndex + 1} of {game.rounds.length}</p>
          <h3>{game.rounds[roundIndex].title}</h3>
          <p>{game.rounds[roundIndex].prompt}</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {game.rounds[roundIndex].choices.map((c) => (
              <button
                key={c.id}
                disabled={submitting}
                onClick={() => handleDealMumbaiChoice(c.id)}
                style={{ textAlign: 'left', padding: 12, borderRadius: 8, border: '1px solid #ddd', cursor: 'pointer' }}
              >
                <strong>{c.label}</strong>
                {c.description && <div style={{ fontSize: 13, color: '#6D7286' }}>{c.description}</div>}
              </button>
            ))}
          </div>
        </div>
      )}

      {log.length > 0 && (
        <div style={{ marginTop: 24, fontSize: 12, color: '#6D7286' }}>
          {log.length} step(s) played so far.
        </div>
      )}
    </div>
  );
}
