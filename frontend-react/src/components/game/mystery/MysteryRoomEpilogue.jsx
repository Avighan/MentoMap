/**
 * MysteryRoomEpilogue — final outcome panel for the mystery_room game type
 * (Task 22 of mystery-room plan).
 *
 * Rendered as the `epilogueSlot` of `PostGameInsights`. Shows the chosen
 * ending's image / title / paragraphs, names the soft skill the outcome
 * embodies, and lists any evidence the player missed (with a nudge to
 * replay).
 *
 * Props:
 *   epilogue        — { title, image, paragraphs[], soft_skill_named } from
 *                     report_core.epilogue.
 *   outcomeLabel    — climax option ID (e.g. "whistleblower").
 *   knowledgeScore  — 0–100, fraction of factual puzzles answered correctly.
 *   missedClues     — [{ id, label }] — evidence items that were not collected.
 */
export default function MysteryRoomEpilogue({
  epilogue,
  outcomeLabel,
  knowledgeScore,
  missedClues = [],
}) {
  if (!epilogue) return null;
  const paragraphs = Array.isArray(epilogue.paragraphs) ? epilogue.paragraphs : [];

  return (
    <div className="bg-gradient-to-b from-stone-900 to-stone-800 text-stone-100 rounded-lg p-6 mb-4">
      {epilogue.image && (
        <img
          src={epilogue.image}
          alt={epilogue.title || 'Mystery room ending'}
          className="w-full max-h-72 object-cover rounded mb-4"
        />
      )}
      {epilogue.title && (
        <h2 className="text-2xl font-semibold mb-2">{epilogue.title}</h2>
      )}
      {paragraphs.map((p, i) => (
        <p key={i} className="text-stone-300 mb-2 leading-relaxed">{p}</p>
      ))}

      {epilogue.soft_skill_named && (
        <div className="mt-5 pt-4 border-t border-stone-700">
          <p className="text-sm text-amber-300">{epilogue.soft_skill_named}</p>
        </div>
      )}

      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        {outcomeLabel && (
          <div>
            <dt className="text-stone-500">Outcome</dt>
            <dd className="font-medium">{outcomeLabel}</dd>
          </div>
        )}
        {typeof knowledgeScore === 'number' && (
          <div>
            <dt className="text-stone-500">Knowledge accuracy</dt>
            <dd className="font-medium">{knowledgeScore}%</dd>
          </div>
        )}
      </dl>

      {missedClues.length > 0 && (
        <div className="mt-4 p-3 bg-stone-800 rounded">
          <p className="text-sm text-stone-400 mb-1">Clues you didn't find:</p>
          <ul className="text-sm text-stone-300 list-disc list-inside">
            {missedClues.map((c) => <li key={c.id}>{c.label}</li>)}
          </ul>
          <p className="text-xs text-stone-500 mt-2">
            Replay to see how the story changes.
          </p>
        </div>
      )}
    </div>
  );
}
