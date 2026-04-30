/**
 * Games API - All game-related endpoints
 */

import apiClient from './client';

/**
 * Get list of all available games
 */
export const listGames = async () => {
  const response = await apiClient.get('/api/games');
  return response.data;
};

/**
 * Start a new game
 * @param {string} gameId - Game ID to start
 * @param {object} playerMetadata - Optional player metadata
 */
export const startGame = async (gameId, playerMetadata = {}, options = {}) => {
  const response = await apiClient.post('/api/run/start', {
    game_id: gameId,
    player_metadata: playerMetadata,
    coach_mode: options.coach_mode || false,
    assess_lock_ip: options.assess_lock_ip || false,
  });
  return response.data;
};

/**
 * Submit a choice (also advances to next round)
 * @param {string} runId - Current run ID
 * @param {string|string[]} choiceId - Choice ID(s) to submit
 */
export const submitChoice = async (runId, choiceId, metadata = {}) => {
  const response = await apiClient.post(`/api/run/${runId}/choose`, {
    choice_id: choiceId,
    ...metadata,
  });
  return response.data;
};

/**
 * Submit a `mystery_room` action. The backend escape-room engine reads the
 * full request body as the action payload (e.g. { action, target, puzzle_id, ... }),
 * so we POST it directly without wrapping in `choice_id`.
 *
 * @param {string} runId
 * @param {object} actionPayload  e.g. { action: "examine", target: "hotspot:desk" }
 * @returns {Promise<{ state: object, events?: array, climax_unlocked?: boolean }>}
 */
export const submitMysteryAction = async (runId, actionPayload) => {
  const response = await apiClient.post(`/api/run/${runId}/choose`, actionPayload);
  return response.data;
};

/**
 * Fetch the current run state (used by mystery_room renderer to sync after mount).
 */
export const getRunState = async (runId) => {
  const response = await apiClient.get(`/api/run/${runId}/state`);
  return response.data;
};

/**
 * Advance to next round (same as submitChoice for games without explicit choices)
 * @param {string} runId - Current run ID
 */
export const nextRound = async (runId) => {
  // Backend advances rounds on submitChoice; nextRound just re-syncs state.
  const response = await apiClient.get(`/api/run/${runId}/state`);
  return response.data;
};

/**
 * End game and get final report
 * @param {string} runId - Run ID to end
 * @param {string|null} batchId - Optional HR assessment batch ID (appended as ?b=)
 */
export const endGame = async (runId, batchId = null) => {
  const url = batchId
    ? `/api/run/${runId}/report?b=${encodeURIComponent(batchId)}`
    : `/api/run/${runId}/report`;
  const response = await apiClient.get(url);
  return response.data;
};

/**
 * Get report cards (parent + teacher)
 * @param {string} runId - Run ID
 */
export const getReportCards = async (runId) => {
  const response = await apiClient.get(`/api/run/${runId}/report-cards`);
  return response.data;
};

/**
 * List saved (in-progress) games that can be resumed
 */
export const listSavedGames = async () => {
  const response = await apiClient.get('/api/saves');
  return response.data;
};

/**
 * Resume a saved game
 * @param {string} runId - Run ID to resume
 */
export const resumeGame = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/resume`);
  return response.data;
};

/**
 * Get leaderboard
 * @param {string} gameId - Optional game ID to filter
 */
export const getLeaderboard = async (gameId = null) => {
  const params = gameId ? { game_id: gameId } : {};
  const response = await apiClient.get('/api/leaderboard', { params });
  return response.data;
};

/**
 * Rate a completed game
 */
export const rateGame = async (runId, rating, feedback = '') => {
  const response = await apiClient.post(`/api/run/${runId}/rate`, { rating, feedback });
  return response.data;
};

/**
 * Generate a post-game quiz
 */
export const generateQuiz = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/generate-quiz`);
  return response.data;
};

/**
 * Submit quiz answers
 */
export const submitQuiz = async (runId, answers, questions) => {
  const response = await apiClient.post(`/api/run/${runId}/submit-quiz`, { answers, questions });
  return response.data;
};

/**
 * Get certificate HTML for a completed game
 */
export const getCertificate = async (runId) => {
  const response = await apiClient.get(`/api/run/${runId}/certificate`, {
    responseType: 'text',
  });
  return response.data;
};

/**
 * Get daily challenge recommendations
 */
export const getDailyChallenge = async () => {
  const response = await apiClient.get('/api/daily-challenge');
  return response.data;
};

