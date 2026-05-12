// frontend-react/src/components/module/UnknownLessonRenderer.jsx
import React from "react";

export default function UnknownLessonRenderer({ lesson }) {
  return (
    <div className="rounded-2xl border-2 border-dashed border-gray-300 p-8 text-center bg-gray-50">
      <div className="text-4xl mb-2">🚧</div>
      <h3 className="text-lg font-semibold mb-1">{lesson?.title || "Coming soon"}</h3>
      <p className="text-sm text-gray-600">
        This lesson uses a new format ({lesson?.type}) that will be available in an upcoming update.
      </p>
    </div>
  );
}
