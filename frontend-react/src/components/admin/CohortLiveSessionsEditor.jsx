import { useEffect, useState } from "react";
import {
  listCohortLiveSessions,
  createCohortLiveSession,
  updateCohortLiveSession,
  deleteCohortLiveSession,
} from "../../api/modules";

const EMPTY = {
  week: 1,
  title: "",
  host_name: "",
  host_bio_short: "",
  scheduled_at: "",
  duration_min: 60,
  meeting_url: "",
  recording_url: "",
};

/**
 * Admin/teacher editor for cohort live sessions.
 *
 * Props:
 *  - cohortId (string, required): cohort identifier
 *  - moduleId (string, optional, default 'mento_entrepreneur_4week')
 */
export default function CohortLiveSessionsEditor({
  cohortId,
  moduleId = "mento_entrepreneur_4week",
}) {
  const [sessions, setSessions] = useState([]);
  const [draft, setDraft] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState(null);

  const reload = () =>
    listCohortLiveSessions(cohortId, moduleId)
      .then((d) => setSessions(d?.sessions || []))
      .catch(() => setSessions([]));

  useEffect(() => {
    if (cohortId) reload();
  }, [cohortId, moduleId]);

  const create = async () => {
    setSaving(true);
    setErr(null);
    try {
      await createCohortLiveSession(cohortId, moduleId, draft);
      setDraft(EMPTY);
      await reload();
    } catch (e) {
      setErr(e?.response?.data?.error || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (sid) => {
    if (!window.confirm("Delete this session?")) return;
    try {
      await deleteCohortLiveSession(cohortId, moduleId, sid);
      await reload();
    } catch (e) {
      // ignore
    }
  };

  const setRecording = async (sid, url) => {
    try {
      await updateCohortLiveSession(cohortId, moduleId, sid, {
        recording_url: url,
        status: "recorded",
      });
      await reload();
    } catch (e) {
      // ignore
    }
  };

  if (!cohortId) {
    return (
      <div className="text-sm text-slate-500">
        Select a cohort to schedule live sessions.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="font-semibold">Live sessions — {moduleId}</h3>
      <div className="rounded border p-3 grid grid-cols-2 gap-2 text-sm">
        <label>
          Week
          <input
            type="number"
            min={1}
            max={4}
            value={draft.week}
            onChange={(e) => setDraft({ ...draft, week: +e.target.value })}
            className="w-full border p-1"
          />
        </label>
        <label>
          Title
          <input
            value={draft.title}
            onChange={(e) => setDraft({ ...draft, title: e.target.value })}
            className="w-full border p-1"
          />
        </label>
        <label>
          Host name
          <input
            value={draft.host_name}
            onChange={(e) => setDraft({ ...draft, host_name: e.target.value })}
            className="w-full border p-1"
          />
        </label>
        <label>
          Host bio
          <input
            value={draft.host_bio_short}
            onChange={(e) =>
              setDraft({ ...draft, host_bio_short: e.target.value })
            }
            className="w-full border p-1"
          />
        </label>
        <label>
          Scheduled (ISO)
          <input
            value={draft.scheduled_at}
            onChange={(e) =>
              setDraft({ ...draft, scheduled_at: e.target.value })
            }
            placeholder="2026-06-15T18:00:00+05:30"
            className="w-full border p-1"
          />
        </label>
        <label>
          Duration (min)
          <input
            type="number"
            value={draft.duration_min}
            onChange={(e) =>
              setDraft({ ...draft, duration_min: +e.target.value })
            }
            className="w-full border p-1"
          />
        </label>
        <label className="col-span-2">
          Meeting URL
          <input
            value={draft.meeting_url}
            onChange={(e) =>
              setDraft({ ...draft, meeting_url: e.target.value })
            }
            className="w-full border p-1"
          />
        </label>
        {err && (
          <div className="col-span-2 text-rose-600 text-xs">{err}</div>
        )}
        <div className="col-span-2">
          <button
            type="button"
            onClick={create}
            disabled={saving}
            className="bg-indigo-600 text-white rounded px-4 py-2 text-sm disabled:bg-indigo-300"
          >
            {saving ? "Saving…" : "Schedule session"}
          </button>
        </div>
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500">
            <th>Week</th>
            <th>Title</th>
            <th>When</th>
            <th>RSVPs</th>
            <th>Recording</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((s) => (
            <tr key={s.session_id} className="border-t">
              <td>W{s.week}</td>
              <td>
                {s.title}
                <div className="text-xs text-slate-500">{s.host_name}</div>
              </td>
              <td>{new Date(s.scheduled_at).toLocaleString()}</td>
              <td>{(s.rsvps || []).length}</td>
              <td>
                <input
                  defaultValue={s.recording_url || ""}
                  onBlur={(e) => setRecording(s.session_id, e.target.value)}
                  placeholder="paste URL"
                  className="w-full border p-1"
                />
              </td>
              <td>
                <button
                  type="button"
                  onClick={() => remove(s.session_id)}
                  className="text-rose-600 text-xs"
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