// ── AI Arena API functions ──

/**
 * Submit a story intro choice (AI Arena)
 * @param {string} runId - Current run ID
 * @param {string} sceneId - Scene ID
 * @param {string} choiceId - Choice ID within the scene
 */
export const submitStoryChoice = async (runId, sceneId, choiceId) => {
  const response = await apiClient.post(`/api/run/${runId}/story-choice`, {
    scene_id: sceneId,
    choice_id: choiceId,
  });
  return response.data;
};

/**
 * Send a message to an AI Arena NPC
 * @param {string} runId - Current run ID
 * @param {string} npcId - NPC ID
 * @param {string} message - Player message
 * @param {Array} history - Chat history
 */
export const sendArenaNPCChat = async (runId, npcId, message, history = []) => {
  const response = await apiClient.post(`/api/run/${runId}/arena-npc-chat`, {
    npc_id: npcId,
    message,
    history,
  });
  return response.data;
};

/**
 * Get competitor chat reaction (AI Arena)
 * @param {string} runId - Current run ID
 * @param {string} competitorId - Competitor ID
 * @param {object} playerChoice - The choice the player just made
 * @param {string} roundTitle - Current round title
 */
export const getCompetitorChat = async (runId, competitorId, playerChoice, roundTitle) => {
  const response = await apiClient.post(`/api/run/${runId}/competitor-chat`, {
    competitor_id: competitorId,
    player_choice: playerChoice,
    round_title: roundTitle,
  });
  return response.data;
};

/**
 * Batch generate DALL-E images for AI Arena game scenes (admin only)
 * @param {string} gameId - Game ID to generate images for
 */
export const batchGenerateImages = async (gameId) => {
  const response = await apiClient.post('/api/admin/ai-arena/generate-images', {
    game_id: gameId,
  });
  return response.data;
};

/**
 * Submit a choice during a crisis event
 * @param {string} runId - Current run ID
 * @param {string} crisisId - Crisis event ID
 * @param {string} choiceId - Selected choice ID
 */
export const submitCrisisChoice = async (runId, crisisId, choiceId) => {
  const response = await apiClient.post(`/api/run/${runId}/crisis-choice`, {
    crisis_id: crisisId,
    choice_id: choiceId,
  });
  return response.data;
};

/**
 * Notify backend that a timed round expired
 * @param {string} runId - Current run ID
 * @param {string} roundId - Round ID that timed out
 */
export const submitTimerExpire = async (runId, roundId) => {
  const response = await apiClient.post(`/api/run/${runId}/timer-expire`, {
    round_id: roundId,
  });
  return response.data;
};

// ── Story Branching API ──

/**
 * Submit a choice in a story_branching game
 * @param {string} runId - Current run ID
 * @param {string} sceneId - Current scene ID
 * @param {string} choiceId - Selected choice ID
 */
export const submitBranchingChoice = async (runId, sceneId, choiceId) => {
  const response = await apiClient.post(`/api/run/${runId}/branching-choice`, {
    scene_id: sceneId,
    choice_id: choiceId,
  });
  return response.data;
};

/**
 * Live-LLM "challenge me on this" beat for a story_branching scene.
 * @param {string} runId
 * @param {string} sceneId
 * @param {string} choiceId
 * @param {string} userReply - optional player reply for follow-up turn
 * @param {Array<{role:string, content:string}>} history - prior turns
 */
export const submitStoryChallenge = async (runId, sceneId, choiceId, userReply = '', history = []) => {
  const response = await apiClient.post(`/api/run/${runId}/story-challenge`, {
    scene_id: sceneId,
    choice_id: choiceId,
    user_reply: userReply,
    history,
  });
  return response.data;
};

/**
 * R1 — Live investor reaction (Series A and other simulation rounds with `live_investor`).
 */
export const submitInvestorReact = async (runId, roundId, choiceId, userMessage = '', history = []) => {
  const response = await apiClient.post(`/api/run/${runId}/investor-react`, {
    round_id: roundId,
    choice_id: choiceId,
    user_message: userMessage,
    history,
  });
  return response.data;
};

/**
 * R4 — Contrarian dissent juror (Ethics Tribunal and similar rounds with `dissent_juror`).
 */
export const submitDissentJuror = async (runId, roundId, choiceId, userReply = '', history = []) => {
  const response = await apiClient.post(`/api/run/${runId}/dissent-juror`, {
    round_id: roundId,
    choice_id: choiceId,
    user_reply: userReply,
    history,
  });
  return response.data;
};

