/**
 * GameTypeRouter - Routes to the appropriate game renderer based on game_type.
 * Note: Board3DRenderer (react-three-fiber) is disabled — all board games use
 * the 2D BoardGameRenderer to avoid multiple-React-instance crashes (R3F bundles
 * its own React copy which conflicts with the app's react-vendor chunk).
 */
import React, { Suspense } from 'react';
import { LoadingState } from '../ui/LoadingSpinner';
import ErrorBoundary from '../ui/ErrorBoundary';

const BoardGameRenderer = React.lazy(() => import('./renderers/BoardGameRenderer'));
const SummitLeadersRenderer = React.lazy(() => import('./renderers/SummitLeadersRenderer'));
const MiniGameRenderer = React.lazy(() => import('./renderers/MiniGameRenderer'));
const CardGameRenderer = React.lazy(() => import('./renderers/CardGameRenderer'));
const StrategyGameRenderer = React.lazy(() => import('./renderers/StrategyGameRenderer'));
const AIArenaRenderer = React.lazy(() => import('./renderers/AIArenaRenderer'));
const StoryBranchingRenderer = React.lazy(() => import('./renderers/StoryBranchingRenderer'));
const FoundersGambitRenderer = React.lazy(() => import('./renderers/FoundersGambitRenderer'));
const GoTerritoryRenderer = React.lazy(() => import('./renderers/GoTerritoryRenderer'));
const ReversiRenderer = React.lazy(() => import('./renderers/ReversiRenderer'));
const TowerDefenseRenderer = React.lazy(() => import('./renderers/TowerDefenseRenderer'));
const PuzzleMatchRenderer = React.lazy(() => import('./renderers/PuzzleMatchRenderer'));
const StrategyGridRenderer = React.lazy(() => import('./renderers/StrategyGridRenderer'));
const CardBoardRenderer = React.lazy(() => import('./renderers/CardBoardRenderer'));
const TrumpCardRenderer = React.lazy(() => import('./renderers/TrumpCardRenderer'));
const SimulationRenderer = React.lazy(() => import('./renderers/SimulationRenderer'));
const MysteryRoomRenderer = React.lazy(() => import('./renderers/MysteryRoomRenderer'));
const MusicGameRenderer = React.lazy(() => import('./renderers/MusicGameRenderer'));
const TitrationLabRenderer = React.lazy(() => import('./renderers/TitrationLabRenderer'));

const KNOWN_TYPES = new Set([
  'rounds', 'board', 'minigame', 'card', 'strategy', 'story_branching', 'ai_arena',
  'chess_strategy', 'go_territory', 'reversi', 'tower_defense', 'puzzle_match', 'strategy_grid',
  'card_board', 'trump_card', 'simulation', 'mystery_room',
  'music_match', 'lab_titration',
]);

const UnknownGameType = ({ type, onBack }) => (
  <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-8">
    <div className="text-6xl mb-4">🎮</div>
    <h2 className="text-2xl font-bold text-gray-800 mb-2">Game Type Not Supported</h2>
    <p className="text-gray-500 mb-6">
      This game uses a "{type}" renderer which isn't available yet.
    </p>
    <button
      onClick={onBack}
      className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors"
    >
      Back to Games
    </button>
  </div>
);

const GameTypeRouter = ({ gameType, currentGame, gameState, runId, onGameEnd, onBack, defaultAiMode = false, playerProfile = null }) => {
  const type = gameType || currentGame?.game_type || 'rounds';

  if (type === 'rounds') return null;

  // Unknown game type fallback
  if (!KNOWN_TYPES.has(type)) {
    return <UnknownGameType type={type} onBack={onBack} />;
  }

  // Check if board game requests a specific renderer (3D disabled — use 2D always)
  const boardRenderer = type === 'board' ? currentGame?.board_config?.renderer : null;
  const isSummitLeaders = boardRenderer === 'summit_leaders';

  const commonProps = { gameData: currentGame, gameState, runId, onComplete: onGameEnd, onBack, playerProfile };

  return (
    <ErrorBoundary variant="gameplay">
      <Suspense fallback={<LoadingState message="Loading game..." />}>
        {type === 'board' && isSummitLeaders && <SummitLeadersRenderer {...commonProps} />}
        {type === 'board' && !isSummitLeaders && <BoardGameRenderer {...commonProps} />}
        {type === 'minigame' && <MiniGameRenderer {...commonProps} />}
        {type === 'card' && <CardGameRenderer {...commonProps} />}
        {type === 'strategy' && <StrategyGameRenderer {...commonProps} />}
        {type === 'story_branching' && <StoryBranchingRenderer {...commonProps} defaultAiMode={defaultAiMode} />}
        {type === 'ai_arena' && <AIArenaRenderer {...commonProps} />}
        {type === 'chess_strategy' && <FoundersGambitRenderer {...commonProps} />}
        {type === 'go_territory' && <GoTerritoryRenderer {...commonProps} />}
        {type === 'reversi' && <ReversiRenderer {...commonProps} />}
        {type === 'tower_defense' && <TowerDefenseRenderer {...commonProps} />}
        {type === 'puzzle_match' && <PuzzleMatchRenderer {...commonProps} />}
        {type === 'strategy_grid' && <StrategyGridRenderer {...commonProps} />}
        {type === 'card_board' && <CardBoardRenderer {...commonProps} />}
        {type === 'trump_card' && <TrumpCardRenderer {...commonProps} />}
        {type === 'simulation' && <SimulationRenderer {...commonProps} />}
        {type === 'mystery_room' && <MysteryRoomRenderer {...commonProps} />}
        {type === 'music_match' && (
          <MusicGameRenderer game={currentGame} runId={runId} onComplete={onGameEnd} />
        )}
        {type === 'lab_titration' && (
          <TitrationLabRenderer game={currentGame} onComplete={onGameEnd} />
        )}
      </Suspense>
    </ErrorBoundary>
  );
};

export default GameTypeRouter;
