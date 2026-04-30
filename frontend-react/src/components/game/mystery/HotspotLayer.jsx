/**
 * HotspotLayer — clickable bounding-box overlays on top of a mystery_room
 * background image. Renders one button per hotspot (examine / pickup) and
 * one per exit (move to another room). Coordinates in `bbox` are normalized
 * 0..1 of the parent's width/height.
 *
 * Props:
 *   - hotspots: Array<{ id, bbox: [x, y, w, h], hint?, yields_item?, puzzle_id? }>
 *   - exits:    Array<{ id, to, bbox: [x, y, w, h], label? }>
 *   - onExamine(hotspot)
 *   - onMoveTo(toRoomId)
 *
 * Accessibility: each hotspot is a real <button> with aria-label. A visually
 * hidden <ul> below the layer mirrors the hotspots so screen-reader users
 * (or keyboard users without spatial context) can pick from a list.
 */
import React from 'react';

const pct = (n) => `${(Number(n) || 0) * 100}%`;

const HotspotLayer = ({ hotspots = [], exits = [], onExamine, onMoveTo }) => {
  return (
    <>
      <div className="absolute inset-0 z-10" data-testid="hotspot-layer">
        {hotspots.map((spot) => {
          const [x, y, w, h] = spot.bbox || [0, 0, 0, 0];
          return (
            <button
              key={spot.id}
              type="button"
              onClick={() => onExamine?.(spot)}
              aria-label={spot.hint || `Examine ${spot.id}`}
              className="absolute group rounded-md border-2 border-transparent hover:border-yellow-300 hover:bg-yellow-300/10 focus:border-yellow-300 focus:bg-yellow-300/10 focus:outline-none transition-colors"
              style={{
                left: pct(x),
                top: pct(y),
                width: pct(w),
                height: pct(h),
              }}
            >
              <span className="sr-only">{spot.hint || spot.id}</span>
            </button>
          );
        })}

        {exits.map((exit) => {
          const [x, y, w, h] = exit.bbox || [0, 0, 0, 0];
          return (
            <button
              key={exit.id}
              type="button"
              onClick={() => onMoveTo?.(exit.to)}
              aria-label={exit.label || `Go to ${exit.to}`}
              className="absolute rounded-md border-2 border-transparent hover:border-emerald-300 hover:bg-emerald-300/10 focus:border-emerald-300 focus:bg-emerald-300/10 focus:outline-none transition-colors"
              style={{
                left: pct(x),
                top: pct(y),
                width: pct(w),
                height: pct(h),
              }}
            >
              <span className="sr-only">{exit.label || `Go to ${exit.to}`}</span>
            </button>
          );
        })}
      </div>

      {/* Screen-reader / keyboard fallback list */}
      <ul className="sr-only">
        {hotspots.map((spot) => (
          <li key={`sr-h-${spot.id}`}>
            <button type="button" onClick={() => onExamine?.(spot)}>
              {spot.hint || `Examine ${spot.id}`}
            </button>
          </li>
        ))}
        {exits.map((exit) => (
          <li key={`sr-e-${exit.id}`}>
            <button type="button" onClick={() => onMoveTo?.(exit.to)}>
              {exit.label || `Go to ${exit.to}`}
            </button>
          </li>
        ))}
      </ul>
    </>
  );
};

export default HotspotLayer;