/**
 * R18 — "Mento explains" contextual coach. Used by the per-round popover
 * that lets the player ask "why does this matter?" or "what did the expert do?"
 * without revealing the right answer.
 */
export const submitMentoExplain = async (runId, roundId, question = '', kind = 'free', history = []) => {
  const response = await apiClient.post(`/api/run/${runId}/explain`, {
    round_id: roundId,
    question,
    kind,
    history,
  });
  return response.data;
};

/**
 * R12 — Live boardroom debate. Calls the backend /boardroom-debate endpoint
 * which wraps debate_ai_response with a per-round persona pulled from the
 * round's `live_debate` config.
 */
export const submitBoardroomDebate = async (runId, roundId, studentArgument = '', history = []) => {
  const response = await apiClient.post(`/api/run/${runId}/boardroom-debate`, {
    round_id: roundId,
    student_argument: studentArgument,
    history,
  });
  return response.data;
};

/**
 * R13 — Launch a PvP live session from inside a single-player run.
 * mode: "create" | "join" | "random"
 */
export const launchPvpSession = async (runId, roundId, mode = 'create', { sessionId = '', role = '' } = {}) => {
  const response = await apiClient.post(`/api/run/${runId}/pvp/launch`, {
    round_id: roundId,
    mode,
    session_id: sessionId,
    role,
  });
  return response.data;
};

// Chess Strategy (Founder's Gambit) API

export const chessInit = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/chess/init`);
  return response.data;
};

export const chessMove = async (runId, pieceId, target) => {
  const response = await apiClient.post(`/api/run/${runId}/chess/move`, {
    piece_id: pieceId,
    target,
  });
  return response.data;
};

export const chessAbility = async (runId, pieceId, abilityId = null, target = null) => {
  const response = await apiClient.post(`/api/run/${runId}/chess/ability`, {
    piece_id: pieceId,
    ability_id: abilityId,
    target,
  });
  return response.data;
};

export const chessEndTurn = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/chess/end-turn`);
  return response.data;
};

export const chessValidMoves = async (runId, pieceId) => {
  const response = await apiClient.post(`/api/run/${runId}/chess/valid-moves`, {
    piece_id: pieceId,
  });
  return response.data;
};

export const chessComplete = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/chess/complete`);
  return response.data;
};

// GO Territory API
export const goInit = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/go/init`);
  return response.data;
};
export const goPlace = async (runId, position) => {
  const response = await apiClient.post(`/api/run/${runId}/go/place`, { position });
  return response.data;
};
export const goPass = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/go/pass`);
  return response.data;
};
export const goScore = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/go/score`);
  return response.data;
};
export const goComplete = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/go/complete`);
  return response.data;
};

// Reversi API
export const reversiInit = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/reversi/init`);
  return response.data;
};
export const reversiPlace = async (runId, position) => {
  const response = await apiClient.post(`/api/run/${runId}/reversi/place`, { position });
  return response.data;
};
export const reversiValidMoves = async (runId) => {
  const response = await apiClient.get(`/api/run/${runId}/reversi/valid-moves`);
  return response.data;
};
export const reversiComplete = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/reversi/complete`);
  return response.data;
};

// Tower Defense API
export const tdInit = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/towerdefense/init`);
  return response.data;
};
export const tdPlace = async (runId, towerType, position) => {
  const response = await apiClient.post(`/api/run/${runId}/towerdefense/place`, { tower_type: towerType, position });
  return response.data;
};
export const tdUpgrade = async (runId, towerId) => {
  const response = await apiClient.post(`/api/run/${runId}/towerdefense/upgrade`, { tower_id: towerId });
  return response.data;
};
export const tdWave = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/towerdefense/wave`);
  return response.data;
};
export const tdTick = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/towerdefense/tick`);
  return response.data;
};
export const tdComplete = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/towerdefense/complete`);
  return response.data;
};

// Puzzle Match API
export const puzzleInit = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/puzzle/init`);
  return response.data;
};
export const puzzleSwap = async (runId, pos1, pos2) => {
  const response = await apiClient.post(`/api/run/${runId}/puzzle/swap`, { pos1, pos2 });
  return response.data;
};
export const puzzleHint = async (runId) => {
  const response = await apiClient.get(`/api/run/${runId}/puzzle/hint`);
  return response.data;
};
export const puzzleComplete = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/puzzle/complete`);
  return response.data;
};

// ─── Adaptive Game System ───────────────────────────────────────────────

/** Get the player's play style analysis */
export const getPlayStyle = async () => {
  const response = await apiClient.get('/api/adaptive/play-style');
  return response.data;
};

/** Get personalized game recommendations */
export const getRecommendations = async (count = 5) => {
  const response = await apiClient.get(`/api/adaptive/recommend?count=${count}`);
  return response.data;
};

/** Get difficulty suggestion for a specific game */
export const getDifficultySuggestion = async (gameId) => {
  const response = await apiClient.get(`/api/adaptive/difficulty/${gameId}`);
  return response.data;
};

/** Get a tailored game variant */
export const getGameVariant = async (gameId) => {
  const response = await apiClient.get(`/api/adaptive/variant/${gameId}`);
  return response.data;
};

/** Track engagement metrics for a completed game */
export const trackEngagement = async (runId) => {
  const response = await apiClient.get(`/api/adaptive/engagement/${runId}`);
  return response.data;
};

// Strategy Grid API
export const sgInit = async (runId, { difficulty, players } = {}) => {
  const body = { difficulty };
  if (players) body.players = players;
  const response = await apiClient.post(`/api/run/${runId}/strategygrid/init`, body);
  return response.data;
};
export const sgValidMoves = async (runId, pieceId) => {
  const response = await apiClient.post(`/api/run/${runId}/strategygrid/valid-moves`, { piece_id: pieceId });
  return response.data;
};
export const sgMove = async (runId, pieceId, position) => {
  const response = await apiClient.post(`/api/run/${runId}/strategygrid/move`, { piece_id: pieceId, position });
  return response.data;
};
export const sgAbility = async (runId, pieceId, targetPos) => {
  const response = await apiClient.post(`/api/run/${runId}/strategygrid/ability`, { piece_id: pieceId, target_pos: targetPos });
  return response.data;
};
export const sgComplete = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/strategygrid/complete`);
  return response.data;
};

