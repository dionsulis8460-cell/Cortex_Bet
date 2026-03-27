'use client';

import React, { useEffect, useState } from 'react';
import { Trophy, TrendingUp, DollarSign, Percent, RefreshCw } from 'lucide-react';
import SocialFeed from './SocialFeed';

interface LeaderboardEntry {
  username: string;
  roi: number;
  profit: number;
  win_rate: number;
  wins?: number; // Added field
  'Total Bets': number;
}

export default function Leaderboard() {
  const [data, setData] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'rankings' | 'feed' | 'topbets'>('rankings');

  const fetchLeaderboard = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/leaderboard');
      const result = await res.json();
      if (result.success) {
        setData(result.data.leaderboard);
      }
    } catch (err) {
      console.error('Failed to fetch leaderboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeaderboard();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Trophy className="text-yellow-500" /> Tipster League
          </h2>
          <p className="text-slate-400 text-sm mt-1">Compete with the community</p>
        </div>
        {activeTab === 'rankings' && (
          <button 
            onClick={fetchLeaderboard}
            disabled={loading}
            className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
          </button>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 bg-slate-900/50 p-1 rounded-lg border border-slate-800">
        <button
          onClick={() => setActiveTab('rankings')}
          className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-all ${
            activeTab === 'rankings' 
              ? 'bg-blue-600 text-white shadow-lg' 
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          📊 Rankings
        </button>
        <button
          onClick={() => setActiveTab('feed')}
          className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-all ${
            activeTab === 'feed' 
              ? 'bg-blue-600 text-white shadow-lg' 
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          🔴 Live Feed
        </button>
        <button
          onClick={() => setActiveTab('topbets')}
          className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-all ${
            activeTab === 'topbets' 
              ? 'bg-blue-600 text-white shadow-lg' 
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          🏆 Top Bets
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'rankings' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px] text-left border-collapse">
              <thead>
                <tr className="bg-slate-950/50 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-800">
                  <th className="p-4 font-semibold text-center w-16">Rank</th>
                  <th className="p-4 font-semibold">Tipster</th>
                  <th className="p-4 font-semibold text-right text-emerald-400">Wins</th>
                  <th className="p-4 font-semibold text-right">Total Bets</th>
                  <th className="p-4 font-semibold text-right">Win Rate</th>
                  <th className="p-4 font-semibold text-right">ROI</th>
                  <th className="p-4 font-semibold text-right">Profit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-sm">
                {data.map((entry, index) => {
                  const isTop3 = index < 3;
                  const profitColor = entry.profit >= 0 ? 'text-emerald-400' : 'text-red-400';
                  const roiColor = entry.roi >= 0 ? 'text-emerald-400' : 'text-red-400';
                  
                  return (
                    <tr key={entry.username} className="hover:bg-slate-800/50 transition-colors group">
                      <td className="p-4 text-center font-bold text-slate-500 group-hover:text-white">
                        {isTop3 ? (
                          <span className={`flex items-center justify-center w-8 h-8 rounded-full ${
                            index === 0 ? 'bg-yellow-500/20 text-yellow-500' :
                            index === 1 ? 'bg-slate-400/20 text-slate-300' :
                            'bg-amber-700/20 text-amber-600'
                          }`}>
                            {index + 1}
                          </span>
                        ) : (
                          <span>{index + 1}</span>
                        )}
                      </td>
                      <td className="p-4 font-medium text-white flex items-center gap-2">
                         {index === 0 && <span className="text-xl">👑</span>}
                         {entry.username}
                         {localStorage.getItem('username') === entry.username && (
                           <span className="text-[10px] bg-blue-600/20 text-blue-400 px-1.5 py-0.5 rounded ml-2">YOU</span>
                         )}
                      </td>
                      <td className="p-4 text-right font-bold text-emerald-400">
                        {entry.wins || 0} {/* Show Wins */}
                      </td>
                      <td className="p-4 text-right text-slate-300 font-mono">{entry['Total Bets']}</td>
                      <td className="p-4 text-right text-slate-300 font-mono">
                        {entry.win_rate.toFixed(1)}%
                      </td>
                      <td className={`p-4 text-right font-mono font-bold ${roiColor}`}>
                        {entry.roi > 0 ? '+' : ''}{entry.roi.toFixed(1)}%
                      </td>
                      <td className={`p-4 text-right font-mono font-bold ${profitColor}`}>
                        {entry.profit >= 0 ? '+' : ''}R$ {entry.profit.toFixed(2)}
                      </td>
                    </tr>
                  );
                })}
                
                {data.length === 0 && !loading && (
                  <tr>
                     <td colSpan={7} className="p-8 text-center text-slate-500 italic">No rankings available yet. Start betting!</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'feed' && <SocialFeed />}

      {activeTab === 'topbets' && (
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-12 text-center">
          <Trophy size={64} className="mx-auto mb-4 text-yellow-500 opacity-50" />
          <p className="text-slate-400 text-lg font-medium mb-2">Top Bets Coming Soon</p>
          <p className="text-slate-500 text-sm">We're working on showing the highest ROI bets of the week!</p>
        </div>
      )}
    </div>
  );
}
