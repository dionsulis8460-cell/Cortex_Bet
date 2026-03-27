"use client"

import React from 'react';
import { Bell, Search, Zap, User, FlaskConical } from 'lucide-react';
import { motion } from 'framer-motion';
import { useLabs } from '../contexts/LabsContext';

const TopBar = () => {
  return (
    <header className="flex justify-between items-center mb-10 px-4">
      <div className="flex items-center gap-8">
        <div>
          <h1 className="text-3xl font-black tracking-tighter text-white">
            CORTEX<span className="text-primary">BET</span>
            <span className="ml-3 text-[10px] font-bold border border-primary/20 bg-primary/5 px-2 py-0.5 rounded text-primary uppercase tracking-[0.2em] vertical-middle">V5 PRO</span>
          </h1>
        </div>

        <div className="hidden lg:flex items-center bg-secondary/30 border border-white/5 rounded-2xl px-4 py-2 gap-3 group focus-within:border-primary/50 transition-all">
          <Search size={18} className="text-white/20 group-focus-within:text-primary transition-colors" />
          <input 
            type="text" 
            placeholder="Search teams or leagues..." 
            className="bg-transparent border-none outline-none text-sm w-64 placeholder:text-white/20"
          />
        </div>
      </div>

      <div className="flex items-center gap-6">
        <motion.div 
           whileHover={{ scale: 1.05 }}
           className="hidden md:flex items-center gap-3 bg-accent/10 border border-accent/20 px-4 py-2 rounded-2xl cursor-pointer"
        >
          <Zap size={16} className="text-accent fill-accent" />
          <span className="text-[10px] font-black text-accent uppercase tracking-widest">High Volatility Alert</span>
        </motion.div>

        {/* Labs / Shadow Mode Toggle */}
        <ShadowModeToggle />

        <div className="flex items-center gap-4 border-l border-white/5 pl-6">
          <div className="relative cursor-pointer text-white/40 hover:text-white transition-colors">
            <Bell size={22} />
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-accent rounded-full border-2 border-background" />
          </div>
          
          <div className="flex items-center gap-3 bg-secondary/50 p-1.5 rounded-2xl border border-white/5 cursor-pointer hover:border-white/10 transition-all">
            <div className="w-8 h-8 bg-gradient-to-br from-white/10 to-white/5 rounded-xl flex items-center justify-center">
              <User size={18} className="text-white/60" />
            </div>
            <div className="hidden sm:block pr-2">
              <p className="text-[10px] font-black text-white/40 leading-none mb-1 uppercase">PHD ACCESS</p>
              <p className="text-xs font-bold text-white leading-none">Prof. Predictor</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

function ShadowModeToggle() {
  const { isShadowMode, toggleShadowMode } = useLabs();
  
  return (
    <motion.button
      whileTap={{ scale: 0.95 }}
      onClick={toggleShadowMode}
      className={`relative flex items-center gap-2 px-3 py-1.5 rounded-full border transition-all ${
        isShadowMode 
          ? "bg-purple-900/40 border-purple-500/50 text-purple-200 shadow-[0_0_15px_rgba(168,85,247,0.3)]" 
          : "bg-slate-800/50 border-slate-700 text-slate-400 hover:border-slate-500"
      }`}
    >
      <FlaskConical size={14} className={isShadowMode ? "text-purple-400 fill-purple-400/20" : ""} />
      <span className="text-[10px] font-bold uppercase tracking-wider">
        Labs: {isShadowMode ? "Ghost ON" : "Ghost OFF"}
      </span>
      {isShadowMode && (
         <span className="absolute -top-1 -right-1 flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-purple-500"></span>
         </span>
      )}
    </motion.button>
  );
}

export default TopBar;
