"use client";

import { useEffect, useState } from 'react';
import { Trophy, TrendingUp, AlertTriangle } from 'lucide-react';

interface Prediction {
    id: string;
    homeTeam: string;
    awayTeam: string;
    kickoff: string;
    league: string;
    mainBet: {
        type: string;
        prediction: number;
        confidence: number;
        fairOdd: number;
        marketGroup: string;
    };
}

export default function TopOpportunitiesList() {
    const [stats, setTopStats] = useState<Prediction[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchTop7 = async () => {
            try {
                const res = await fetch('/api/predictions?top7Only=true');
                const data = await res.json();
                if (data.success) {
                    setTopStats(data.matches);
                }
            } catch (error) {
                console.error('Error fetching Top 7:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchTop7();
    }, []);

    if (loading) return null; // Don't show loading state to avoid clutter, just appear when ready

    return (
        <div className="mt-8 mb-12 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="flex items-center gap-3 mb-6">
                <div className="p-3 bg-gradient-to-br from-amber-500/20 to-orange-500/20 rounded-xl border border-amber-500/30 shadow-lg shadow-amber-900/20">
                    <Trophy className="text-amber-500" size={24} />
                </div>
                <div>
                    <h2 className="text-2xl font-bold text-white bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
                        Top 7 AI Opportunities
                    </h2>
                    <p className="text-slate-400 text-sm">Targeted high-value predictions across all leagues</p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {stats.map((match, index) => (
                    <div 
                        key={`${match.id}-${index}`}
                        className="group bg-slate-900/50 border border-slate-700/50 rounded-xl overflow-hidden hover:border-amber-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-amber-900/10 hover:-translate-y-1"
                    >
                        {/* Header */}
                        <div className="p-4 border-b border-slate-800/50 bg-slate-900/80">
                            <div className="flex justify-between items-start mb-2">
                                <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-slate-800 text-xs font-bold text-slate-400 border border-slate-700">
                                    #{index + 1}
                                </span>
                                <span className="text-xs font-medium text-amber-500 bg-amber-500/10 px-2 py-1 rounded border border-amber-500/20">
                                    {(match.mainBet.confidence * 100).toFixed(0)}% Conf
                                </span>
                            </div>
                            <h3 className="text-sm font-semibold text-white leading-tight mb-1">
                                {match.homeTeam}
                                <span className="text-slate-500 mx-1">vs</span>
                                {match.awayTeam}
                            </h3>
                            <div className="flex justify-between items-center text-xs text-slate-500">
                                <span>{match.league}</span>
                                <span>{match.kickoff}</span>
                            </div>
                        </div>

                        {/* Bet & Reason */}
                        <div className="p-4 bg-gradient-to-b from-slate-900/50 to-slate-800/30">
                            <div className="mb-3">
                                <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Recommended Bet</p>
                                <div className="flex justify-between items-center">
                                    <span className="font-bold text-emerald-400 text-lg">{match.mainBet.type}</span>
                                    <span className="font-mono text-white bg-slate-800 px-2 py-1 rounded border border-slate-700">
                                        @{match.mainBet.fairOdd.toFixed(2)}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
