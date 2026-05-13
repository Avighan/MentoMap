/**
 * Modules API client — multi-week guided learning courses
 * (e.g. Mento Entrepreneurship Workshop)
 */
import apiClient from './client';

// ---------- Catalogue + content ----------

export const listModules = async (grade) => {
  const params = grade ? { grade } : {};
  const res = await apiClient.get('/api/modules', { params });
  return res.data;
};

export const getModule = async (moduleId) => {
  const res = await apiClient.get(`/api/modules/${moduleId}`);
  return res.data;
};

// ---------- Per-user progress ----------

export const startModule = async (moduleId) => {
  const res = await apiClient.post(`/api/modules/${moduleId}/start`);
  return res.data;
};

export const getModuleProgress = async (moduleId) => {
  const res = await apiClient.get(`/api/modules/${moduleId}/progress`);
  return res.data;
};

export const saveLesson = async (moduleId, lessonId, answers) => {
  const res = await apiClient.post(
    `/api/modules/${moduleId}/lessons/${lessonId}/save`,
    { answers }
  );
  return res.data;
};

export const completeLesson = async (moduleId, lessonId, payload = {}) => {
  const res = await apiClient.post(
    `/api/modules/${moduleId}/lessons/${lessonId}/complete`,
    payload
  );
  return res.data;
};

export const listMyModules = async () => {
  const res = await apiClient.get('/api/modules/mine');
  return res.data;
};

export const getModuleReport = async (moduleId) => {
  const res = await apiClient.get(`/api/modules/${moduleId}/report`);
  return res.data;
};

/**
 * Module composite v2 (P0 Task 13/21) — lighter, 5-channel composite report
 * with per-dimension delta. See backend/modules_engine.compute_module_composite_v2.
 */
export const getModuleReportV2 = async (moduleId) => {
  const res = await apiClient.get(`/api/modules/${moduleId}/report-v2`);
  return res.data;
};

// Teacher: per-cohort answer review
export const getCohortModuleAnswers = async (cohortId, moduleId) => {
  const res = await apiClient.get(
    `/api/cohorts/${cohortId}/modules/${moduleId}/answers`
  );
  return res.data;
};

// ---------- Field mission (offline human-research lesson type) ----------

export const getFieldMission = async (moduleId, lessonId) => {
  const res = await apiClient.get(
    `/api/modules/${moduleId}/lessons/${lessonId}/field-mission`
  );
  return res.data;
};

export const addFieldMissionEntry = async (moduleId, lessonId, entry) => {
  const res = await apiClient.post(
    `/api/modules/${moduleId}/lessons/${lessonId}/field-mission/entry`,
    entry
  );
  return res.data;
};

export const deleteFieldMissionEntry = async (moduleId, lessonId, entryId) => {
  const res = await apiClient.delete(
    `/api/modules/${moduleId}/lessons/${lessonId}/field-mission/entry/${entryId}`
  );
  return res.data;
};

export const getAllFieldMissionEntries = async (moduleId) => {
  const res = await apiClient.get(
    `/api/modules/${moduleId}/field-mission-entries`
  );
  return res.data;
};

// ---------- Voice-recording lesson type (public speaking) ----------

export const submitVoiceLesson = async (moduleId, lessonId, payload) => {
  const res = await apiClient.post(
    `/api/modules/${moduleId}/lessons/${lessonId}/voice-submit`,
    payload
  );
  return res.data;
};

// ---------- Cohort / multi-user (teacher views) ----------

export const assignModuleToCohort = async (cohortId, moduleId, opts = {}) => {
  const res = await apiClient.post(`/api/cohorts/${cohortId}/modules`, {
    module_id: moduleId,
    start_date: opts.startDate || null,
    due_date: opts.dueDate || null,
  });
  return res.data;
};

export const unassignModuleFromCohort = async (cohortId, moduleId) => {
  const res = await apiClient.delete(`/api/cohorts/${cohortId}/modules/${moduleId}`);
  return res.data;
};

export const listCohortModules = async (cohortId) => {
  const res = await apiClient.get(`/api/cohorts/${cohortId}/modules`);
  return res.data;
};

export const getCohortModuleProgress = async (cohortId, moduleId) => {
  const res = await apiClient.get(
    `/api/cohorts/${cohortId}/modules/${moduleId}/progress`
  );
  return res.data;
};

export const listMyCohortAssignedModules = async () => {
  const res = await apiClient.get('/api/modules/cohort-assigned');
  return res.data;
};

// ---------- Pitch Coach (Phase B) ----------

