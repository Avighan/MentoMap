// dayBoundaries.js
// Returns the tick indices that are the FIRST tick of each day after the first.
// Used to render dashed vertical separators on charts and to drive day-rollover
// detection in the host renderer. Pure / side-effect-free.
//
// Example: DAYS=[mon(4), tue(4), wed(4), thu(4), fri(4)] → [4, 8, 12, 16].
// (The first day starts at tick 0 — never emitted.
//  The last day's end-tick is the run end — also never emitted.)
export function dayBoundaries(days) {
  if (!Array.isArray(days) || days.length <= 1) return [];
  const out = [];
  let acc = 0;
  for (let i = 0; i < days.length - 1; i++) {
    acc += Number(days[i].ticks || 0);
    out.push(acc);
  }
  return out;
}
