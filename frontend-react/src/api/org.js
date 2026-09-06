/**
 * Admin org-management API client — backs OrgsSection.jsx.
 *
 * Routes (backend/admin.py, require_admin — Authorization: Bearer <token>
 * with role=admin; apiClient's interceptor attaches this automatically):
 *   GET    /api/admin/orgs          -> { orgs: [...] }
 *   GET    /api/admin/orgs/<id>     -> org
 *   POST   /api/admin/orgs          -> org, 201
 *   PUT    /api/admin/orgs/<id>     -> org
 *   DELETE /api/admin/orgs/<id>     -> { message }
 */
import apiClient from './client';

export const adminListOrgs = async () => {
  const res = await apiClient.get('/api/admin/orgs');
  return res.data.orgs || [];
};

export const adminGetOrg = async (orgId) => {
  const res = await apiClient.get(`/api/admin/orgs/${orgId}`);
  return res.data;
};

export const adminCreateOrg = async (payload) => {
  const res = await apiClient.post('/api/admin/orgs', payload);
  return res.data;
};

export const adminUpdateOrg = async (orgId, payload) => {
  const res = await apiClient.put(`/api/admin/orgs/${orgId}`, payload);
  return res.data;
};

export const adminDeleteOrg = async (orgId) => {
  const res = await apiClient.delete(`/api/admin/orgs/${orgId}`);
  return res.data;
};
