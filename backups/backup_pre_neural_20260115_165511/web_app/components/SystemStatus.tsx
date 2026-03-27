"use client";

import { useState, useEffect } from 'react';

interface StatusData {
  status: string;
  last_updated: string;
  live_matches: number;
}

export default function SystemStatus() {
  const [data, setData] = useState<StatusData | null>(null);
  const [scannerActive, setScannerActive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(false);

  const fetchStatus = async () => {
    try {
      // 1. Get System Data Status
      const res = await fetch('/api/system-status');
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
      
      // 2. Get Scanner Process Status
      const procRes = await fetch('/api/scanner/control');
      if (procRes.ok) {
         const procJson = await procRes.json();
         setScannerActive(procJson.active);
      }

    } catch (error) {
      console.error('Status fetch error:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleScanner = async () => {
    setToggling(true);
    try {
      const action = scannerActive ? 'stop' : 'start';
      const res = await fetch('/api/scanner/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action })
      });
      
      if (res.ok) {
        const json = await res.json();
        // Optimistic update or wait for next poll? Better wait or check immediately.
        // Let's check immediately
        setTimeout(fetchStatus, 1000); 
        setScannerActive(action === 'start');
      }
    } catch (error) {
      console.error('Toggle error:', error);
    } finally {
      setToggling(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000); // Check every 10s
    return () => clearInterval(interval);
  }, []);

  if (loading && !data) return null;

  // Calculate if status is "fresh" (< 5 mins)
  const lastUpdate = data ? new Date(data.last_updated) : new Date();
  const now = new Date();
  // Simple diff (assuming same timezone context or forgiving logic)
  const diffMinutes = data ? (now.getTime() - new Date(data.last_updated.replace(" ", "T")).getTime()) / 60000 : 0;
  
  let statusColor = "bg-emerald-500";
  let statusText = "Online";
  
  if (!data || data.status === 'error') {
    statusColor = "bg-red-500";
    statusText = "Error";
  } else if (diffMinutes > 10) {
    statusColor = "bg-yellow-500";
    statusText = "Stalled"; 
  } else if (!scannerActive && diffMinutes > 2) {
    statusColor = "bg-slate-500";
    statusText = "Offline";
  }

  return (
    <div className="flex items-center gap-4">
      {/* Scanner Toggle */}
      <div className="flex items-center gap-2 bg-slate-900/50 px-2 py-1 rounded-full border border-slate-800">
        <span className="text-[10px] uppercase font-bold text-slate-400 pl-1">Scanner</span>
        <button
          onClick={toggleScanner}
          disabled={toggling}
          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-900 ${
            scannerActive ? 'bg-blue-600' : 'bg-slate-700'
          }`}
        >
          <span
            className={`${
              scannerActive ? 'translate-x-4.5' : 'translate-x-0.5'
            } inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200`}
            style={{ transform: scannerActive ? 'translateX(18px)' : 'translateX(2px)' }}
          />
        </button>
      </div>

      {/* System Status Indicator */}
      <div className="flex items-center gap-3 px-3 py-1.5 bg-slate-900/50 rounded-full border border-slate-800">
        <div className="relative flex h-2.5 w-2.5">
          {scannerActive && <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${statusColor}`}></span>}
          <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${statusColor}`}></span>
        </div>
        <div className="flex flex-col leading-none">
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
            System {statusText}
          </span>
          {data && (
            <span className="text-[10px] text-slate-500 font-mono">
              Last: {data.last_updated.split(' ')[1] || data.last_updated}
            </span>
          )}
        </div>
        {data && data.live_matches > 0 && (
          <div className="ml-2 px-1.5 py-0.5 bg-red-500/10 border border-red-500/20 rounded text-[10px] font-bold text-red-400 animate-pulse">
            {data.live_matches} LIVE
          </div>
        )}
      </div>
    </div>
  );
}
