"use client";

import { useEffect, useState } from 'react';
import { Wallet, TrendingUp, History, CheckCircle2, XCircle, Clock, DollarSign } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface BetItemDetail {
  label: string;
  odds: number;
  status: string;
  match: string;
}

interface BetHistoryItem {
  id: number;
  label: string;
  line: number;
  stake: number;
  house_odd: number;
  fair_odd: number;
  status: string;
  profit: number;
  created_at: string;
  home_team: string; // Legacy/Compat
  away_team: string; // Legacy/Compat
  match_time: number;
  items?: BetItemDetail[]; // New field
  match_name?: string; // Added for single bet display
}

export default function MyBets() {
  const [balance, setBalance] = useState<number>(0);
  const [bets, setBets] = useState<BetHistoryItem[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [expandedBetId, setExpandedBetId] = useState<number | null>(null);

  useEffect(() => {
    fetchBankrollData();
  }, []);

  const fetchBankrollData = async () => {
    try {
      const userId = localStorage.getItem('userId') || '1';
      const res = await fetch(`/api/bankroll?type=all&userId=${userId}`);
      const result = await res.json();
      
      if (result.success) {
        setBalance(result.data.balance);
        setBets(result.data.bets || []);
        setStats(result.data.stats);
      }
    } catch (err) {
      console.error('Failed to fetch bankroll:', err);
    } finally {
      setLoading(false);
    }
  };

  /* Delete Handler */
  const handleDeleteBet = async (id: number) => {
    if (!confirm('Are you sure you want to delete this bet? This will refund the stake if pending.')) return;

    try {
      const userId = localStorage.getItem('userId') || '1';
      const res = await fetch(`/api/bankroll?id=${id}&userId=${userId}`, { method: 'DELETE' });
      const result = await res.json();

      if (result.success) {
        // Update local state
        setBets(prev => prev.filter(b => b.id !== id));
        setBalance(result.data.new_balance);
        alert('Bet deleted successfully!');
      } else {
        alert(`Error deleting bet: ${result.error}`);
      }
    } catch (err: any) {
      alert(`Failed to delete bet: ${err.message}`);
    }
  };

  /* Transaction Handler */
  const handleTransaction = async (type: 'DEPOSIT' | 'WITHDRAW') => {
    const amountStr = prompt(`Enter amount to ${type.toLowerCase()}:`);
    if (!amountStr) return;
    
    const amount = parseFloat(amountStr);
    if (isNaN(amount) || amount <= 0) {
      alert('Invalid amount');
      return;
    }

    try {
      const userId = localStorage.getItem('userId') || '1';
      const res = await fetch('/api/bankroll', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'transaction',
          userId: userId,
          type: type,
          amount: amount
        })
      });

      const result = await res.json();
      if (result.success) {
        setBalance(result.data.new_balance);
        alert(`${type} successful! New balance: R$ ${result.data.new_balance.toFixed(2)}`);
        // Refresh full data to show in history
        fetchBankrollData();
      } else {
        alert(`Transaction failed: ${result.error}`);
      }
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    }
  };

  const toggleExpand = (id: number) => {
    setExpandedBetId(expandedBetId === id ? null : id);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent"></div>
      </div>
    );
  }

  const roi = balance > 0 ? ((balance - 1000) / 1000 * 100) : 0;
  const totalProfit = stats?.total_profit || 0;

  return (
    <div className="space-y-8 pb-10">
      {/* Bankroll Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Balance Card */}
        <div className="bg-slate-800 p-8 rounded-2xl border border-slate-700 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-110 transition-transform">
            <Wallet size={80} />
          </div>
          <p className="text-slate-400 text-sm font-medium mb-1">Current Balance</p>
          <p className="text-4xl font-bold text-white font-mono">R$ {balance.toFixed(2)}</p>
          <div className="mt-4 flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <span className={`text-sm font-bold flex items-center gap-1 ${roi >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                <TrendingUp size={16} /> {roi >= 0 ? '+' : ''}{roi.toFixed(1)}%
              </span>
              <span className="text-slate-500 text-xs">from R$ 1,000</span>
            </div>
            
            <div className="flex gap-2 mt-2 z-10">
              <button 
                onClick={() => handleTransaction('DEPOSIT')}
                className="flex-1 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 text-xs font-bold py-2 px-3 rounded-lg border border-emerald-600/30 transition-colors flex items-center justify-center gap-1"
              >
                <DollarSign size={14} /> Deposit
              </button>
              <button 
                onClick={() => handleTransaction('WITHDRAW')}
                className="flex-1 bg-red-600/20 hover:bg-red-600/30 text-red-400 text-xs font-bold py-2 px-3 rounded-lg border border-red-600/30 transition-colors flex items-center justify-center gap-1"
              >
                <Wallet size={14} /> Withdraw
              </button>
            </div>
          </div>
        </div>

        {/* Performance Card */}
        <div className="bg-slate-800 p-8 rounded-2xl border border-slate-700">
          <p className="text-slate-400 text-sm font-medium mb-1">Total Record</p>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-3xl font-bold text-white">
                {stats?.wins || 0}W - {(stats?.total_bets || 0) - (stats?.wins || 0) - (stats?.pending || 0)}L
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Win Rate: {stats?.win_rate?.toFixed(1) || 0}%
              </p>
            </div>
            <div className="text-right">
              <p className={`text-2xl font-bold ${totalProfit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {totalProfit >= 0 ? '+' : ''}R$ {totalProfit.toFixed(2)}
              </p>
              <p className="text-xs text-slate-500 mt-1">Net Profit</p>
            </div>
          </div>
        </div>

        {/* Stats Card */}
        <div className="bg-slate-800 p-8 rounded-2xl border border-slate-700">
          <p className="text-slate-400 text-sm font-medium mb-1">Bet Statistics</p>
          <div className="space-y-3 mt-3">
            <div className="flex justify-between items-center">
              <span className="text-slate-400 text-sm">Total Bets</span>
              <span className="text-white font-bold">{stats?.total_bets || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400 text-sm">Pending</span>
              <span className="text-yellow-400 font-bold">{stats?.pending || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400 text-sm">Avg Stake</span>
              <span className="text-blue-400 font-bold font-mono">
                R$ {bets.length > 0 ? (bets.reduce((s, b) => s + b.stake, 0) / bets.length).toFixed(2) : '0.00'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Bankroll Evolution Chart */}
      {bets.length > 0 && (
        <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700">
          <h3 className="text-lg font-bold text-white mb-6">📈 Bankroll Evolution</h3>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={generateBankrollHistory(bets, 1000)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis 
                  dataKey="index" 
                  stroke="#94a3b8" 
                  fontSize={12}
                  label={{ value: 'Bet Number', position: 'insideBottom', offset: -5 }}
                />
                <YAxis 
                  stroke="#94a3b8" 
                  fontSize={12}
                  label={{ value: 'Balance (R$)', angle: -90, position: 'insideLeft' }}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                  itemStyle={{ color: '#f1f5f9' }}
                />
                <Line 
                  type="monotone" 
                  dataKey="balance" 
                  stroke="#10b981" 
                  strokeWidth={3}
                  dot={{ fill: '#10b981', r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Recent Bets History */}
      <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
        <div className="p-6 border-b border-slate-700 flex items-center justify-between">
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <History size={20} className="text-blue-400" />
            Bet History ({bets.length})
          </h3>
        </div>
        
        {bets.length === 0 ? (
          <div className="p-12 text-center">
            <div className="text-6xl mb-4">📊</div>
            <p className="text-slate-400">No bets placed yet</p>
            <p className="text-slate-500 text-sm mt-2">Start building your slip and track your performance!</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px] text-left border-collapse">
              <thead className="bg-slate-900/50 text-slate-400 text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-4 font-semibold w-8"></th>
                  <th className="px-6 py-4 font-semibold">Date</th>
                  <th className="px-6 py-4 font-semibold">Match</th>
                  <th className="px-6 py-4 font-semibold">Bet</th>
                  <th className="px-6 py-4 font-semibold">Stake</th>
                  <th className="px-6 py-4 font-semibold">Odd</th>
                  <th className="px-6 py-4 font-semibold">Profit</th>
                  <th className="px-6 py-4 font-semibold text-right">Status</th>
                  <th className="px-6 py-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {bets.map((bet) => (
                  <>
                  <tr key={bet.id} className="hover:bg-slate-700/30 transition-colors cursor-pointer" onClick={() => bet.items && bet.items.length > 1 && toggleExpand(bet.id)}>
                    <td className="px-6 py-4 text-center">
                       {bet.items && bet.items.length > 1 && (
                         <span className="text-slate-400 text-xs">{expandedBetId === bet.id ? '▼' : '▶'}</span>
                       )}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-400">
                      {new Date(bet.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })}
                    </td>
                    <td className="px-6 py-4 text-sm text-white font-medium">
                      {(bet.items && bet.items.length > 1) ? 
                        <span className="text-blue-300 font-bold italic">Multi-Bet ({bet.items.length} items)</span> : 
                        (bet.home_team && bet.away_team ? `${bet.home_team} vs ${bet.away_team}` : bet.match_name || 'Match Info N/A')
                      }
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-300">{bet.label}</td>
                    <td className="px-6 py-4 text-sm text-white font-mono">R$ {bet.stake.toFixed(2)}</td>
                    <td className="px-6 py-4 text-sm text-blue-400 font-mono">@{bet.house_odd?.toFixed(2) || bet.fair_odd?.toFixed(2)}</td>
                    <td className={`px-6 py-4 text-sm font-bold font-mono ${
                      bet.status === 'GREEN' ? 'text-emerald-400' : 
                      bet.status === 'RED' ? 'text-red-400' : 
                      'text-slate-400'
                    }`}>
                      {bet.status === 'PENDING' ? '--' : `${bet.profit >= 0 ? '+' : ''}R$ ${bet.profit.toFixed(2)}`}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {bet.status === 'GREEN' ? (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 text-emerald-400 rounded-full text-xs font-bold border border-emerald-500/20">
                          <CheckCircle2 size={12} /> GREEN
                        </span>
                      ) : bet.status === 'RED' ? (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-red-500/10 text-red-400 rounded-full text-xs font-bold border border-red-500/20">
                          <XCircle size={12} /> RED
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-yellow-500/10 text-yellow-400 rounded-full text-xs font-bold border border-yellow-500/20">
                          <Clock size={12} /> PENDING
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right" onClick={(e) => e.stopPropagation()}>
                       <button
                         onClick={() => handleDeleteBet(bet.id)}
                         className="p-1 hover:bg-slate-700 rounded text-slate-400 hover:text-red-400 transition-colors"
                         title="Delete Bet"
                       >
                         <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
                       </button>
                    </td>
                  </tr>
                  
                  {/* Expanded Details Row */}
                  {expandedBetId === bet.id && bet.items && bet.items.length > 1 && (
                    <tr className="bg-slate-800/50">
                      <td colSpan={9} className="px-6 py-4 pl-14">
                        <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700/50 space-y-2">
                          <div className="text-xs text-slate-500 font-bold uppercase tracking-wider mb-2">Build of Bet #{bet.id}</div>
                          {bet.items.map((item, idx) => (
                            <div key={idx} className="flex items-center justify-between text-sm py-1 border-b border-slate-800 last:border-0">
                               <div className="flex-1">
                                 <span className="text-blue-300 mr-2">{item.match}</span>
                               </div>
                               <div className="flex-1 text-center">
                                 <span className="text-white bg-slate-800 px-2 py-0.5 rounded text-xs">{item.label}</span>
                               </div>
                               <div className="w-20 text-right font-mono text-slate-400">
                                 @{item.odds.toFixed(2)}
                               </div>
                               <div className="w-20 text-right">
                                  {item.status === 'GREEN' && <span className="text-emerald-400 text-xs">✔</span>}
                                  {item.status === 'RED' && <span className="text-red-400 text-xs">✘</span>}
                                  {item.status === 'PENDING' && <span className="text-yellow-400 text-xs">⏱</span>}
                               </div>
                            </div>
                          ))}
                        </div>
                      </td>
                    </tr>
                  )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// Helper function to generate bankroll evolution data
function generateBankrollHistory(bets: BetHistoryItem[], startingBalance: number) {
  let balance = startingBalance;
  const history = [{ index: 0, balance: startingBalance }];
  
  // Sort bets by date
  const sortedBets = [...bets].sort((a, b) => 
    new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );
  
  sortedBets.forEach((bet, index) => {
    balance += bet.profit;
    history.push({
      index: index + 1,
      balance: balance
    });
  });
  
  return history;
}
