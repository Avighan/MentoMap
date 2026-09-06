/**
 * Wallet (in-game coin economy) API client. Routes confirmed in
 * backend/app.py / backend/wallet.py:
 *   GET  /api/wallet                 -> wallet record
 *   GET  /api/wallet/history?limit=  -> { transactions: [...] }
 *   POST /api/wallet/spend           body: { amount, purpose } -> wallet record or { error }
 *   GET  /api/leaderboard/global?limit= -> global lifetime-coins leaderboard
 */
import apiClient from './client';

export const getWallet = async () => {
  const res = await apiClient.get('/api/wallet');
  return res.data;
};

export const getWalletHistory = async (limit = 50) => {
  const res = await apiClient.get('/api/wallet/history', { params: { limit } });
  return res.data;
};

export const spendWallet = async (amount, purpose = '') => {
  const res = await apiClient.post('/api/wallet/spend', { amount, purpose });
  return res.data;
};

export const getGlobalLeaderboard = async (limit = 20) => {
  const res = await apiClient.get('/api/leaderboard/global', { params: { limit } });
  return res.data;
};
