"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  Plus,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import { useBettingSlip } from "../contexts/BettingSlipContext";
import MatchStatusBadge from "./MatchStatusBadge";

interface MatchPrediction {
  id: string;
  homeTeam: string;
  awayTeam: string;
  homePosition?: number;
  awayPosition?: number;
  kickoff: string;
  status?: string;  // 'inprogress', 'finished', 'notstarted'
  matchMinute?: string;  // '45+2', 'HT', '78', etc.
  homeScore?: number;
  awayScore?: number;
  mainBet: {
    type: string;
    line: number;
    prediction: number;
    confidence: number;
    fairOdd: number;
    isCorrect?: boolean | null; // NEW
    status?: string; // NEW
  };
  aiReasoning: {
    recentForm: {
      homeSpecific?: { avg: number; std: number; trend: number; games: number[]; ht?: any; st?: any };
      awaySpecific?: { avg: number; std: number; trend: number; games: number[]; ht?: any; st?: any };
      homeOverall?: { avg: number; std: number; trend: number; games: number[]; ht?: any; st?: any };
      awayOverall?: { avg: number; std: number; trend: number; games: number[]; ht?: any; st?: any };
    };
    h2h?: { avg: number; games: number[] };
    featureImportance: { name: string; value: number }[];
    riskFactors: {
      type: string;
      description: string;
      status: "good" | "warning" | "bad";
    }[];
  };
  liveStats?: {
    homeScore: number;
    awayScore: number;
    homeCorners: number;
    awayCorners: number;
    homeCornersHT: number;
    awayCornersHT: number;
    totalCorners: number;
    possessionHome?: number;
    possessionAway?: number;
    attacksHome?: number;
    attacksAway?: number;
    xgHome?: number;
    xgAway?: number;
    shotsHome?: number;
    shotsAway?: number;
  };
  alternativeBets: Array<{
    type: string;
    prediction: number;
    confidence: number;
    fairOdd: number;
    isCorrect?: boolean | null; // NEW
    status?: string; // NEW
  }>;
  generalPrediction?: number;
}

