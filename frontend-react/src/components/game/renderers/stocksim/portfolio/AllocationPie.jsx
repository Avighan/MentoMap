// AllocationPie.jsx
import React from 'react';

const PALETTE = ['#B46B1E', '#0F6E56', '#A32D2D', '#854F0B', '#3F6FB0', '#7A3FA8', '#D4A645', '#5B7C2F'];

function arcPath(cx, cy, r, startAngle, endAngle) {
  const x1 = cx + r * Math.cos(startAngle);
  const y1 = cy + r * Math.sin(startAngle);
  const x2 = cx + r * Math.cos(endAngle);
  const y2 = cy + r * Math.sin(endAngle);
  const largeArc = endAngle - startAngle > Math.PI ? 1 : 0;
  return `M ${cx},${cy} L ${x1},${y1} A ${r},${r} 0 ${largeArc} 1 ${x2},${y2} Z`;
}

export default function AllocationPie({ slices = [], size = 120, onSliceClick }) {
  const total = slices.reduce((s, x) => s + (x.value || 0), 0);
  if (total <= 0) return <svg width={size} height={size} aria-label="pie-empty" />;
  const r = size / 2;
  let acc = -Math.PI / 2;
  return (
    <svg width={size} height={size} aria-label="allocation-pie">
      {slices.map((s, i) => {
        const angle = (s.value / total) * Math.PI * 2;
        const d = arcPath(r, r, r, acc, acc + angle);
        const path = (
          <path
            key={s.label}
            d={d}
            fill={PALETTE[i % PALETTE.length]}
            data-slice={s.label}
            style={{ cursor: onSliceClick ? 'pointer' : 'default' }}
            onClick={onSliceClick ? () => onSliceClick(s.label) : undefined}
          />
        );
        acc += angle;
        return path;
      })}
    </svg>
  );
}
