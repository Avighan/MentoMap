/**
 * PlayRouter — dispatches /play/:gameId to the right play screen.
 *
 * The 3 Phase 1 pilot games (dealcraft, mumbai_manufacturer, heliogrid)
 * have their own bespoke backend engines and use PilotGamePlayPage; every
 * other whitelisted "rounds"-type game runs through the generic engine.py
 * play path and uses AdventureGamePlayPage. Neither page needs to know
 * about the other — this is just the routing decision.
 */
import { useParams } from 'react-router-dom';
import PilotGamePlayPage from './PilotGamePlayPage';
import AdventureGamePlayPage from './AdventureGamePlayPage';

const PILOT_GAME_IDS = new Set(['dealcraft', 'mumbai_manufacturer', 'heliogrid']);

export default function PlayRouter() {
  const { gameId } = useParams();
  return PILOT_GAME_IDS.has(gameId) ? <PilotGamePlayPage /> : <AdventureGamePlayPage />;
}
