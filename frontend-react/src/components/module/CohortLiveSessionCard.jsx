import { useEffect, useState } from "react";
import {
  listCohortLiveSessions,
  rsvpCohortLiveSession,
} from "../../api/modules";

function countdown(targetISO) {
  const ms = new Date(targetISO) - new Date();
  if (ms <= 0) return "Now";
  const days = Math.floor(ms / 86400000);
  const hrs = Math.floor((ms % 86400000) / 3600000);
  const mins = Math.floor((ms % 3600000) / 60000);
  if (days > 0) return `in ${days}d ${hrs}h`;
  if (hrs > 0) return `in ${hrs}h ${mins}m`;
  return `in ${mins}m`;
}

function gcalLink({ title, scheduled_at, duration_min, meeting_url, host_name }) {
  const start = new Date(scheduled_at);
  const end = new Date(start.getTime() + (duration_min || 60) * 60000);
  const fmt = (d) => d.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
  const text = encodeURIComponent(`${title} — Mento Founder Lab`);
  const details = encodeURIComponent(`Host: ${host_name}\nJoin: ${meeting_url}`);
  return `https://calendar.google.com/calendar/r/eventedit?text=${text}&dates=${fmt(start)}/${fmt(end)}&details=${details}`;
}

export default function CohortLiveSessionCard({ cohortId, moduleId, currentUserId, lesson }) {
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    if (!cohortId || !moduleId) return;
    let cancelled = false;
    listCohortLiveSessions(cohortId, moduleId)
      .then((d) => {
        if (!cancelled) setSessions(d?.sessions || []);
      })
      .catch(() => {
        if (!cancelled) setSessions([]);
      });
    return () => {
      cancelled = true;
    };
  }, [cohortId, moduleId]);

  const next = sessions
    .filter(
      (s) =>
        s.status !== "cancelled" &&
        new Date(s.scheduled_at) > new Date(Date.now() - 24 * 3600000),
    )
    .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))[0];

  if (!next) {
    // Lesson-renderer fallback: rendered inline as a lesson without a cohort context.
    if (lesson && !cohortId) {
      return (
        <div className="rounded-xl border-2 border-indigo-200 bg-indigo-50 p-4">
          <div className="text-xs uppercase tracking-wide text-indigo-700">
            Live session
          </div>
          <div className="font-semibold mt-1">
            {lesson.title || "Cohort live session"}
          </div>
          {lesson.summary && (
            <div className="text-sm text-slate-700 mt-1">{lesson.summary}</div>
          )}
          <div className="text-xs text-slate-500 mt-2">
            Join your cohort to RSVP and receive reminders.
          </div>
        </div>
      );
    }
    return null;
  }
  const rsvped = (next.rsvps || []).includes(currentUserId);

  const toggleRsvp = async () => {
    try {
      await rsvpCohortLiveSession(cohortId, moduleId, next.session_id, !rsvped);
      const d = await listCohortLiveSessions(cohortId, moduleId);
      setSessions(d?.sessions || []);
    } catch (e) {
      // Silent — banner just won't update if RSVP fails.
    }
  };

  const joinable = new Date(next.scheduled_at) - new Date() < 10 * 60000;
  return (
    <div className="rounded-xl border-2 border-indigo-300 bg-indigo-50 p-4 flex flex-wrap items-center gap-4">
      <div className="flex-1 min-w-[200px]">
        <div className="text-xs uppercase tracking-wide text-indigo-700">
          Live session · Week {next.week}
        </div>
        <div className="font-semibold mt-1">{next.title}</div>
        <div className="text-sm text-slate-700">
          {next.host_name} · {countdown(next.scheduled_at)}
        </div>
        {next.host_bio_short && (
          <div className="text-xs text-slate-500 mt-1">{next.host_bio_short}</div>
        )}
      </div>
      <div className="flex gap-2 flex-wrap">
        <button
          type="button"
          onClick={toggleRsvp}
          className={(rsvped ? "bg-emerald-600" : "bg-indigo-600") + " text-white rounded px-3 py-2 text-sm"}
        >
          {rsvped ? "✓ I'm in" : "RSVP"}
        </button>
        <a
          href={gcalLink(next)}
          target="_blank"
          rel="noreferrer"
          className="bg-white border rounded px-3 py-2 text-sm"
        >
          📅 Add to Calendar
        </a>
        <a
          href={next.meeting_url}
          target="_blank"
          rel="noreferrer"
          className={(joinable ? "bg-rose-600" : "bg-slate-300 pointer-events-none") + " text-white rounded px-3 py-2 text-sm"}
        >
          Join
        </a>
      </div>
    </div>
  );
}
