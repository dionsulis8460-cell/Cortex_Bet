"use client"

import React, { useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import StatsGrid from './StatsGrid';
import MatchCard from './MatchCard';
import { Activity } from 'lucide-react';

const Dashboard = () => {
  const [matches, setMatches] = useState<any[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimer: NodeJS.Timeout;

    const connect = () => {
      console.log('Attempting to connect to Cortex engine...');
      ws = new WebSocket('ws://localhost:8000/ws/live');

      ws.onopen = () => {
        console.log('✅ Connected to Cortex Engine');
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'matches_update') {
            setMatches(data.matches);
          }
        } catch (err) {
          console.error('Failed to parse WS message:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('⚠️ Disconnected from Cortex Engine');
        setIsConnected(false);
        // Attempt to reconnect after 5 seconds
        reconnectTimer = setTimeout(connect, 5000);
      };
    };

    connect();

    return () => {
      if (ws) ws.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, []);

  // Fallback / Initial Mock data
  const initialMatches = [
    {
      id: 1,
      league: "PREMIER LEAGUE",
      homeTeam: "Arsenal",
      awayTeam: "Man City",
      score: { home: 1, away: 0 },
      minute: "24'",
      prediction: "Over 10.5 Corners",
      probability: 78
    },
    {
      id: 2,
      league: "LALIGA",
      homeTeam: "Real Madrid",
      awayTeam: "Barcelona",
      score: { home: 2, away: 2 },
      minute: "78'",
      prediction: "Under 12.5 Corners",
      probability: 65
    },
    {
      id: 3,
      league: "SERIE A",
      homeTeam: "Inter Milan",
      awayTeam: "Juventus",
      score: { home: 0, away: 0 },
      minute: "12'",
      prediction: "Home Corner Race (5)",
      probability: 84
    },
    {
        id: 4,
        league: "BRASILEIRÃO",
        homeTeam: "Flamengo",
        awayTeam: "Palmeiras",
        score: { home: 1, away: 1 },
        minute: "45+2'",
        prediction: "Over 3.5 HT Corners",
        probability: 91
      }
  ];

  const currentMatches = matches.length > 0 ? matches : initialMatches;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      
      <main className="flex-1 ml-24 p-8 lg:p-12 overflow-x-hidden">
        <TopBar />
        
        <div className="max-w-7xl mx-auto">
          <StatsGrid />

          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-4">
               <div className="bg-accent/20 p-2 rounded-xl">
                  <Activity size={20} className={`text-accent ${isConnected ? 'animate-pulse' : ''}`} />
               </div>
               <div>
                  <h3 className="text-xl font-bold text-white tracking-tight">Live Opportunities</h3>
                  <p className="text-[10px] font-black text-white/20 uppercase tracking-widest">
                    {isConnected ? 'Connection: ACTIVE - 1,248 data points/sec' : 'Connection: OFFLINE - Using cached data'}
                  </p>
               </div>
            </div>
            
            <div className="flex gap-2">
               <button className="bg-secondary/50 hover:bg-secondary border border-white/5 px-4 py-2 rounded-xl text-xs font-bold transition-all">ALL LEAGUES</button>
               <button className="bg-primary hover:bg-primary-dark text-background px-4 py-2 rounded-xl text-xs font-black shadow-premium transition-all">
                 {isConnected ? 'SYNCING...' : 'SCAN NEW OPPORTUNITIES'}
               </button>
            </div>
          </div>

          {currentMatches.length > 0 ? (
            <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
              {currentMatches.map((match: any) => (
                <MatchCard key={match.id} {...match} />
              ))}
            </section>
          ) : (
            <div className="flex flex-col items-center justify-center p-20 border border-dashed border-white/5 rounded-3xl bg-secondary/20">
              <Activity size={48} className="text-white/10 mb-4 animate-pulse" />
              <p className="text-white/40 font-medium">No live matches found in the database.</p>
              <p className="text-white/20 text-xs mt-2">Engine is scanning for new opportunities...</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
