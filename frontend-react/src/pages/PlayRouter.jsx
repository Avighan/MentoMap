/**
 * PlayRouter — dispatches /play/:gameId to the right play screen.
 *
 * The 3 Phase 1 pilot games (dealcraft, mumbai_manufacturer, heliogrid)
 * have their own bespoke backend engines and use PilotGamePlayPage.
 * story_branching, mystery_room, minigame/stock_market and ai_lab games
 * each have their own backend contracts (chapters+scenes, escape-room
 * hotspots, T+1 trading, prompt grading) and use their own dedicated
 * pages. Every other whitelisted "rounds"-type game runs through the
 * generic engine.py play path and uses AdventureGamePlayPage.
 */
import { useParams } from 'react-router-dom';
import PilotGamePlayPage from './PilotGamePlayPage';
import AdventureGamePlayPage from './AdventureGamePlayPage';
import StoryBranchingPlayPage from './StoryBranchingPlayPage';
import MysteryRoomPlayPage from './MysteryRoomPlayPage';
import StockMarketPlayPage from './StockMarketPlayPage';
import AiLabPlayPage from './AiLabPlayPage';

const PILOT_GAME_IDS = new Set(['dealcraft', 'mumbai_manufacturer', 'heliogrid']);

const STORY_BRANCHING_GAME_IDS = new Set([
  'city-mayor',
  'climate-champions',
  'kids-kindness-quest',
  'kids-share-the-toys',
  'kids-tiny-leader',
  'pro-burnout-recovery',
  'pro-promotion-case',
  'space-explorer-expanded',
  'the-great-bazaar-deal',
  'the-startup-decision',
  'the-street-market-negotiator',
  'the-treaty',
]);

const MYSTERY_ROOM_GAME_IDS = new Set(['the-substitute-teacher']);

const STOCK_MARKET_GAME_IDS = new Set(['stock-market-day-trader', 'stock-market-simulator']);

const AI_LAB_GAME_IDS = new Set(['ai-prompt-lab-school']);

export default function PlayRouter() {
  const { gameId } = useParams();
  if (PILOT_GAME_IDS.has(gameId)) return <PilotGamePlayPage />;
  if (STORY_BRANCHING_GAME_IDS.has(gameId)) return <StoryBranchingPlayPage />;
  if (MYSTERY_ROOM_GAME_IDS.has(gameId)) return <MysteryRoomPlayPage />;
  if (STOCK_MARKET_GAME_IDS.has(gameId)) return <StockMarketPlayPage />;
  if (AI_LAB_GAME_IDS.has(gameId)) return <AiLabPlayPage />;
  return <AdventureGamePlayPage />;
}
