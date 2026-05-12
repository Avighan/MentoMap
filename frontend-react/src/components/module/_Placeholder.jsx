import React from "react";
export default function Placeholder({ title, type, phase }) {
  return (
    <div className="rounded-2xl border-2 border-dashed p-8 bg-gray-50 text-center">
      <div className="text-3xl mb-2">🛠️</div>
      <h3 className="text-lg font-semibold">{title || type}</h3>
      <p className="text-sm text-gray-600">This feature ships in Phase {phase}.</p>
    </div>
  );
}
