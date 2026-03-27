"use client"

import React from 'react';
import { LayoutDashboard, Activity, TrendingUp, BarChart3, Settings, Brain } from 'lucide-react';
import { motion } from 'framer-motion';

const Sidebar = () => {
  const icons = [
    { icon: LayoutDashboard, label: 'Dash' },
    { icon: Activity, label: 'Live' },
    { icon: TrendingUp, label: 'Stats' },
    { icon: BarChart3, label: 'History' },
  ];

  return (
    <aside className="fixed left-0 top-0 h-full w-24 bg-[#0a0f1a]/80 backdrop-blur-2xl border-r border-white/5 flex flex-col items-center py-10 gap-12 z-50">
      <motion.div 
        whileHover={{ rotate: 15 }}
        className="w-14 h-14 bg-gradient-to-br from-primary to-secondary rounded-2xl flex items-center justify-center shadow-[0_0_30px_-5px_rgba(0,210,255,0.5)] cursor-pointer"
      >
        <Brain className="text-white" size={32} />
      </motion.div>
      
      <nav className="flex flex-col gap-10">
        {icons.map((item, i) => (
          <motion.div 
            key={i}
            whileHover={{ scale: 1.2, color: '#00d2ff' }}
            className="text-white/30 cursor-pointer transition-colors relative group"
          >
            <item.icon size={26} />
            <span className="absolute left-16 top-1/2 -translate-y-1/2 bg-primary text-background text-[10px] font-black px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
              {item.label}
            </span>
          </motion.div>
        ))}
      </nav>

      <div className="mt-auto mb-4">
        <motion.div whileHover={{ rotate: 45 }} className="text-white/20 hover:text-white transition-colors cursor-pointer">
          <Settings size={26} />
        </motion.div>
      </div>
    </aside>
  );
};

export default Sidebar;
