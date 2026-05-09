/**
 * stocksim API module — wraps the 5 backend routes for the realtime stock
 * market simulator. All routes require auth; apiClient already attaches the
 * JWT, so callers don't need to pass any auth headers.
 *
 * Routes (backend/app.py, Tasks 10-12):
 *   POST /api/run/<run_id>/stocksim/start
 *   GET  /api/run/<run_id>/stocksim/state
 *   POST /api/run/<run_id>/stocksim/trade
 *   POST /api/run/<run_id>/stocksim/cancel       body: { order_id }
 *   POST /api/run/<run_id>/stocksim/complete
 */

import apiClient from './client';

/**
 * Start (or resume) a stocksim session for the given run.
 * @param {string} runId
 * @param {object} [opts] — optional config overrides forwarded to backend
 * @returns {Promise<object>} initial session state
 */
export async function startStocksim(runId, opts = {}) {
  const res = await apiClient.post(`/api/run/${runId}/stocksim/start`, opts);
  return res.data;
}

/**
 * Fetch current session state (positions, orders, prices, tick, P&L).
 * @param {string} runId
 * @returns {Promise<object>}
 */
export async function getStocksimState(runId) {
  const res = await apiClient.get(`/api/run/${runId}/stocksim/state`);
  return res.data;
}

/**
 * Place a buy/sell order.
 * @param {string} runId
 * @param {object} payload — { symbol, side, qty, order_type, limit_price?, ... }
 * @returns {Promise<object>}
 */
export async function placeStocksimTrade(runId, payload) {
  const res = await apiClient.post(`/api/run/${runId}/stocksim/trade`, payload);
  return res.data;
}

/**
 * Cancel a resting order by id.
 * @param {string} runId
 * @param {string} orderId
 * @returns {Promise<object>}
 */
export async function cancelStocksimOrder(runId, orderId) {
  const res = await apiClient.post(
    `/api/run/${runId}/stocksim/cancel`,
    { order_id: orderId },
  );
  return res.data;
}

/**
 * Mark the session complete and trigger end-of-game scoring.
 * @param {string} runId
 * @returns {Promise<object>}
 */
export async function completeStocksim(runId) {
  const res = await apiClient.post(`/api/run/${runId}/stocksim/complete`);
  return res.data;
}

export default {
  startStocksim,
  getStocksimState,
  placeStocksimTrade,
  cancelStocksimOrder,
  completeStocksim,
};
