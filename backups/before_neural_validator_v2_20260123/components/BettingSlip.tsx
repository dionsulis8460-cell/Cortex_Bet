"use client";

import { useState, useEffect } from 'react';
import { X, Edit2, TrendingUp, DollarSign, Lock, Unlock } from 'lucide-react';
import { useBettingSlip } from '../contexts/BettingSlipContext';

export default function BettingSlip() {
  const { bets, removeBet, updateBet, clearAllBets } = useBettingSlip();
  const [editingBet, setEditingBet] = useState<string | null>(null);
  const [customLineInput, setCustomLineInput] = useState('');
  const [stake, setStake] = useState<number>(10);
  const [manualOddMode, setManualOddMode] = useState(false);
  const [manualOdd, setManualOdd] = useState<number>(0);
  const [balance, setBalance] = useState<number>(0);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchBalance();
  }, []);

  const fetchBalance = async () => {
    try {
      const userId = localStorage.getItem('userId') || '1';
      const res = await fetch(`/api/bankroll?type=balance&userId=${userId}`);
      const data = await res.json();
      if (data.success) {
        setBalance(data.data.balance);
      }
    } catch (err) {
      console.error('Failed to fetch balance:', err);
    }
  };

  const updateCustomLine = (id: string, newLine: number) => {
    const bet = bets.find(b => b.id === id);
    if (!bet) return;
    
    const newProb = calculateNewProb(newLine, bet.suggestedLine);
    const newFairOdd = 1 / newProb; // Fair odd = 1 / probability
    
    updateBet(id, { 
      customLine: newLine, 
      recalculatedProb: newProb,
      fairOdd: newFairOdd  // Update fair odd based on new probability
    });
    setEditingBet(null);
  };

  const calculateNewProb = (customLine: number, suggestedLine: number): number => {
    // Simplified - in practice, would call API or Poisson calculation
    const diff = Math.abs(customLine - suggestedLine);
    return Math.max(0.5, 0.84 - (diff * 0.05)); // Mock calculation
  };

  const getCombinedOdd = (): number => {
    if (manualOddMode && manualOdd > 0) return manualOdd;
    if (bets.length === 0) return 0;
    return bets.reduce((acc, bet) => acc * (bet.houseOdd || bet.fairOdd), 1);
  };

  const getEstimatedWinRate = (): number => {
    if (bets.length === 0) return 0;
    const prob = bets.reduce((acc, bet) => acc * (bet.recalculatedProb || 0.84), 1);
    return prob * 100;
  };

  const getPotentialReturn = (): number => {
    return stake * getCombinedOdd();
  };

  const getKellySuggestion = (): number => {
    const winRate = getEstimatedWinRate() / 100;
    const odd = getCombinedOdd();
    const kelly = (winRate * odd - 1) / (odd - 1);
    return Math.max(0, Math.min(kelly * balance, balance * 0.05)); // Cap at 5% of bankroll
  };

  const handleSubmitBet = async () => {
    if (bets.length === 0 || stake <= 0) return;
    
    setSubmitting(true);
    try {
      const userId = parseInt(localStorage.getItem('userId') || '1');
      
      const betItems = bets.map(b => {
        let finalLabel = b.betType;
        const finalLine = b.customLine || b.suggestedLine;
        
        // If custom line is used, update the label string to match
        if (b.customLine && b.customLine !== b.suggestedLine) {
           // Replace the number in the label with the new line
           // e.g., "Vis. Over 3.5" -> "Vis. Over 2.5"
           finalLabel = finalLabel.replace(/(\d+\.?\d*)/, finalLine.toString());
        }

        return {
          match_id: b.matchId,
          prediction_id: b.predictionId,
          label: finalLabel,
          match_name: b.matchName,
          line: finalLine,
          odd: b.houseOdd || b.fairOdd
        };
      });

      const betData = {
        userId: userId,
        stake: stake,
        house_odd: manualOddMode ? manualOdd : getCombinedOdd(),
        items: betItems,
        notes: `Bet with ${bets.length} selection(s)`
      };

      const res = await fetch('/api/bankroll', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(betData)
      });

      const result = await res.json();
      
      if (result.success) {
        alert(`✅ Bet placed! New balance: R$ ${result.data.new_balance.toFixed(2)}`);
        clearAllBets();
        setStake(10);
        setManualOddMode(false);
        fetchBalance();
      } else {
        alert(`❌ Error: ${result.error || 'Unknown error'}`);
      }
    } catch (err: any) {
      alert(`❌ Failed to place bet: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  /* Mobile Toggle State */
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Mobile Toggle Button (Floating) */}
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 lg:hidden z-50 bg-blue-600 text-white p-4 rounded-full shadow-2xl hover:bg-blue-500 transition-all active:scale-95"
      >
        {bets.length > 0 ? (
          <div className="relative">
            <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold px-1.5 rounded-full">
              {bets.length}
            </span>
            <span className="text-xl">🎫</span>
          </div>
        ) : (
          <span className="text-xl">🎫</span>
        )}
      </button>

      {/* Mobile Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden animate-in fade-in duration-200"
          onClick={() => setIsOpen(false)}
        />
      )}

      <div className={`
        fixed top-0 h-screen bg-slate-900 border-l border-slate-700/50 flex flex-col shadow-2xl overflow-hidden z-50 
        transition-transform duration-300 ease-out
        ${isOpen ? 'translate-x-0' : 'translate-x-full'}
        lg:translate-x-0 lg:right-0 lg:w-[400px]
        right-0 w-full max-w-md
      `}>
        {/* Mobile Close Button */}
        <button 
          onClick={() => setIsOpen(false)}
          className="absolute top-4 right-4 lg:hidden p-2 text-slate-400 hover:text-white"
        >
          <X size={24} />
        </button>
      {/* Header */}
      <div className="p-6 border-b border-slate-700/50">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          🎫 Betting Slip
          {bets.length > 0 && (
            <span className="px-2 py-1 bg-blue-600 rounded-full text-sm">{bets.length}</span>
          )}
        </h2>
        <div className="mt-2 text-sm text-slate-400">
          💰 Balance: <span className="text-emerald-400 font-bold">R$ {balance.toFixed(2)}</span>
        </div>
      </div>

      {/* Bets List */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {bets.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="text-6xl mb-4">🎯</div>
            <p className="text-slate-400 text-sm">
              No bets added yet.<br />
              Click <span className="text-blue-400 font-medium">[+Add]</span> on matches to build your slip.
            </p>
          </div>
        ) : (
          bets.map((bet, index) => (
            <div key={bet.id} className="bg-slate-800 rounded-lg p-4 border border-slate-700/50">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <p className="text-sm text-slate-400 mb-1">{index + 1}. {bet.matchName}</p>
                  <p className="text-white font-bold">{bet.betType}</p>
                </div>
                <button
                  onClick={() => removeBet(bet.id)}
                  className="p-1 hover:bg-red-600 rounded transition-colors"
                >
                  <X size={16} className="text-slate-400 hover:text-white" />
                </button>
              </div>

              {/* Line Editing */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-400">🤖 AI Line:</span>
                  <span className="text-white font-mono">{bet.suggestedLine}</span>
                </div>

                {editingBet === bet.id ? (
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      step="0.5"
                      value={customLineInput}
                      onChange={(e) => setCustomLineInput(e.target.value)}
                      className="flex-1 bg-slate-900 border border-blue-500 rounded px-3 py-1.5 text-sm text-white focus:outline-none"
                      placeholder={bet.suggestedLine.toString()}
                      autoFocus
                    />
                    <button
                      onClick={() => updateCustomLine(bet.id, parseFloat(customLineInput))}
                      className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded text-white text-sm font-medium"
                    >
                      ✓
                    </button>
                    <button
                      onClick={() => setEditingBet(null)}
                      className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded text-white text-sm"
                    >
                      ✕
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-400">📝 Your Line:</span>
                    <button
                      onClick={() => {
                        setEditingBet(bet.id);
                        setCustomLineInput(bet.customLine?.toString() || bet.suggestedLine.toString());
                      }}
                      className="flex items-center gap-1 text-blue-400 hover:text-blue-300 font-mono"
                    >
                      {bet.customLine || bet.suggestedLine}
                      <Edit2 size={12} />
                    </button>
                  </div>
                )}

                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-400">💰 Fair Odd:</span>
                  <span className="text-white font-bold font-mono">@{bet.fairOdd.toFixed(2)}</span>
                </div>

                {bet.recalculatedProb && (
                  <div className="flex items-center gap-2 text-sm mt-2 p-2 bg-blue-900/20 rounded border border-blue-500/20">
                    <TrendingUp size={14} className="text-emerald-400" />
                    <span className="text-slate-300">
                      Prob: <span className="text-emerald-400 font-bold">{(bet.recalculatedProb * 100).toFixed(0)}%</span>
                      {bet.recalculatedProb > 0.84 && <span className="text-emerald-400"> ⬆️</span>}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Summary Footer */}
      {bets.length > 0 && (
        <div className="border-t border-slate-700/50 p-6 bg-slate-950 space-y-4">
          {/* Odd Display with Manual Override */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-slate-400">💎 Total Odd:</span>
                <button
                  onClick={() => setManualOddMode(!manualOddMode)}
                  className="text-xs text-blue-400 hover:text-blue-300"
                  title="Toggle manual odd entry"
                >
                  {manualOddMode ? <Unlock size={14} /> : <Lock size={14} />}
                </button>
              </div>
              {manualOddMode ? (
                <input
                  type="number"
                  step="0.01"
                  value={manualOdd || ''}
                  onChange={(e) => setManualOdd(parseFloat(e.target.value) || 0)}
                  className="w-24 bg-slate-800 border border-blue-500 rounded px-2 py-1 text-right text-white font-mono font-bold focus:outline-none"
                  placeholder={getCombinedOdd().toFixed(2)}
                />
              ) : (
                <span className="text-2xl font-bold text-white font-mono">@{getCombinedOdd().toFixed(2)}</span>
              )}
            </div>

            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-400">🎯 Est. Win Rate:</span>
              <span className="text-lg font-bold text-emerald-400">{getEstimatedWinRate().toFixed(1)}%</span>
            </div>
          </div>

          {/* Stake Input */}
          <div className="space-y-2">
            <label className="text-sm text-slate-400 flex items-center gap-2">
              <DollarSign size={14} />
              Stake Amount:
            </label>
            <input
              type="number"
              step="1"
              min="1"
              value={stake}
              onChange={(e) => setStake(parseFloat(e.target.value) || 0)}
              className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-white font-mono font-bold focus:outline-none focus:border-blue-500"
            />
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>Kelly: R$ {getKellySuggestion().toFixed(2)}</span>
              <button
                onClick={() => setStake(getKellySuggestion())}
                className="text-blue-400 hover:text-blue-300"
              >
                Use Kelly
              </button>
            </div>
          </div>

          {/* Potential Return */}
          <div className="p-3 bg-emerald-900/20 border border-emerald-500/30 rounded-lg">
            <div className="flex items-center justify-between">
              <span className="text-emerald-400 text-sm">💰 Potential Return:</span>
              <span className="text-emerald-400 font-bold text-xl">R$ {getPotentialReturn().toFixed(2)}</span>
            </div>
            <div className="text-xs text-emerald-400/70 mt-1">
              Profit: R$ {(getPotentialReturn() - stake).toFixed(2)}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <button
              onClick={() => {
                clearAllBets();
                setManualOddMode(false);
                setStake(10);
              }}
              className="flex-1 px-4 py-3 bg-slate-800 hover:bg-slate-700 rounded-lg text-white font-medium transition-colors"
            >
              Clear All
            </button>
            <button 
              onClick={handleSubmitBet}
              disabled={submitting || stake > balance}
              className="flex-1 px-4 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg text-white font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? 'Placing...' : 'Place Bet'}
            </button>
          </div>

          {stake > balance && (
            <p className="text-red-400 text-xs text-center">
              ⚠️ Insufficient balance
            </p>
          )}
        </div>
      )}
    </div>
    </>
  );
}
