import { describe, it, expect } from 'vitest';
import { dayBoundaries } from './dayBoundaries';

const DAYS = [
  { id: 'mon', ticks: 4 },
  { id: 'tue', ticks: 4 },
  { id: 'wed', ticks: 4 },
  { id: 'thu', ticks: 4 },
  { id: 'fri', ticks: 4 },
];

describe('dayBoundaries', () => {
  it('returns first-of-day ticks (excluding tick 0)', () => {
    expect(dayBoundaries(DAYS)).toEqual([4, 8, 12, 16]);
  });

  it('returns empty for missing days', () => {
    expect(dayBoundaries([])).toEqual([]);
    expect(dayBoundaries(null)).toEqual([]);
  });

  it('returns empty for a single-day calendar', () => {
    expect(dayBoundaries([{ id: 'mon', ticks: 4 }])).toEqual([]);
  });

  it('handles missing/non-numeric ticks defensively', () => {
    expect(dayBoundaries([
      { id: 'mon', ticks: 4 },
      { id: 'tue' },               // missing ticks
      { id: 'wed', ticks: '4' },   // string ticks
    ])).toEqual([4, 4]); // 4 + 0 = 4; 4 + 0 + 4 NOT emitted (last day boundary excluded)
  });
});
