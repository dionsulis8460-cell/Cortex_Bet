'use client';

import React, { useEffect, useState } from 'react';
import { Clock, TrendingUp, TrendingDown, Users, RefreshCw } from 'lucide-react';

interface FeedItem {
  bet_id: number;
  username: string;
  stake: number;
  total_odds: number;
  possible_win: number;
  status: string;
  profit: number;
  created_at: string;
  bet_type: string;
  items: Array<{
    match: string;
    label: string;
    odds: number;
  }>;
}

export default function SocialFeed() {
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'green' | 'red'>('all');

  const fetchFeed = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/feed?limit=30');
      const result = await res.json();
      if (result.success) {
        setFeed(result.data.feed);
      }
    } catch (err) {
      console.error('Failed to fetch feed:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFeed();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchFeed, 30000);
    return () => clearInterval(interval);
  }, []);

  const getRelativeTime = (timestamp: string) => {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now.getTime() - then.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  const filteredFeed = feed.filter(item => {
    if (filter === 'all') return true;
    return item.status.toLowerCase() === filter;
  });

  const currentUser = localStorage.getItem('username');

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Users className="text-blue-400" size={24} />
            Live Feed
          </h2>
          <p className="text-slate-400 text-sm mt-1">Recent bets from the community</p>
        </div>
        <button 
          onClick={fetchFeed}
          disabled={loading}
          className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 bg-slate-900/50 p-1 rounded-lg border border-slate-800 overflow-x-auto">
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 text-xs font-medium rounded-md transition-all whitespace-nowrap ${
            filter === 'all' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          All Bets
        </button>
        <button
          onClick={() => setFilter('pending')}
          className={`px-4 py-2 text-xs font-medium rounded-md transition-all whitespace-nowrap ${
            filter === 'pending' ? 'bg-yellow-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          Pending
        </button>
        <button
          onClick={() => setFilter('green')}
          className={`px-4 py-2 text-xs font-medium rounded-md transition-all whitespace-nowrap ${
            filter === 'green' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          Won
        </button>
        <button
          onClick={() => setFilter('red')}
          className={`px-4 py-2 text-xs font-medium rounded-md transition-all whitespace-nowrap ${
            filter === 'red' ? 'bg-red-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          Lost
        </button>
      </div>

      {/* Feed Items */}
      <div className="space-y-4">
        {loading && feed.length === 0 ? (
          <div className="text-center py-12 text-slate-400">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent mx-auto mb-4"></div>
            Loading feed...
          </div>
        ) : filteredFeed.length === 0 ? (
          <div className="text-center py-12 text-slate-400">
            <Users size={48} className="mx-auto mb-4 opacity-50" />
            <p>No bets found</p>
          </div>
        ) : (
          filteredFeed.map((item) => (
            <div 
              key={item.bet_id} 
              className="bg-slate-800 rounded-lg p-4 border border-slate-700 hover:border-slate-600 transition-all"
            >
              {/* User Header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-lg">
                    {item.username[0].toUpperCase()}
                  </div>
                  <div>
                    <p className="text-white font-bold flex items-center gap-2">
                      {item.username}
                      {item.username === currentUser && (
                        <span className="text-[10px] bg-blue-600/20 text-blue-400 px-1.5 py-0.5 rounded">YOU</span>
                      )}
                    </p>
                    <p className="text-slate-400 text-xs flex items-center gap-1">
                      <Clock size={12} />
                      {getRelativeTime(item.created_at)}
                    </p>
                  </div>
                </div>

                {/* Status Badge */}
                <div>
                  {item.status === 'GREEN' && (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 text-emerald-400 rounded-full text-xs font-bold border border-emerald-500/20">
                      ✓ Won
                    </span>
                  )}
                  {item.status === 'RED' && (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-red-500/10 text-red-400 rounded-full text-xs font-bold border border-red-500/20">
                      ✗ Lost
                    </span>
                  )}
                  {item.status === 'PENDING' && (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-yellow-500/10 text-yellow-400 rounded-full text-xs font-bold border border-yellow-500/20">
                      ⏱ Pending
                    </span>
                  )}
                </div>
              </div>

              {/* Bet Content */}
              <div className="bg-slate-900/50 rounded-lg p-3 mb-3">
                {item.bet_type === 'MULTIPLE' && item.items.length > 1 && (
                  <div className="text-xs text-blue-400 font-bold mb-2">
                    🎯 Multi-Bet ({item.items.length} selections)
                  </div>
                )}
                <div className="space-y-2">
                  {item.items.map((bet, idx) => (
                    <div key={idx} className="flex items-center justify-between text-sm border-b border-slate-800 last:border-0 pb-2 last:pb-0">
                      <div className="flex-1">
                        <p className="text-slate-400 text-xs">{bet.match}</p>
                        <p className="text-white font-medium">{bet.label}</p>
                      </div>
                      <div className="text-blue-400 font-mono font-bold ml-4">
                        @{bet.odds.toFixed(2)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Bet Stats */}
              <div className="flex items-center justify-between text-sm">
                <div className="flex gap-4">
                  <div>
                    <span className="text-slate-500 text-xs">Stake:</span>
                    <span className="text-white font-mono ml-1">R$ {item.stake.toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 text-xs">Odds:</span>
                    <span className="text-blue-400 font-mono ml-1">@{item.total_odds.toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 text-xs">Possible:</span>
                    <span className="text-white font-mono ml-1">R$ {item.possible_win.toFixed(2)}</span>
                  </div>
                </div>

                {item.status !== 'PENDING' && (
                  <div className="flex items-center gap-1">
                    {item.profit >= 0 ? (
                      <TrendingUp size={16} className="text-emerald-400" />
                    ) : (
                      <TrendingDown size={16} className="text-red-400" />
                    )}
                    <span className={`font-mono font-bold ${item.profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {item.profit >= 0 ? '+' : ''}R$ {item.profit.toFixed(2)}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
