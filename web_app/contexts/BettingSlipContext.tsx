"use client";

import React, { createContext, useContext, useState, ReactNode } from 'react';

interface BetItem {
  id: string;
  matchId: number;
  predictionId?: number;
  matchName: string;
  betType: string;
  suggestedLine: number;
  customLine?: number;
  fairOdd: number;
  houseOdd?: number;
  recalculatedProb?: number;
  aiSuggested: boolean;
}

interface BettingSlipContextType {
  bets: BetItem[];
  addBet: (bet: Omit<BetItem, 'id'>) => void;
  removeBet: (id: string) => void;
  updateBet: (id: string, updates: Partial<BetItem>) => void;
  clearAllBets: () => void;
}

const BettingSlipContext = createContext<BettingSlipContextType | undefined>(undefined);

export function BettingSlipProvider({ children }: { children: ReactNode }) {
  const [bets, setBets] = useState<BetItem[]>([]);

  const addBet = (bet: Omit<BetItem, 'id'>) => {
    const newBet: BetItem = {
      ...bet,
      id: `${bet.matchId}-${Date.now()}-${Math.random()}`
    };
    
    // Check if bet already exists for this match + type
    const exists = bets.some(b => 
      b.matchId === bet.matchId && b.betType === bet.betType
    );
    
    if (!exists) {
      setBets(prev => [...prev, newBet]);
    }
  };

  const removeBet = (id: string) => {
    setBets(prev => prev.filter(bet => bet.id !== id));
  };

  const updateBet = (id: string, updates: Partial<BetItem>) => {
    setBets(prev => prev.map(bet => 
      bet.id === id ? { ...bet, ...updates } : bet
    ));
  };

  const clearAllBets = () => {
    setBets([]);
  };

  return (
    <BettingSlipContext.Provider value={{ bets, addBet, removeBet, updateBet, clearAllBets }}>
      {children}
    </BettingSlipContext.Provider>
  );
}

export function useBettingSlip() {
  const context = useContext(BettingSlipContext);
  if (context === undefined) {
    throw new Error('useBettingSlip must be used within a BettingSlipProvider');
  }
  return context;
}
