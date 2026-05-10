import React, { useState, useEffect } from 'react';
import { adminListOrgs, adminCreateOrg, adminUpdateOrg, adminDeleteOrg } from '../../api/org';

const EMPTY_FORM = {
  name: '',
  primary_color: '#6C5CE7',
  accent_color: '#00B894',
  logo_url: '',
  custom_dimensions: '',
  score_version: 1,
};

export default function OrgsSection() {
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editId, setEditId] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const load = async () => {
    try {
      const list = await adminListOrgs();
      setOrgs(list);
    } catch (e) {
      setError('Failed to load organisations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(''); setSuccess('');
    const payload = {
      ...form,
      custom_dimensions: form.custom_dimensions
        ? form.custom_dimensions.split(',').map(s => s.trim()).filter(Boolean)
        : null,
      score_version: form.score_version === 2 ? 2 : 1,
    };
    try {
      if (editId) {
        await adminUpdateOrg(editId, payload);
        setSuccess('Organisation updated');
      } else {
        await adminCreateOrg(payload);
        setSuccess('Organisation created');
      }
      setForm(EMPTY_FORM);
      setEditId(null);
      load();
    } catch (e) {
      setError(e?.response?.data?.error || 'Save failed');
    }
  };

  const handleEdit = (org) => {
    setEditId(org.id);
    setForm({
      name: org.name || '',
      primary_color: org.primary_color || '#6C5CE7',
      accent_color: org.accent_color || '#00B894',
      logo_url: org.logo_url || '',
      custom_dimensions: (org.custom_dimensions || []).join(', '),
      score_version: org.score_version === 2 ? 2 : 1,
    });
  };

  const handleDelete = async (orgId) => {
    if (!confirm('Delete this organisation? Users in this org will be moved to default.')) return;
    setError('');
    try {
      await adminDeleteOrg(orgId);
      setSuccess('Organisation deleted');
      load();
    } catch (e) {
      setError(e?.response?.data?.error || 'Delete failed');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">🏢 Organisations</h2>
        <span className="text-gray-400 text-sm">{orgs.length} org{orgs.length !== 1 ? 's' : ''}</span>
      </div>

      {error && <div className="bg-red-900/40 text-red-300 px-4 py-2 rounded-lg text-sm">{error}</div>}
      {success && <div className="bg-green-900/40 text-green-300 px-4 py-2 rounded-lg text-sm">{success}</div>}

      {/* Org Table */}
      {loading ? (
        <div className="text-gray-400 text-sm">Loading...</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left text-gray-300">
            <thead className="text-xs text-gray-400 uppercase bg-gray-800">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Primary</th>
                <th className="px-4 py-3">Accent</th>
                <th className="px-4 py-3">Logo URL</th>
                <th className="px-4 py-3">Custom Dims</th>
                <th className="px-4 py-3">Scoring</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {orgs.map(org => (
                <tr key={org.id} className="border-b border-gray-700 hover:bg-gray-800/50">
                  <td className="px-4 py-3 font-medium text-white">
                    {org.name}
                    {org.id === 'default' && <span className="ml-2 text-xs text-gray-500">(default)</span>}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-5 h-5 rounded" style={{ backgroundColor: org.primary_color }} />
                      <span className="font-mono text-xs">{org.primary_color}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-5 h-5 rounded" style={{ backgroundColor: org.accent_color }} />
                      <span className="font-mono text-xs">{org.accent_color}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400 truncate max-w-[120px]">{org.logo_url || '—'}</td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {org.custom_dimensions ? org.custom_dimensions.join(', ') : '— all 8 —'}
                  </td>
                  <td className="px-4 py-3 text-xs">
                    {org.score_version === 2 ? (
                      <span className="px-2 py-1 rounded bg-emerald-900/40 text-emerald-300 font-mono">v2 (CI)</span>
                    ) : (
                      <span className="px-2 py-1 rounded bg-gray-700 text-gray-300 font-mono">v1</span>
                    )}
                  </td>
                  <td className="px-4 py-3 flex gap-2">
                    <button
                      onClick={() => handleEdit(org)}
                      className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs"
                    >Edit</button>
                    {org.id !== 'default' && (
                      <button
                        onClick={() => handleDelete(org.id)}
                        className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs"
                      >Delete</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add / Edit Form */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">{editId ? 'Edit Organisation' : 'Add Organisation'}</h3>
        <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Name *</label>
            <input
              required
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm"
              placeholder="Acme Corp"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Logo URL</label>
            <input
              value={form.logo_url}
              onChange={e => setForm(f => ({ ...f, logo_url: e.target.value }))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm"
              placeholder="https://..."
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Primary Color</label>
            <div className="flex gap-2 items-center">
              <input
                type="color"
                value={form.primary_color}
                onChange={e => setForm(f => ({ ...f, primary_color: e.target.value }))}
                className="w-10 h-10 rounded cursor-pointer border-0 bg-transparent"
              />
              <input
                value={form.primary_color}
                onChange={e => setForm(f => ({ ...f, primary_color: e.target.value }))}
                className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm font-mono"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Accent Color</label>
            <div className="flex gap-2 items-center">
              <input
                type="color"
                value={form.accent_color}
                onChange={e => setForm(f => ({ ...f, accent_color: e.target.value }))}
                className="w-10 h-10 rounded cursor-pointer border-0 bg-transparent"
              />
              <input
                value={form.accent_color}
                onChange={e => setForm(f => ({ ...f, accent_color: e.target.value }))}
                className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm font-mono"
              />
            </div>
          </div>
          <div className="md:col-span-2">
            <label className="block text-xs text-gray-400 mb-1">
              Custom Dimensions <span className="text-gray-500">(comma-separated; leave blank for all 8)</span>
            </label>
            <input
              value={form.custom_dimensions}
              onChange={e => setForm(f => ({ ...f, custom_dimensions: e.target.value }))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm"
              placeholder="strategic_thinking, empathy, ethical_reasoning"
            />
          </div>
          <div className="md:col-span-2">
            <label className="flex items-start gap-3 p-3 bg-gray-900/40 rounded-lg cursor-pointer hover:bg-gray-900/60">
              <input
                type="checkbox"
                checked={form.score_version === 2}
                onChange={e => setForm(f => ({ ...f, score_version: e.target.checked ? 2 : 1 }))}
                className="mt-0.5 w-4 h-4 accent-emerald-500"
              />
              <span className="flex-1 text-sm text-gray-200">
                <span className="font-semibold">Use v2 scoring</span>
                <span className="ml-2 px-2 py-0.5 rounded bg-amber-900/40 text-amber-300 text-[10px] font-mono uppercase tracking-wider">Pilot</span>
                <span className="block text-xs text-gray-400 mt-0.5">
                  Blended authored + behavioral signals with 90% confidence intervals on each dimension. Default off — enable for shadow rollout pilots only.
                </span>
              </span>
            </label>
          </div>
          <div className="md:col-span-2 flex gap-3">
            <button
              type="submit"
              className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium"
            >
              {editId ? 'Update' : 'Create'}
            </button>
            {editId && (
              <button
                type="button"
                onClick={() => { setEditId(null); setForm(EMPTY_FORM); }}
                className="px-6 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg text-sm"
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