export default function MatchCardV2({
  match,
  rank,
}: {
  match: MatchPrediction;
  rank: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const { addBet } = useBettingSlip();

  const getRankIcon = (rank: number) => {
    if (rank === 1) return "🔥";
    if (rank >= 2 && rank <= 3) return "✅";
    return "⚠️";
  };

  const getStatusColor = (status: string) => {
    if (status === "good") return "text-emerald-500";
    if (status === "warning") return "text-yellow-500";
    return "text-red-500";
  };

  const getMatchStatusBadge = () => {
    if (match.status === 'inprogress') {
      return (
        <div className="flex items-center gap-2">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
          </span>
          <span className="text-xs font-bold text-red-500 uppercase">Live</span>
          {match.matchMinute && (
            <span className="text-xs font-mono text-red-400">{match.matchMinute}</span>
          )}
        </div>
      );
    }
    if (match.status === 'finished') {
      return <span className="text-xs font-semibold text-slate-500 uppercase">Final</span>;
    }
    return <span className="text-xs text-slate-600">{match.kickoff}</span>;
  };

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700/50 overflow-hidden hover:border-blue-500/30 transition-all">
      {/* Collapsed View */}
      <div className={`p-4 md:p-6 ${match.status === 'inprogress' ? 'bg-gradient-to-r from-slate-800 via-slate-800 to-red-900/10' : match.status === 'finished' ? 'opacity-75' : ''}`}>
        
        {/* Status Badge Header */}
        <div className="flex justify-between items-start mb-2">
           <MatchStatusBadge status={match.status} matchMinute={match.matchMinute} kickoff={match.kickoff} />
        </div>

        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{getRankIcon(rank)}</span>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-slate-400">#{rank}</span>
                  <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    {/* Home Team */}
                    <span>
                      {match.homeTeam}
                      {match.homePosition && (
                        <span className="text-xs text-slate-500 font-normal">
                          {" "}
                          [{match.homePosition}°]
                        </span>
                      )}
                    </span>
                    
                    {/* Score for Live/Finished matches */}
                    {(match.status === 'inprogress' || match.status === 'finished') && (
                      <span className="text-2xl font-bold text-blue-400 mx-2">
                        {match.liveStats?.homeScore ?? match.homeScore ?? 0} - {match.liveStats?.awayScore ?? match.awayScore ?? 0}
                      </span>
                    )}
                    
                    {/* VS for scheduled matches */}
                    {match.status !== 'inprogress' && match.status !== 'finished' && (
                      <span className="text-slate-500 mx-1">vs</span>
                    )}
                    
                    {/* Away Team */}
                    <span>
                      {match.awayTeam}
                      {match.awayPosition && (
                        <span className="text-xs text-slate-500 font-normal">
                          {" "}
                          [{match.awayPosition}°]
                        </span>
                      )}
                    </span>
                  </h3>
                </div>
              </div>
          </div>
          <button
            onClick={() =>
              addBet({
                matchId: parseInt(match.id),
                matchName: `${match.homeTeam} vs ${match.awayTeam}`,
                betType: match.mainBet.type,
                suggestedLine: match.mainBet.line,
                fairOdd: match.mainBet.fairOdd,
                aiSuggested: true,
              })
            }
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-white text-sm font-medium flex items-center gap-2 transition-colors"
          >
            <Plus size={16} />
            Add
          </button>
        </div>

        {/* Match Forecast / General Prediction Badge */}
        {match.generalPrediction && (
          <div className="flex justify-center mb-4">
             <div className={`border rounded-full px-4 py-1.5 flex items-center gap-2 shadow-lg backdrop-blur-sm ${
               match.status === 'finished' && match.liveStats
                 ? Math.abs(match.liveStats.totalCorners - match.generalPrediction) <= 2
                   ? 'bg-emerald-900/40 border-emerald-500/50 shadow-emerald-900/20'
                   : 'bg-red-900/40 border-red-500/50 shadow-red-900/20'
                 : 'bg-gradient-to-r from-blue-900/40 to-slate-900/40 border-blue-500/30'
             }`}>
                <span className={`text-xs font-bold uppercase tracking-wider ${
                   match.status === 'finished' && match.liveStats
                     ? Math.abs(match.liveStats.totalCorners - match.generalPrediction) <= 2
                       ? 'text-emerald-400'
                       : 'text-red-400'
                     : 'text-blue-400'
                }`}>
                  🔮 Match Forecast
                </span>
                <div className={`w-px h-3 ${
                   match.status === 'finished' && match.liveStats
                     ? Math.abs(match.liveStats.totalCorners - match.generalPrediction) <= 2
                       ? 'bg-emerald-500/30'
                       : 'bg-red-500/30'
                     : 'bg-blue-500/30'
                }`}></div>
                <span className="text-white font-mono font-bold text-sm">
                  {match.generalPrediction.toFixed(1)} <span className="text-slate-400 text-xs font-normal">corners</span>
                </span>
                
                {/* Show Actual if Finished */}
                {match.status === 'finished' && match.liveStats && (
                  <>
                     <div className="w-px h-3 bg-slate-600/50"></div>
                     <span className="text-slate-300 font-mono text-sm">
                       Actual: <span className="text-white font-bold">{match.liveStats.totalCorners}</span>
                     </span>
                  </>
                )}
             </div>
          </div>
        )}

        {/* Main Prediction */}
        <div className={`bg-slate-900/50 rounded-lg p-4 mb-4 border ${
          match.mainBet.isCorrect === true ? 'border-emerald-500/50 bg-emerald-900/10' :
          match.mainBet.isCorrect === false ? 'border-red-500/50 bg-red-900/10' :
          'border-transparent'
        }`}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm relative">
            {/* Result Badge */}
            {match.mainBet.isCorrect !== undefined && match.mainBet.isCorrect !== null && (
               <div className={`absolute -top-6 right-0 text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                 match.mainBet.isCorrect ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'
               }`}>
                 {match.mainBet.isCorrect ? '✅ Green' : '❌ Red'}
               </div>
            )}

            <div>
              <p className="text-slate-400 mb-1">Bet</p>
              <p className="text-white font-bold">{match.mainBet.type}</p>
            </div>
            <div>
              <p className="text-slate-400 mb-1">AI Prediction</p>
              <p className="text-white font-bold font-mono">
                {match.mainBet.prediction.toFixed(1)}
              </p>
            </div>
            <div>
              <p className="text-slate-400 mb-1">Confidence</p>
              <p className="text-emerald-400 font-bold">
                {(match.mainBet.confidence * 100).toFixed(0)}%
              </p>
            </div>
            <div>
              <p className="text-slate-400 mb-1">Fair Odd</p>
              <p className="text-white font-bold font-mono">
                @{match.mainBet.fairOdd.toFixed(2)}
              </p>
            </div>
          </div>
        </div>

        {/* Expand Button */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full py-2 text-sm text-blue-400 hover:text-blue-300 flex items-center justify-center gap-2 transition-colors"
        >
          📊 Why this prediction? Click to expand
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {/* Expanded View */}
      {expanded && (
        <div className="border-t border-slate-700/50 bg-slate-900/30 p-6">
          {/* AI Reasoning */}
          <div className="space-y-6">
            {/* Two-Column Layout: Specific Form vs Overall Form */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
              {/* Specific Form Card (Home/Away Only) */}
              <div className="bg-slate-800/50 rounded-lg p-4">
                <h4 className="text-white font-bold mb-3 text-sm flex items-center gap-2">
                  📈 RECENT FORM (Specific)
                </h4>
                <div className="space-y-4">
                  {/* Home Team - Home Games */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">🏠</span>
                        <span className="text-white font-medium text-sm">
                          {match.homeTeam}
                        </span>
                      </div>
                      <span className="text-xs text-slate-400 uppercase">
                        Home Only
                      </span>
                    </div>

                    {/* Full Time Row */}
                    <div className="flex items-center justify-between bg-slate-900/50 p-2 rounded mb-1">
                      <div className="flex gap-1">
                        {(match.aiReasoning.recentForm.homeSpecific?.games || []).map((g, i) => (
                          <span
                            key={i}
                            className="text-xs bg-slate-700 px-2 py-1 rounded text-slate-300 font-mono"
                          >
                            {g}
                          </span>
                        ))}
                      </div>
                      <span className="text-emerald-400 font-bold text-sm ml-2">
                        {(match.aiReasoning.recentForm.homeSpecific?.avg || "-")} 
                        <span className="text-slate-500 text-xs ml-1">
                          ± {(match.aiReasoning.recentForm.homeSpecific?.std || 0)}
                        </span>
                      </span>
                    </div>

                    {/* 1ST Half Row */}
                    {match.aiReasoning.recentForm.homeSpecific?.ht && (
                      <div className="flex items-center justify-between bg-slate-900/30 p-1.5 rounded mb-1">
                        <div className="flex items-center gap-1">
                          <span className="text-xs text-blue-400 font-semibold w-8">1ST</span>
                          <div className="flex gap-1">
                            {(match.aiReasoning.recentForm.homeSpecific.ht.games || []).map((g, i) => (
                              <span
                                key={i}
                                className="text-xs bg-slate-700/50 px-1.5 py-0.5 rounded text-slate-400 font-mono"
                              >
                                {g}
                              </span>
                            ))}
                          </div>
                        </div>
                        <span className="text-blue-400 font-semibold text-xs ml-2">
                          {match.aiReasoning.recentForm.homeSpecific.ht.avg}
                          <span className="text-slate-600 text-xs ml-1">
                            ± {match.aiReasoning.recentForm.homeSpecific.ht.std}
                          </span>
                        </span>
                      </div>
                    )}

                    {/* 2ST Half Row */}
                    {match.aiReasoning.recentForm.homeSpecific?.st && (
                      <div className="flex items-center justify-between bg-slate-900/30 p-1.5 rounded">
                        <div className="flex items-center gap-1">
                          <span className="text-xs text-orange-400 font-semibold w-8">2ST</span>
                          <div className="flex gap-1">
                            {(match.aiReasoning.recentForm.homeSpecific.st.games || []).map((g, i) => (
                              <span
                                key={i}
                                className="text-xs bg-slate-700/50 px-1.5 py-0.5 rounded text-slate-400 font-mono"
                              >
                                {g}
                              </span>
                            ))}
                          </div>
                        </div>
                        <span className="text-orange-400 font-semibold text-xs ml-2">
                          {match.aiReasoning.recentForm.homeSpecific.st.avg}
                          <span className="text-slate-600 text-xs ml-1">
                            ± {match.aiReasoning.recentForm.homeSpecific.st.std}
                          </span>
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Away Team - Away Games Only */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">✈️</span>
                        <span className="text-white font-medium text-sm">
                          {match.awayTeam}
                        </span>
                      </div>
                      <span className="text-xs text-slate-400 uppercase">
                        Away Only
                      </span>
                    </div>

                    {/* Full Time Row */}
                    <div className="flex items-center justify-between bg-slate-900/50 p-2 rounded mb-1">
                      <div className="flex gap-1">
                        {(match.aiReasoning.recentForm.awaySpecific?.games || []).map((g, i) => (
                          <span key={i} className="text-xs bg-slate-700 px-2 py-1 rounded text-slate-300 font-mono">
                            {g}
                          </span>
                        ))}
                      </div>
                      <span className="text-emerald-400 font-bold text-sm ml-2">
                        {(match.aiReasoning.recentForm.awaySpecific?.avg || "-")}
                        <span className="text-slate-500 text-xs ml-1">± {(match.aiReasoning.recentForm.awaySpecific?.std || 0)}</span>
                      </span>
                    </div>

                    {/* 1ST Half Row */}
                    {match.aiReasoning.recentForm.awaySpecific?.ht && (
                      <div className="flex items-center justify-between bg-slate-900/30 p-1.5 rounded mb-1">
                        <div className="flex items-center gap-1">
                          <span className="text-xs text-blue-400 font-semibold w-8">1ST</span>
                          <div className="flex gap-1">
                            {(match.aiReasoning.recentForm.awaySpecific.ht.games || []).map((g, i) => (
                              <span key={i} className="text-xs bg-slate-700/50 px-1.5 py-0.5 rounded text-slate-400 font-mono">{g}</span>
                            ))}
                          </div>
                        </div>
                        <span className="text-blue-400 font-semibold text-xs ml-2">
                          {match.aiReasoning.recentForm.awaySpecific.ht.avg}
                          <span className="text-slate-600 text-xs ml-1">± {match.aiReasoning.recentForm.awaySpecific.ht.std}</span>
                        </span>
                      </div>
                    )}

                    {/* 2ST Half Row */}
                    {match.aiReasoning.recentForm.awaySpecific?.st && (
                      <div className="flex items-center justify-between bg-slate-900/30 p-1.5 rounded">
                        <div className="flex items-center gap-1">
                          <span className="text-xs text-orange-400 font semibold w-8">2ST</span>
                          <div className="flex gap-1">
                            {(match.aiReasoning.recentForm.awaySpecific.st.games || []).map((g, i) => (
                              <span key={i} className="text-xs bg-slate-700/50 px-1.5 py-0.5 rounded text-slate-400 font-mono">{g}</span>
                            ))}
                          </div>
                        </div>
                        <span className="text-orange-400 font-semibold text-xs ml-2">
                          {match.aiReasoning.recentForm.awaySpecific.st.avg}
                          <span className="text-slate-600 text-xs ml-1">± {match.aiReasoning.recentForm.awaySpecific.st.std}</span>
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Overall Form Card (All Games) */}
              <div className="bg-slate-800/50 rounded-lg p-4">
                <h4 className="text-white font-bold mb-3 text-sm">
                  📊 RECENT FORM (Overall)
                </h4>
                <div className="space-y-4">
                  {/* Home Team - All Games */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">🏠</span>
                        <span className="text-white font-medium text-sm">
                          {match.homeTeam}
                        </span>
                      </div>
                      <span className="text-xs text-slate-400 uppercase">
                        All Games
                      </span>
                    </div>

                    {/* Full Time Row */}
                    <div className="flex items-center justify-between bg-slate-900/50 p-2 rounded mb-1">
                      <div className="flex gap-1">
                        {(match.aiReasoning.recentForm.homeOverall?.games || []).map((g, i) => (
                          <span
                            key={i}
                            className="text-xs bg-slate-700 px-2 py-1 rounded text-slate-300 font-mono"
                          >
                            {g}
                          </span>
                        ))}
                      </div>
                      <span className="text-emerald-400 font-bold text-sm ml-2">
                        {match.aiReasoning.recentForm.homeOverall?.avg || "-"} 
                        <span className="text-slate-500 text-xs ml-1">± {(match.aiReasoning.recentForm.homeOverall?.std || 0)}</span>
                      </span>
                    </div>

                    {/* 1ST Half Row */}
                    {match.aiReasoning.recentForm.homeOverall?.ht && (
                      <div className="flex items-center justify-between bg-slate-900/30 p-1.5 rounded mb-1">
                        <div className="flex items-center gap-1">
                          <span className="text-xs text-blue-400 font-semibold w-8">1ST</span>
                          <div className="flex gap-1">
                            {(match.aiReasoning.recentForm.homeOverall.ht.games || []).map((g, i) => (
                              <span key={i} className="text-xs bg-slate-700/50 px-1.5 py-0.5 rounded text-slate-400 font-mono">{g}</span>
                            ))}
                          </div>
                        </div>
                        <span className="text-blue-400 font-semibold text-xs ml-2">
                          {match.aiReasoning.recentForm.homeOverall.ht.avg}
                          <span className="text-slate-600 text-xs ml-1">± {match.aiReasoning.recentForm.homeOverall.ht.std}</span>
                        </span>
                      </div>
                    )}

                    {/* 2ST Half Row */}
                    {match.aiReasoning.recentForm.homeOverall?.st && (
                      <div className="flex items-center justify-between bg-slate-900/30 p-1.5 rounded">
                        <div className="flex items-center gap-1">
                          <span className="text-xs text-orange-400 font-semibold w-8">2ST</span>
                          <div className="flex gap-1">
                            {(match.aiReasoning.recentForm.homeOverall.st.games || []).map((g, i) => (
                              <span key={i} className="text-xs bg-slate-700/50 px-1.5 py-0.5 rounded text-slate-400 font-mono">{g}</span>
                            ))}
                          </div>
                        </div>
                        <span className="text-orange-400 font-semibold text-xs ml-2">
                          {match.aiReasoning.recentForm.homeOverall.st.avg}
                          <span className="text-slate-600 text-xs ml-1">± {match.aiReasoning.recentForm.homeOverall.st.std}</span>
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Away Team - All Games */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">✈️</span>
                        <span className="text-white font-medium text-sm">
                          {match.awayTeam}
                        </span>
                      </div>
                      <span className="text-xs text-slate-400 uppercase">
                        All Games
                      </span>
                    </div>

                    {/* Full Time Row */}
                    <div className="flex items-center justify-between bg-slate-900/50 p-2 rounded mb-1">
                      <div className="flex gap-1">
                        {(match.aiReasoning.recentForm.awayOverall?.games || []).map((g, i) => (
                          <span
                            key={i}
                            className="text-xs bg-slate-700 px-2 py-1 rounded text-slate-300 font-mono"
                          >
                            {g}
                          </span>
                        ))}
                      </div>
                      <span className="text-emerald-400 font-bold text-sm ml-2">
                        {match.aiReasoning.recentForm.awayOverall?.avg || "-"} 
                        <span className="text-slate-500 text-xs ml-1">± {(match.aiReasoning.recentForm.awayOverall?.std || 0)}</span>
                      </span>
                    </div>

                    {/* 1ST Half Row */}
                    {match.aiReasoning.recentForm.awayOverall?.ht && (
                      <div className="flex items-center justify-between bg-slate-900/30 p-1.5 rounded mb-1">
                        <div className="flex items-center gap-1">
                          <span className="text-xs text-blue-400 font-semibold w-8">1ST</span>
                          <div className="flex gap-1">
                            {(match.aiReasoning.recentForm.awayOverall.ht.games || []).map((g, i) => (
                              <span key={i} className="text-xs bg-slate-700/50 px-1.5 py-0.5 rounded text-slate-400 font-mono">{g}</span>
                            ))}
                          </div>
                        </div>
                        <span className="text-blue-400 font-semibold text-xs ml-2">
                          {match.aiReasoning.recentForm.awayOverall.ht.avg}
                          <span className="text-slate-600 text-xs ml-1">± {match.aiReasoning.recentForm.awayOverall.ht.std}</span>
                        </span>
                      </div>
                    )}

                    {/* 2ST Half Row */}
                    {match.aiReasoning.recentForm.awayOverall?.st && (
                      <div className="flex items-center justify-between bg-slate-900/30 p-1.5 rounded">
                        <div className="flex items-center gap-1">
                          <span className="text-xs text-orange-400 font-semibold w-8">2ST</span>
                          <div className="flex gap-1">
                            {(match.aiReasoning.recentForm.awayOverall.st.games || []).map((g, i) => (
                              <span key={i} className="text-xs bg-slate-700/50 px-1.5 py-0.5 rounded text-slate-400 font-mono">{g}</span>
                            ))}
                          </div>
                        </div>
                        <span className="text-orange-400 font-semibold text-xs ml-2">
                          {match.aiReasoning.recentForm.awayOverall.st.avg}
                          <span className="text-slate-600 text-xs ml-1">± {match.aiReasoning.recentForm.awayOverall.st.std}</span>
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Collapsible Advanced Analytics (Including H2H) */}
            <details className="group bg-slate-800/30 rounded-lg border border-slate-700/50 overflow-hidden">
              <summary className="flex items-center justify-between p-3 cursor-pointer hover:bg-slate-800/50 transition-colors">
                <h4 className="text-slate-300 font-medium text-sm flex items-center gap-2">
                  🧠 Advanced Analysis (H2H, Features & Risk)
                </h4>
                <ChevronDown
                  size={16}
                  className="text-slate-400 group-open:rotate-180 transition-transform"
                />
              </summary>

              <div className="p-4 pt-2 space-y-6">
                {/* Head-to-Head */}
                <div className="bg-slate-900/30 rounded-lg p-3">
                  <h5 className="text-xs font-bold text-slate-400 uppercase mb-3">
                    🎭 Head-to-Head (Last 3)
                  </h5>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-slate-400 text-sm">
                      Average Corners
                    </span>
                    <span className="text-white font-bold text-lg">
                      {match.aiReasoning.h2h.avg}
                    </span>
                  </div>
                  <div className="flex gap-2 justify-center mt-2">
                    {match.aiReasoning.h2h.games.map((g, i) => (
                      <div
                        key={i}
                        className="h-8 w-12 bg-slate-700/50 rounded flex items-center justify-center font-mono text-white text-sm border border-slate-600"
                      >
                        {g}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Feature Importance */}
                  <div>
                    <h5 className="text-xs font-bold text-slate-400 uppercase mb-3">
                      Feature Importance
                    </h5>
                    <div className="space-y-2">
                      {match.aiReasoning.featureImportance.map((feature, i) => (
                        <div key={i}>
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-slate-300">
                              {feature.name}
                            </span>
                            <span className="text-blue-400 font-mono">
                              {feature.value}%
                            </span>
                          </div>
                          <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full"
                              style={{ width: `${feature.value}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Risk Factors */}
                  <div>
                    <h5 className="text-xs font-bold text-slate-400 uppercase mb-3">
                      Risk Assessment
                    </h5>
                    <div className="space-y-2">
                      {match.aiReasoning.riskFactors.map((risk, i) => (
                        <div
                          key={i}
                          className="flex items-start gap-2 text-xs bg-slate-900/50 p-2 rounded"
                        >
                          <span className={getStatusColor(risk.status)}>•</span>
                          <span className="text-slate-300">
                            <span className="font-medium text-white">
                              {risk.type}:
                            </span>{" "}
                            {risk.description}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </details>

            {/* Live Stats - Only if available */}
            {match.liveStats && (
              <div className="mb-6">
                <h4 className="text-white font-bold mb-3 flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                  LIVE MATCH STATS
                </h4>
                <div className="bg-slate-800/80 rounded-lg p-4 border border-slate-700">
                  {/* Scoreboard (Compact) */}
                  <div className="flex justify-center items-center gap-6 mb-4">
                    <div className="text-center w-24">
                       <span className="text-2xl font-bold text-white">{match.liveStats.homeScore}</span>
                       <p className="text-[10px] text-slate-400 truncate">{match.homeTeam}</p>
                    </div>
                    <div className="text-slate-500 font-bold">:</div>
                    <div className="text-center w-24">
                       <span className="text-2xl font-bold text-white">{match.liveStats.awayScore}</span>
                       <p className="text-[10px] text-slate-400 truncate">{match.awayTeam}</p>
                    </div>
                  </div>

                  {/* Possession Bar */}
                  {(match.liveStats.possessionHome > 0 || match.liveStats.possessionAway > 0) && (
                    <div className="mb-4">
                      <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                        <span>{match.liveStats.possessionHome}%</span>
                        <span>POSSESSION</span>
                        <span>{match.liveStats.possessionAway}%</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-700 rounded-full overflow-hidden flex">
                        <div 
                          className="h-full bg-emerald-500" 
                          style={{ width: `${match.liveStats.possessionHome}%` }}
                        />
                        <div 
                          className="h-full bg-red-500" 
                          style={{ width: `${match.liveStats.possessionAway}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Advanced Stats Grid */}
                  <div className="space-y-1">
                    {[
                       { label: 'xG', home: match.liveStats.xgHome?.toFixed(2), away: match.liveStats.xgAway?.toFixed(2), visible: (match.liveStats.xgHome || 0) + (match.liveStats.xgAway || 0) > 0 },
                       { label: 'Attacks', home: match.liveStats.attacksHome, away: match.liveStats.attacksAway, visible: (match.liveStats.attacksHome || 0) + (match.liveStats.attacksAway || 0) > 0 },
                       { label: 'Shots', home: match.liveStats.shotsHome, away: match.liveStats.shotsAway, visible: (match.liveStats.shotsHome || 0) + (match.liveStats.shotsAway || 0) > 0 },
                       { label: 'Corners', home: match.liveStats.homeCorners, away: match.liveStats.awayCorners, visible: true },
                       { label: '1T Corn.', home: match.liveStats.homeCornersHT, away: match.liveStats.awayCornersHT, visible: true },
                       { label: '2T Corn.', home: (match.liveStats.homeCorners - match.liveStats.homeCornersHT), away: (match.liveStats.awayCorners - match.liveStats.awayCornersHT), visible: true },
                    ].map((stat, i) => (
                       stat.visible && (
                          <div key={i} className="flex items-center justify-between text-xs py-1 border-b border-slate-700/50 last:border-0 hover:bg-slate-700/20 px-2 rounded">
                             <span className="font-mono font-bold text-slate-300 w-12 text-left">{stat.home}</span>
                             <span className="text-slate-500 uppercase font-medium">{stat.label}</span>
                             <span className="font-mono font-bold text-slate-300 w-12 text-right">{stat.away}</span>
                          </div>
                       )
                    ))}
                  </div>

                   <div className="mt-3 text-center">
                     <span className="text-xs text-slate-500">Total Match Corners: </span>
                     <span className="text-sm font-bold text-amber-400">{match.liveStats.totalCorners}</span>
                   </div>

                </div>
              </div>
            )}

            {/* Alternative Bets */}
            <div>
              <h4 className="text-white font-bold mb-3">
                📋 ALTERNATIVE MARKETS (Match Specific)
              </h4>
                {/* Compact Alternative Markets Table */}
                <div className="bg-slate-800/50 rounded-lg overflow-hidden border border-slate-700/50">
                  <table className="w-full text-sm text-left">
                    <thead className="text-xs text-slate-400 uppercase bg-slate-900/50">
                      <tr>
                        <th className="px-3 py-2">Market</th>
                        <th className="px-3 py-2 text-center">Pred</th>
                        <th className="px-3 py-2 text-center">Conf</th>
                        <th className="px-3 py-2 text-center">Odd</th>
                        <th className="px-3 py-2 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700/50">
                      {match.alternativeBets.map((bet, i) => (
                        <tr 
                          key={i} 
                          className={`hover:bg-slate-700/30 transition-colors ${
                             bet.isCorrect === true ? 'bg-emerald-900/10' :
                             bet.isCorrect === false ? 'bg-red-900/10' : ''
                          }`}
                        >
                          <td className="px-3 py-2 font-medium text-white">
                             <div className="flex items-center gap-2">
                               {bet.isCorrect === true && <span className="text-emerald-500 text-xs">✅</span>}
                               {bet.isCorrect === false && <span className="text-red-500 text-xs">❌</span>}
                               {bet.type}
                             </div>
                          </td>
                          <td className="px-3 py-2 text-center font-mono text-slate-300">
                            {bet.prediction.toFixed(1)}
                          </td>
                          <td className="px-3 py-2 text-center">
                            <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${
                              bet.confidence > 0.7 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-blue-500/20 text-blue-400'
                            }`}>
                              {(bet.confidence * 100).toFixed(0)}%
                            </span>
                          </td>
                          <td className="px-3 py-2 text-center font-mono text-slate-300">
                            @{bet.fairOdd.toFixed(2)}
                          </td>
                          <td className="px-3 py-2 text-right">
                             <button 
                               onClick={() => {
                                 // Extract line from type string (e.g. "Over 10.5" -> 10.5)
                                 const lineMatch = bet.type.match(/[0-9]+(\.[0-9]+)?/);
                                 const extractedLine = lineMatch ? parseFloat(lineMatch[0]) : 0;
                                 
                                 addBet({
                                   matchId: parseInt(match.id),
                                   matchName: `${match.homeTeam} vs ${match.awayTeam}`,
                                   betType: bet.type,
                                   suggestedLine: extractedLine,
                                   fairOdd: bet.fairOdd,
                                   aiSuggested: true,
                                 });
                               }}
                               className="p-1 hover:bg-blue-600 rounded transition-colors inline-flex"
                             >
                               <Plus size={14} className="text-white" />
                             </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
