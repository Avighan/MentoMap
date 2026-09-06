/**
 * Curriculum/schedule API client (student-facing). Route confirmed in
 * backend/app.py `student_get_schedule`:
 *   GET /api/student/schedule -> { schedule: [...], summary: {...} }
 */
import apiClient from './client';

export const getStudentSchedule = async () => {
  const res = await apiClient.get('/api/student/schedule');
  return res.data;
};
