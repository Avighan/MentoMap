/**
 * Shared helper used by the 12 audit-followup grader renderers.
 *
 * Each renderer (PendulumLabRenderer, OpticsLabRenderer, etc.) computes the
 * student's submission entirely client-side, then calls submitGrader to
 * POST it to the matching backend endpoint. Backend re-derives the
 * authoritative answer from the JSON config and returns the real score —
 * this client-side path is just for collecting observations.
 *
 * @param {string} runId        - the run id from props (may be null)
 * @param {string} endpointSlug - e.g. "pendulum-lab", "boggle"
 * @param {object} payload      - body keys/values the route expects
 * @returns {Promise<{ok:boolean, summary?:object, error?:string}>}
 */
export async function submitGrader(runId, endpointSlug, payload) {
  if (!runId) {
    return { ok: false, error: "no_run_id" };
  }
  const token = (typeof localStorage !== "undefined") ? localStorage.getItem("token") : null;
  try {
    const res = await fetch(`/api/run/${runId}/${endpointSlug}/complete`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      return { ok: false, error: `http_${res.status}` };
    }
    const data = await res.json();
    return { ok: true, summary: data?.summary };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}
