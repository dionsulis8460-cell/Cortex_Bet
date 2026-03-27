"use client"

import React from 'react';
import { motion } from 'framer-motion';
import { Target, TrendingUp, ShieldCheck } from 'lucide-react';

const StatCard = ({ label, value, subtext, icon: Icon, color }: any) => (
  <motion.div 
    initial={{ opacity: 0, scale: 0.9 }}
    animate={{ opacity: 1, scale: 1 }}
    className="bg-glass border border-white/5 p-6 rounded-[2rem] shadow-2xl relative overflow-hidden group"
  >
    <div className={`absolute top-0 right-0 w-32 h-32 bg-${color}/10 blur-[60px] -mr-16 -mt-16 group-hover:bg-${color}/20 transition-colors pointer-events-none`} />
    
    <div className="flex items-center justify-between mb-6">
       <div className={`p-3 bg-${color}/10 rounded-2xl border border-${color}/20`}>
          <Icon size={24} className={`text-${color}`} />
       </div>
       <span className="text-[10px] font-black text-white/20 uppercase tracking-[0.3em]">System Engine</span>
    </div>

    <div>
       <p className="text-white/40 text-[11px] font-bold uppercase tracking-widest mb-1">{label}</p>
       <h2 className="text-4xl font-black tracking-tighter text-white mb-2">{value}</h2>
       <p className={`text-[10px] font-bold ${color === 'primary' ? 'text-primary' : color === 'green-400' ? 'text-green-400' : 'text-blue-400'} uppercase`}>
         {subtext}
       </p>
    </div>
  </motion.div>
);

const StatsGrid = () => {
  return (
    <section className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
      <StatCard 
        label="Monthly ROI" 
        value="+24.8%" 
        subtext="↑ 4.2% from last week" 
        icon={TrendingUp} 
        color="green-400" 
      />
      <StatCard 
        label="Bayesian Accuracy" 
        value="82.4%" 
        subtext="Confidence Interval: 95%" 
        icon={Target} 
        color="primary" 
      />
      <StatCard 
        label="Capital Protected" 
        value="R$ 12.5k" 
        subtext="RL Safe-Margin active" 
        icon={ShieldCheck} 
        color="blue-400" 
      />
    </section>
  );
};

export default StatsGrid;
