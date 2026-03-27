"use client";

import { TrendingUp, TrendingDown, Activity, Target, Zap } from 'lucide-react';

interface PerformanceMetricsProps {
  metrics: {
    total_bets: number;
    wins: number;
    losses: number;
    pending: number;
    win_rate: number;
    rps: number | null;
    mae: number | null;
    ece: number | null;
  };
}

export default function PerformanceMetrics({ metrics }: PerformanceMetricsProps) {
  if (!metrics) {
    return <div className="text-slate-400 text-center py-8">No metrics available</div>;
  }

  const metricCards = [
    {
      title: 'Win Rate (Top 7 Only)',
      value: `${metrics.win_rate}%`,
      subtitle: `${metrics.wins}/${metrics.wins + metrics.losses} finalized`,
      icon: <Target className="text-emerald-500" size={24} />,
      bgColor: 'bg-emerald-500/10',
      borderColor: 'border-emerald-500/30',
      trend: metrics.win_rate >= 70 ? 'up' : metrics.win_rate >= 60 ? 'neutral' : 'down'
    },
    {
      title: 'Green (Correct)',
      value: metrics.wins,
      subtitle: 'Successful Predictions',
      icon: <TrendingUp className="text-emerald-500" size={24} />,
      bgColor: 'bg-emerald-500/10',
      borderColor: 'border-emerald-500/30',
      tooltip: 'Total number of Top 7 predictions that were correct (Green)'
    },
    {
      title: 'Red (Incorrect)',
      value: metrics.losses,
      subtitle: 'Failed Predictions',
      icon: <TrendingDown className="text-red-500" size={24} />,
      bgColor: 'bg-red-500/10',
      borderColor: 'border-red-500/30',
      tooltip: 'Total number of Top 7 predictions that were incorrect (Red)'
    },
    {
      title: 'Pending (Waiting)',
      value: metrics.pending,
      subtitle: 'Awaiting Results',
      icon: <Activity className="text-yellow-500" size={24} />,
      bgColor: 'bg-yellow-500/10',
      borderColor: 'border-yellow-500/30',
      tooltip: 'Predictions awaiting match finish or validation'
    }
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
      {metricCards.map((card, idx) => (
        <div
          key={idx}
          className={`${card.bgColor} border ${card.borderColor} rounded-xl p-4 relative group`}
          title={card.tooltip}
        >
          {/* Tooltip */}
          {card.tooltip && (
            <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 w-64 p-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 hidden md:block">
              {card.tooltip}
            </div>
          )}

          <div className="flex items-start justify-between mb-3">
            <div className={`p-2 rounded-lg ${card.bgColor}`}>
              {card.icon}
            </div>
            {card.trend && (
              <div className={`${
                card.trend === 'up' ? 'text-emerald-500' :
                card.trend === 'down' ? 'text-red-500' :
                'text-slate-500'
              }`}>
                {card.trend === 'up' ? <TrendingUp size={16} /> : 
                 card.trend === 'down' ? <TrendingDown size={16} /> : null}
              </div>
            )}
          </div>

          <h3 className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1">
            {card.title}
          </h3>
          <p className="text-white text-2xl font-bold mb-1">
            {card.value}
          </p>
          <p className="text-slate-500 text-xs">
            {card.subtitle}
          </p>
        </div>
      ))}
    </div>
  );
}
