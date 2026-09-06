/**
 * Teacher/cohort-membership API client (student-facing calls used by
 * HomePage.jsx). Routes confirmed in backend/app.py:
 *   GET  /api/student/weekly-challenge -> { challenge } (per current cohort)
 *   GET  /api/student/assignments      -> { assignments: [...] }
 *   POST /api/cohorts/join             body: { join_code } -> { ok, cohort_name, cohort_id }
 */
import apiClient from './client';

export const getWeeklyChallenge = async () => {
  const res = await apiClient.get('/api/student/weekly-challenge');
  return res.data;
};

export const getStudentAssignments = async () => {
  const res = await apiClient.get('/api/student/assignments');
  return res.data;
};

export const joinCohortByCode = async (code) => {
  const res = await apiClient.post('/api/cohorts/join', { join_code: code });
  return res.data;
};
