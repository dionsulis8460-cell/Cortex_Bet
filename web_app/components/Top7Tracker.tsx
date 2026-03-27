"use client";

import { CheckCircle2, XCircle, Clock, ChevronDown } from 'lucide-react';
import { useState } from 'react';

interface Prediction {
  match_id: number;
  home_team: string;
  away_team: string;
  prediction: string;
  predicted_value: number;
  confidence: number;
  fair_odd: number;
  is_correct: boolean | null;
  status: string;
}

interface Top7TrackerProps {
  predictionsByDate: Record<string, Prediction[]>;
}

export default function Top7Tracker({ predictionsByDate }: Top7TrackerProps) {
  const [expandedDates, setExpandedDates] = useState<Set<string>>(new Set());

  const toggleDate = (date: string) => {
    const newSet = new Set(expandedDates);
    if (newSet.has(date)) {
      newSet.delete(date);
    } else {
      newSet.add(date);
    }
    setExpandedDates(newSet);
  };

  const getStatusDisplay = (prediction: Prediction) => {
    if (prediction.is_correct === null) {
      return {
        icon: <Clock size={16} className="text-yellow-500" />,
        badge: 'PENDING',
        bgColor: 'bg-yellow-500/10',
        borderColor: 'border-yellow-500/30',
        textColor: 'text-yellow-400'
      };
    } else if (prediction.is_correct) {
      return {
        icon: <CheckCircle2 size={16} className="text-emerald-500" />,
        badge: 'GREEN',
        bgColor: 'bg-emerald-500/10',
        borderColor: 'border-emerald-500/30',
        textColor: 'text-emerald-400'
      };
    } else {
      return {
        icon: <XCircle size={16} className="text-red-500" />,
        badge: 'RED',
        bgColor: 'bg-red-500/10',
        borderColor: 'border-red-500/30',
        textColor: 'text-red-400'
      };
    }
  };

  const dates = Object.keys(predictionsByDate).sort((a, b) => b.localeCompare(a));

  if (dates.length === 0) {
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-8 text-center">
        <p className="text-slate-400">No predictions found for the selected period</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {dates.map((date) => {
        const predictions = predictionsByDate[date];
        const isExpanded = expandedDates.has(date);
        
        // Calculate stats for this date
        const total = predictions.length;
        const wins = predictions.filter(p => p.is_correct === true).length;
        const losses = predictions.filter(p => p.is_correct === false).length;
        const pending = predictions.filter(p => p.is_correct === null).length;
        const finished = total - pending;
        const winRate = finished > 0 ? (wins / finished * 100).toFixed(1) : '0.0';

        return (
          <div key={date} className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
            {/* Date Header */}
            <button
              onClick={() => toggleDate(date)}
              className="w-full p-4 flex items-center justify-between hover:bg-slate-800/70 transition-colors"
            >
              <div className="flex items-center gap-4">
                <div className="text-left">
                  <h3 className="text-white font-bold">{new Date(date + 'T12:00:00').toLocaleDateString('pt-BR', { weekday: 'short', month: 'short', day: 'numeric' })}</h3>
                  <p className="text-sm text-slate-400">{total} Top Predictions</p>
                </div>
                
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 size={16} className="text-emerald-500" />
                    <span className="text-sm text-emerald-400 font-medium">{wins} Green</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <XCircle size={16} className="text-red-500" />
                    <span className="text-sm text-red-400 font-medium">{losses} Red</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock size={16} className="text-yellow-500" />
                    <span className="text-sm text-yellow-400 font-medium">{pending} Pending</span>
                  </div>
                </div>
                
                {finished > 0 && (
                  <div className="px-3 py-1 bg-blue-600/20 border border-blue-500/30 rounded-lg">
                    <span className="text-blue-400 font-bold text-sm">{winRate}% Win Rate</span>
                  </div>
                )}
              </div>

              <ChevronDown
                size={20}
                className={`text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
              />
            </button>

            {/* Predictions List */}
            {isExpanded && (
              <div className="border-t border-slate-700/50 p-4 space-y-3">
                {predictions.map((pred, idx) => {
                  const status = getStatusDisplay(pred);
                  
                  return (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg border ${status.bgColor} ${status.borderColor}`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {status.icon}
                          <div>
                            <p className="text-white font-medium text-sm">
                              {pred.home_team} vs {pred.away_team}
                            </p>
                            <p className="text-xs text-slate-400 mt-0.5">{pred.prediction}</p>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <p className="text-xs text-slate-400">Confidence</p>
                            <p className="text-emerald-400 font-bold text-sm">{pred.confidence}%</p>
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-slate-400">Fair Odd</p>
                            <p className="text-white font-mono font-bold text-sm">@{pred.fair_odd}</p>
                          </div>
                          <div className={`px-2 py-1 rounded text-xs font-bold ${status.textColor}`}>
                            {status.badge}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
