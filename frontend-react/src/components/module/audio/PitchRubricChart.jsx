import React from "react";

const AXES = ["hook", "problem", "solution", "customer", "ask"];

export default function PitchRubricChart({ scores = {} }) {
  return (
    <div className="space-y-2">
      {AXES.map((a) => (
        <div key={a} className="flex items-center gap-3">
          <div className="w-24 text-sm capitalize">{a}</div>
          <div className="flex-1 bg-gray-200 rounded-full h-3 overflow-hidden">
            <div
              className="bg-emerald-500 h-full"
              style={{ width: `${Math.max(0, Math.min(10, scores[a] || 0)) * 10}%` }}
            />
          </div>
          <div className="w-10 text-sm text-right">{scores[a] ?? 0}/10</div>
        </div>
      ))}
    </div>
  );
}
