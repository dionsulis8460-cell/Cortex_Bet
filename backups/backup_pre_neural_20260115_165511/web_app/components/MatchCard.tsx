"use client"

import React from 'react';
import { motion } from 'framer-motion';
import { Activity, Beaker, TrendingUp } from 'lucide-react';

interface MatchProps {
  id: number;
  league: string;
  homeTeam: string;
  awayTeam: string;
  score: { home: number; away: number };
  minute: string;
  prediction: string;
  probability: number;
}

const MatchCard = ({ league, homeTeam, awayTeam, score, minute, prediction, probability }: MatchProps) => {
  return (
    <motion.div 
      whileHover={{ y: -5, scale: 1.02 }}
      className="bg-secondary/40 backdrop-blur-xl border border-white/5 p-5 rounded-3xl hover:border-primary/40 transition-all cursor-pointer group shadow-2xl"
    >
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-accent rounded-full animate-pulse" />
          <span className="text-[10px] font-black tracking-[0.2em] text-white/40 uppercase">{league}</span>
        </div>
        <span className="text-primary font-mono text-[11px] bg-primary/10 px-2.5 py-1 rounded-full">{minute}</span>
      </div>

      <div className="flex flex-col gap-4 mb-8">
        <div className="flex justify-between items-center">
          <span className="text-lg font-bold tracking-tight">{homeTeam}</span>
          <span className="text-2xl font-black text-white">{score.home}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-lg font-bold tracking-tight text-white/70">{awayTeam}</span>
          <span className="text-2xl font-black text-white/70">{score.away}</span>
        </div>
      </div>

      <div className="bg-primary/5 rounded-2xl p-4 border border-primary/10 flex items-center justify-between group-hover:bg-primary/10 transition-colors">
        <div>
          <p className="text-[9px] font-bold text-primary/60 uppercase tracking-widest mb-1 flex items-center gap-1">
            <Beaker size={10} /> AI Consensus
          </p>
          <p className="text-sm font-black text-white">{prediction}</p>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-1 justify-end text-primary mb-1">
             <TrendingUp size={12} />
             <span className="text-xs font-black">{probability}%</span>
          </div>
          <div className="w-24 h-1 bg-white/5 rounded-full overflow-hidden">
             <motion.div 
                initial={{ width: 0 }}
                animate={{ width: `${probability}%` }}
                className="h-full bg-gradient-to-r from-primary to-secondary"
             />
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default MatchCard;
