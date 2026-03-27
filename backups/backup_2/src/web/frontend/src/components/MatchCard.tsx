import { Card } from './ui/card';
import { useBetSlip } from '../contexts/BetSlipContext';
import { format } from 'date-fns';
import { TrendingUp, Clock } from 'lucide-react';

interface Prediction {
    id: number;
    market_group: string;
    market: string;
    probability: number;
    odds: number;
    is_bet: boolean;
    manual_odd?: number;
}

interface Match {
    match_id: number;
    home_team_name: string;
    away_team_name: string;
    tournament_name: string;
    start_timestamp: number;
    status: string;
    match_minute?: string;
    home_score?: number;
    away_score?: number;
    ml_prediction?: number;
}

interface MatchCardProps {
    match: Match;
    predictions?: Prediction[];
}

export function MatchCard({ match, predictions = [] }: MatchCardProps) {
    const { addToSlip } = useBetSlip();

    // Mock prediction if none (for testing UI)
    const displayPredictions = predictions.length > 0 ? predictions : [
        { id: 999, market: `Over ${match.ml_prediction || 9.5} Escanteios`, odds: 1.85 }
    ];

    return (
        <Card className="bg-card border-border overflow-hidden hover:border-blue-500/50 transition-colors group">
            <div className="p-4 flex gap-4 items-center">
                {/* Time / Status */}
                <div className="flex flex-col items-center justify-center w-16 text-center">
                    <span className="text-xs text-muted-foreground font-medium uppercase truncate w-full">
                        {match.match_minute || format(new Date(match.start_timestamp * 1000), 'HH:mm')}
                    </span>
                    {match.status === 'inprogress' ? (
                        <span className="text-red-500 animate-pulse text-[10px] font-bold">LIVE</span>
                    ) : (
                        <span className="text-muted-foreground text-[10px]">{format(new Date(match.start_timestamp * 1000), 'dd/MM')}</span>
                    )}
                </div>

                {/* Teams */}
                <div className="flex-1 space-y-1">
                    <div className="text-xs text-muted-foreground uppercase tracking-wide">{match.tournament_name}</div>
                    <div className="font-bold text-lg leading-none truncate">{match.home_team_name}</div>
                    <div className="font-bold text-lg leading-none truncate text-muted-foreground">{match.away_team_name}</div>
                </div>

                {/* Scores */}
                {(typeof match.home_score === 'number') && (
                    <div className="flex flex-col font-mono font-bold text-xl text-right">
                        <span>{match.home_score}</span>
                        <span>{match.away_score}</span>
                    </div>
                )}
            </div>

            {/* Predictions / Actions */}
            <div className="bg-secondary/30 p-2 grid grid-cols-2 gap-2">
                {displayPredictions.map((pred: any, idx) => (
                    <button
                        key={idx}
                        onClick={() => addToSlip({
                            match_id: match.match_id,
                            match_name: `${match.home_team_name} vs ${match.away_team_name}`,
                            selection: pred.market,
                            odds: pred.odds || 1.80, // Default odd if missing
                            prediction_id: pred.id
                        })}
                        className="bg-background hover:bg-blue-600 hover:text-white transition-colors border border-border rounded p-2 flex justify-between items-center group/btn"
                    >
                        <span className="text-xs font-medium">{pred.market}</span>
                        <div className="flex items-center gap-1">
                            {pred.probability && (
                                <span className="text-[10px] text-green-500 bg-green-500/10 px-1 rounded group-hover/btn:text-white group-hover/btn:bg-white/20">
                                    {(pred.probability * 100).toFixed(0)}%
                                </span>
                            )}
                            <span className="text-sm font-bold text-blue-400 group-hover/btn:text-white">
                                {pred.odds ? pred.odds.toFixed(2) : '-'}
                            </span>
                        </div>
                    </button>
                ))}
            </div>
        </Card>
    );
}
