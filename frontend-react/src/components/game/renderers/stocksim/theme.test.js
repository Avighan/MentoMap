import { describe, it, expect } from 'vitest';
import { THEME, gainLossColor } from './theme';

describe('stocksim theme', () => {
  it('exposes the warm-amber palette tokens', () => {
    expect(THEME.bgPage).toBe('#FFF9EE');
    expect(THEME.bgTile).toBe('#FFF3DC');
    expect(THEME.borderTile).toBe('#F5E6C8');
    expect(THEME.textPrimary).toBe('#633806');
    expect(THEME.textMuted).toBe('#854F0B');
    expect(THEME.accentWarm).toBe('#B46B1E');
    expect(THEME.gain).toBe('#0F6E56');
    expect(THEME.loss).toBe('#A32D2D');
    expect(THEME.neutral).toBe('#633806');
  });

  it('gainLossColor returns gain for positive, loss for negative, neutral for zero', () => {
    expect(gainLossColor(1.5)).toBe(THEME.gain);
    expect(gainLossColor(-0.01)).toBe(THEME.loss);
    expect(gainLossColor(0)).toBe(THEME.neutral);
  });
});
