/**
 * FieldMissionRenderer — offline human-research lesson type ("go interview
 * someone and log what they said"). Rendered by ModuleDetailPage.jsx as:
 *   <FieldMissionRenderer moduleId={moduleId} lessonId={activeLessonId}
 *     schema={activeLesson.schema} onCountChange={setFieldMissionCount} />
 *
 * Backed by real routes in backend/app.py:
 *   GET    /api/modules/:id/lessons/:lid/field-mission          -> { record: { entries: [...] } }
 *   POST   /api/modules/:id/lessons/:lid/field-mission/entry     body: { complaint, person, frequency, note, capture_type }
 *   DELETE /api/modules/:id/lessons/:lid/field-mission/entry/:eid
 * (see backend/app.py `api_module_field_mission_add_entry` for the exact
 * field names this form must send).
 */
import React, { useEffect, useState, useCallback } from 'react';
import { getFieldMission, addFieldMissionEntry, deleteFieldMissionEntry } from '../../api/modules';

const inputStyle = {
  width: '100%',
  padding: '8px 10px',
  borderRadius: 8,
  border: '1px solid #E5E7EB',
  fontSize: '0.9rem',
};

export default function FieldMissionRenderer({ moduleId, lessonId, schema, onCountChange }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({ person: '', complaint: '', frequency: '', note: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getFieldMission(moduleId, lessonId);
      const list = res?.record?.entries || [];
      setEntries(list);
      onCountChange?.(list.length);
    } catch {
      setEntries([]);
    } finally {
      setLoading(false);
    }
  }, [moduleId, lessonId, onCountChange]);

  useEffect(() => {
    load();
    setForm({ person: '', complaint: '', frequency: '', note: '' });
  }, [load]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.complaint.trim()) {
      setError('Write down what they told you first.');
      return;
    }
    setError('');
    setSubmitting(true);
    try {
      await addFieldMissionEntry(moduleId, lessonId, { ...form, capture_type: 'text' });
      setForm({ person: '', complaint: '', frequency: '', note: '' });
      await load();
    } catch (err) {
      setError(err?.response?.data?.error || 'Could not save that entry — try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (entryId) => {
    try {
      await deleteFieldMissionEntry(moduleId, lessonId, entryId);
      await load();
    } catch {
      setError('Could not delete that entry.');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {schema?.brief && (
        <p style={{ fontSize: '0.9rem', color: '#6D7286', fontStyle: 'italic' }}>{schema.brief}</p>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 10, background: '#F9FAFB', padding: 14, borderRadius: 12 }}>
        <div>
          <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Who did you talk to?</label>
          <input
            style={inputStyle}
            value={form.person}
            onChange={(e) => setForm((f) => ({ ...f, person: e.target.value }))}
            placeholder="e.g. my neighbour, the shopkeeper"
          />
        </div>
        <div>
          <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>What did they say? *</label>
          <textarea
            style={{ ...inputStyle, minHeight: 70, resize: 'vertical' }}
            value={form.complaint}
            onChange={(e) => setForm((f) => ({ ...f, complaint: e.target.value }))}
            placeholder="Write down what you heard, as close to their words as possible"
          />
        </div>
        <div>
          <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>How often does this happen?</label>
          <input
            style={inputStyle}
            value={form.frequency}
            onChange={(e) => setForm((f) => ({ ...f, frequency: e.target.value }))}
            placeholder="e.g. every day, once a week"
          />
        </div>
        {error && <div style={{ color: '#EF4444', fontSize: '0.85rem' }}>{error}</div>}
        <button
          type="submit"
          disabled={submitting}
          style={{
            padding: '10px 16px',
            borderRadius: 10,
            border: 'none',
            background: '#6C5CE7',
            color: '#fff',
            fontWeight: 700,
            cursor: submitting ? 'not-allowed' : 'pointer',
            opacity: submitting ? 0.7 : 1,
          }}
        >
          {submitting ? 'Saving…' : 'Log this entry'}
        </button>
      </form>

      <div>
        <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#6D7286', marginBottom: 8 }}>
          {loading ? 'Loading your entries…' : `${entries.length} entr${entries.length === 1 ? 'y' : 'ies'} logged`}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {entries.map((entry) => (
            <div
              key={entry.id || entry.entry_id}
              style={{ border: '1px solid #E5E7EB', borderRadius: 10, padding: 12, position: 'relative' }}
            >
              <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>{entry.person || 'Anonymous'}</div>
              <div style={{ fontSize: '0.9rem', margin: '4px 0' }}>{entry.complaint}</div>
              {entry.frequency && (
                <div style={{ fontSize: '0.75rem', color: '#9CA3AF' }}>Frequency: {entry.frequency}</div>
              )}
              <button
                onClick={() => handleDelete(entry.id || entry.entry_id)}
                style={{
                  position: 'absolute', top: 8, right: 8, border: 'none', background: 'transparent',
                  color: '#EF4444', cursor: 'pointer', fontSize: '0.8rem',
                }}
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