// Civ mode endpoints
export const sgBuild = async (runId, typeId, position) => {
  const response = await apiClient.post(`/api/run/${runId}/strategygrid/build`, { type_id: typeId, position });
  return response.data;
};

export const sgResearch = async (runId, techId) => {
  const response = await apiClient.post(`/api/run/${runId}/strategygrid/research`, { tech_id: techId });
  return response.data;
};

export const sgSpawn = async (runId, typeId, position) => {
  const response = await apiClient.post(`/api/run/${runId}/strategygrid/spawn`, { type_id: typeId, position });
  return response.data;
};

export const sgEndTurn = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/strategygrid/end-turn`);
  return response.data;
};

// Board Game Learning Pipeline
export const boardLogChoice = async (runId, choiceData) => {
  const response = await apiClient.post(`/api/run/${runId}/board/log-choice`, choiceData);
  return response.data;
};

export const boardComplete = async (runId, completionData) => {
  const response = await apiClient.post(`/api/run/${runId}/board/complete`, completionData);
  return response.data;
};

export const boardGenerateTileStory = async (runId, tileData) => {
  const response = await apiClient.post(`/api/run/${runId}/board/generate-tile-story`, tileData);
  return response.data;
};

// Minigame completion — records score + computes dimension scores on backend
export const minigameComplete = async (runId, completionData) => {
  const response = await apiClient.post(`/api/run/${runId}/minigame/complete`, completionData);
  return response.data;
};

// ── Round 11: MCP-Style Agent API ──────────────────────────────────────────────

/** Get competency assessment report for a completed run */
export const getAssessmentReport = async (runId) => {
  const response = await apiClient.get(`/api/run/${runId}/assessment`);
  return response.data;
};

/** Get LLM-generated market/news events for finance/negotiation games */
export const getMarketEvents = async (runId) => {
  const response = await apiClient.get(`/api/run/${runId}/market-events`);
  return response.data;
};

/** Generate a dynamic round when standard rounds are exhausted */
export const generateRound = async (runId) => {
  const response = await apiClient.post(`/api/run/${runId}/generate-round`);
  return response.data;
};

/**
 * Upload a drawing PNG from the canvas widget
 * @param {string} runId - Current run ID
 * @param {object} data - { image_base64, round_id, stroke_count, tools_used, time_spent_seconds }
 */
export const uploadDrawing = async (runId, data) => {
  const response = await apiClient.post(`/api/run/${runId}/upload-drawing`, data);
  return response.data;
};