export const submitPitchCoach = async (moduleId, lessonId, blob) => {
  const fd = new FormData();
  fd.append('audio', blob, 'pitch.webm');
  try {
    const res = await apiClient.post(
      `/api/modules/${moduleId}/lessons/${lessonId}/pitch-coach`,
      fd,
    );
    return res.data;
  } catch (err) {
    if (err?.response?.status === 429) {
      const e = new Error('cap_reached');
      e.code = 'cap_reached';
      throw e;
    }
    throw err;
  }
};

// ---------- Interview Sim (Phase B) ----------

export const listInterviewPersonas = async (moduleId, lessonId) => {
  const res = await apiClient.get(
    `/api/modules/${moduleId}/lessons/${lessonId}/interview-sim/personas`,
  );
  return res.data;
};

export const startInterview = async (moduleId, lessonId, personaId) => {
  try {
    const res = await apiClient.post(
      `/api/modules/${moduleId}/lessons/${lessonId}/interview-sim/start`,
      { persona_id: personaId },
    );
    return res.data;
  } catch (err) {
    if (err?.response?.status === 429) {
      const e = new Error('cap_reached');
      e.code = 'cap_reached';
      throw e;
    }
    throw err;
  }
};

export const takeInterviewTurn = async (moduleId, lessonId, convId, blob) => {
  const fd = new FormData();
  fd.append('conv_id', convId);
  fd.append('audio', blob, 'turn.webm');
  try {
    const res = await apiClient.post(
      `/api/modules/${moduleId}/lessons/${lessonId}/interview-sim/turn`,
      fd,
    );
    return res.data;
  } catch (err) {
    if (err?.response?.status === 429) {
      const e = new Error('cap_reached');
      e.code = 'cap_reached';
      throw e;
    }
    throw err;
  }
};

export const endInterview = async (moduleId, lessonId, convId) => {
  const res = await apiClient.post(
    `/api/modules/${moduleId}/lessons/${lessonId}/interview-sim/end`,
    { conv_id: convId },
  );
  return res.data;
};

// ---------- Idea Journal (Phase C) ----------

export const listIdeaJournal = async (moduleId) => {
  const res = await apiClient.get(`/api/modules/${moduleId}/idea-journal`);
  return res.data;
};

export const addIdeaJournalEntry = async (moduleId, payload) => {
  const res = await apiClient.post(
    `/api/modules/${moduleId}/idea-journal`,
    payload,
  );
  return res.data;
};

export const patchIdeaJournalEntry = async (moduleId, entryId, patch) => {
  const res = await apiClient.patch(
    `/api/modules/${moduleId}/idea-journal/${entryId}`,
    patch,
  );
  return res.data;
};

export const ideaJournalExportUrl = (moduleId) =>
  `/api/modules/${moduleId}/idea-journal/export`;

// ---------- Phase C: skill report + share card + certificate ----------

export const getModuleSkillReport = async (moduleId) => {
  const res = await apiClient.get(`/api/modules/${moduleId}/skill-report`);
  return res.data;
};

export const moduleShareCardUrl = (moduleId) =>
  `/api/modules/${moduleId}/skill-report/card.png`;

export const getModuleCertificate = async (moduleId) => {
  const res = await apiClient.get(`/api/modules/${moduleId}/certificate`);
  return res.data;
};

export const moduleCertificateUrl = (moduleId) =>
  `/api/modules/${moduleId}/certificate`;

// ---------- Phase C: cohort live sessions ----------

export const listCohortLiveSessions = async (cohortId, moduleId) => {
  const res = await apiClient.get(
    `/api/cohorts/${cohortId}/modules/${moduleId}/live-sessions`,
  );
  return res.data;
};

export const createCohortLiveSession = async (cohortId, moduleId, payload) => {
  const res = await apiClient.post(
    `/api/cohorts/${cohortId}/modules/${moduleId}/live-sessions`,
    payload,
  );
  return res.data;
};

export const updateCohortLiveSession = async (cohortId, moduleId, sessionId, patch) => {
  const res = await apiClient.patch(
    `/api/cohorts/${cohortId}/modules/${moduleId}/live-sessions/${sessionId}`,
    patch,
  );
  return res.data;
};

export const deleteCohortLiveSession = async (cohortId, moduleId, sessionId) => {
  const res = await apiClient.delete(
    `/api/cohorts/${cohortId}/modules/${moduleId}/live-sessions/${sessionId}`,
  );
  return res.data;
};

export const rsvpCohortLiveSession = async (cohortId, moduleId, sessionId, attending) => {
  const res = await apiClient.post(
    `/api/cohorts/${cohortId}/modules/${moduleId}/live-sessions/${sessionId}/rsvp`,
    { attending },
  );
  return res.data;
};
