// Sparkline.jsx
import React from 'react';
import { THEME, gainLossColor } from '../theme';

export default function Sparkline({
  values = [],
  width = 200,
  height = 40,
  stroke,
  strokeWidth = 1.5,
}) {
  if (!values.length) {
    return <svg width={width} height={height} aria-label="sparkline-empty" />;
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const dx = values.length > 1 ? width / (values.length - 1) : 0;
  const points = values
    .map((v, i) => `${(i * dx).toFixed(2)},${(height - ((v - min) / range) * height).toFixed(2)}`)
    .join(' ');
  const color = stroke ?? gainLossColor(values[values.length - 1] - values[0]);
  return (
    <svg width={width} height={height} aria-label="sparkline">
      <polyline points={points} fill="none" stroke={color} strokeWidth={strokeWidth} />
    </svg>
  );
}
