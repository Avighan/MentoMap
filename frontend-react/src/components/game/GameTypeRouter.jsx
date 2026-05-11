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
const PendulumLabRenderer = React.lazy(() => import('./renderers/PendulumLabRenderer'));
const OpticsLabRenderer = React.lazy(() => import('./renderers/OpticsLabRenderer'));
const CircuitDebuggerRenderer = React.lazy(() => import('./renderers/CircuitDebuggerRenderer'));
const GeneticsCrossRenderer = React.lazy(() => import('./renderers/GeneticsCrossRenderer'));
const StoichiometryMixerRenderer = React.lazy(() => import('./renderers/StoichiometryMixerRenderer'));
const MentalMathRenderer = React.lazy(() => import('./renderers/MentalMathRenderer'));
const TypingDrillRenderer = React.lazy(() => import('./renderers/TypingDrillRenderer'));
const BoggleRenderer = React.lazy(() => import('./renderers/BoggleRenderer'));
const MockInterviewRenderer = React.lazy(() => import('./renderers/MockInterviewRenderer'));
const SudokuRenderer = React.lazy(() => import('./renderers/SudokuRenderer'));
const LogicGridRenderer = React.lazy(() => import('./renderers/LogicGridRenderer'));
const GeometryConstructorRenderer = React.lazy(() => import('./renderers/GeometryConstructorRenderer'));

const KNOWN_TYPES = new Set([
  'rounds', 'board', 'minigame', 'card', 'strategy', 'story_branching', 'ai_arena',
  'chess_strategy', 'go_territory', 'reversi', 'tower_defense', 'puzzle_match', 'strategy_grid',
  'card_board', 'trump_card', 'simulation', 'mystery_room',
  'music_match', 'lab_titration',
  // Audit-followup grader types (12)
  'pendulum_lab', 'optics_lab', 'circuit_debugger', 'genetics_cross', 'stoichiometry_mixer',
  'mental_math', 'typing_drill', 'boggle', 'mock_interview',
  'sudoku', 'logic_grid', 'geometry_constructor',
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
          <TitrationLabRenderer game={currentGame} runId={runId} onComplete={onGameEnd} />
        )}
        {type === 'pendulum_lab' && <PendulumLabRenderer {...commonProps} game={currentGame} />}
        {type === 'optics_lab' && <OpticsLabRenderer {...commonProps} game={currentGame} />}
        {type === 'circuit_debugger' && <CircuitDebuggerRenderer {...commonProps} game={currentGame} />}
        {type === 'genetics_cross' && <GeneticsCrossRenderer {...commonProps} game={currentGame} />}
        {type === 'stoichiometry_mixer' && <StoichiometryMixerRenderer {...commonProps} game={currentGame} />}
        {type === 'mental_math' && <MentalMathRenderer {...commonProps} game={currentGame} />}
        {type === 'typing_drill' && <TypingDrillRenderer {...commonProps} game={currentGame} />}
        {type === 'boggle' && <BoggleRenderer {...commonProps} game={currentGame} />}
        {type === 'mock_interview' && <MockInterviewRenderer {...commonProps} game={currentGame} />}
        {type === 'sudoku' && <SudokuRenderer {...commonProps} game={currentGame} />}
        {type === 'logic_grid' && <LogicGridRenderer {...commonProps} game={currentGame} />}
        {type === 'geometry_constructor' && <GeometryConstructorRenderer {...commonProps} game={currentGame} />}
      </Suspense>
    </ErrorBoundary>
  );
};

export default GameTypeRouter;
