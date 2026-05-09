export const THEME = Object.freeze({
  bgPage: '#FFF9EE',
  bgTile: '#FFF3DC',
  borderTile: '#F5E6C8',
  textPrimary: '#633806',
  textMuted: '#854F0B',
  accentWarm: '#B46B1E',
  gain: '#0F6E56',
  loss: '#A32D2D',
  neutral: '#633806',
});

export function gainLossColor(value) {
  if (value > 0) return THEME.gain;
  if (value < 0) return THEME.loss;
  return THEME.neutral;
}
