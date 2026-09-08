/**
 * AssessmentReport — teacher/admin-only expandable detail view.
 * Only mounted for admin/teacher/school_admin/hr roles; placeholder
 * until the full assessment breakdown UI is built.
 */
export default function AssessmentReport({ initialData }) {
  if (!initialData) {
    return <p className="text-xs text-gray-400 italic">Assessment report not available for this run.</p>;
  }
  return (
    <pre className="text-[11px] text-gray-600 bg-gray-50 rounded-lg p-3 overflow-x-auto">
      {JSON.stringify(initialData, null, 2)}
    </pre>
  );
}
