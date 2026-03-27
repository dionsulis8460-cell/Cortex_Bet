"use client";

import { useEffect, useState } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  AreaChart, Area 
} from 'recharts';
import { Calendar, Activity } from 'lucide-react';
import PerformanceMetrics from './PerformanceMetrics';
import Top7Tracker from './Top7Tracker';

export default function AIPerformance() {
  const [performanceData, setPerformanceData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState({ from: '', to: '' });

  useEffect(() => {
    fetchPerformanceData();
  }, [dateRange]);

  const fetchPerformanceData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (dateRange.from) params.append('from_date', dateRange.from);
      if (dateRange.to) params.append('to_date', dateRange.to);

      const res = await fetch(`/api/performance?${params.toString()}`);
      const result = await res.json();
      
      console.log('Performance API response:', result); // Debug log
      
      if (result.success) {
        setPerformanceData(result.data);
      } else {
        console.error('API returned error:', result.error);
        setPerformanceData({ error: result.error });
      }
    } catch (err: any) {
      console.error('Failed to fetch performance data:', err);
      setPerformanceData({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent"></div>
      </div>
    );
  }

  if (!performanceData || performanceData.error) {
    return (
      <div className="text-center py-20">
        <p className="text-red-400 text-lg mb-2">Failed to load performance data</p>
        {performanceData?.error && (
          <p className="text-slate-400 text-sm font-mono bg-slate-900 p-4 rounded-lg inline-block">
            Error: {performanceData.error}
          </p>
        )}
        <p className="text-slate-500 text-sm mt-4">
          Check console for more details or try refreshing the page
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-10">
      {/* Date Range Filter */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
        <div className="flex items-center gap-4">
          <Calendar size={20} className="text-slate-400" />
          <span className="text-sm text-slate-400 font-medium">Date Range:</span>
          <input
            type="date"
            value={dateRange.from}
            onChange={(e) => setDateRange({ ...dateRange, from: e.target.value })}
            className="px-3 py-1.5 bg-slate-700 text-white text-sm rounded-md border border-slate-600 focus:outline-none focus:border-blue-500"
            placeholder="From"
          />
          <span className="text-slate-400">to</span>
          <input
            type="date"
            value={dateRange.to}
            onChange={(e) => setDateRange({ ...dateRange, to: e.target.value })}
            className="px-3 py-1.5 bg-slate-700 text-white text-sm rounded-md border border-slate-600 focus:outline-none focus:border-blue-500"
            placeholder="To"
          />
          {(dateRange.from || dateRange.to) && (
            <button
              onClick={() => setDateRange({ from: '', to: '' })}
              className="px-3 py-1.5 text-sm text-blue-400 hover:text-blue-300"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Performance Summary */}
      <div>
        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <Activity className="text-blue-400" size={20} />
          General Model Performance (Top 7 Per Match)
        </h3>
        <PerformanceMetrics metrics={performanceData.global_metrics} />
      </div>

      {/* Win Rate Evolution Chart */}
      <div className="bg-slate-800 p-4 md:p-6 rounded-xl border border-slate-700">
        <div className="mb-4">
          <h3 className="text-lg font-bold text-white mb-2">📈 Win Rate Evolution</h3>
          <p className="text-xs md:text-sm text-slate-400">
            Based on <span className="text-blue-400 font-medium">Top 7 predictions</span> from each scanner run. 
            Shows performance of <span className="text-emerald-400 font-medium">CORTEX V6 Pro (V2.1_CALIBRATED)</span> model only.
          </p>
          <p className="text-xs text-slate-500 mt-1">
            💡 Note: Predictions are created by Scanner (inference time), not affected by future model training.
          </p>
        </div>
        <div className="h-[250px] md:h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={performanceData.win_rate_by_date}>
              <defs>
                <linearGradient id="colorWinRate" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis 
                dataKey="date" 
                stroke="#94a3b8" 
                fontSize={12}
                tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              />
              <YAxis stroke="#94a3b8" fontSize={12} domain={[0, 100]} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                itemStyle={{ color: '#f1f5f9' }}
                formatter={(value: any) => [`${value}%`, 'Win Rate']}
              />
              <Area 
                type="monotone" 
                dataKey="win_rate" 
                name="Win Rate (%)" 
                stroke="#10b981" 
                fillOpacity={1} 
                fill="url(#colorWinRate)" 
                strokeWidth={3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top 7 Predictions Tracker */}
      <div>
        <h3 className="text-lg font-bold text-white mb-4">🎯 Top 7 Predictions Tracker</h3>
        <Top7Tracker predictionsByDate={performanceData.top7_by_date} />
      </div>

      {/* Market Performance Table */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden overflow-x-auto">
        <div className="p-6 border-b border-slate-700">
          <h3 className="text-lg font-bold text-white">📊 Performance by Market</h3>
        </div>
        <table className="w-full text-left">
          <thead className="bg-slate-900/50 text-slate-400 text-sm">
            <tr>
              <th className="px-6 py-4 font-medium">Market</th>
              <th className="px-6 py-4 font-medium">Win Rate</th>
              <th className="px-6 py-4 font-medium">Avg Confidence</th>
              <th className="px-6 py-4 font-medium">ROI Potential</th>
              <th className="px-6 py-4 font-medium text-right">Total Bets</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {performanceData.performance_by_market.map((market: any, i: number) => (
              <tr key={i} className="text-sm hover:bg-slate-800/50">
                <td className="px-6 py-4 text-white font-medium">{market.market}</td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <span className={`font-bold ${market.win_rate >= 70 ? 'text-emerald-400' : market.win_rate >= 60 ? 'text-blue-400' : 'text-slate-400'}`}>
                      {market.win_rate}%
                    </span>
                    <div className="w-20 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full ${market.win_rate >= 70 ? 'bg-emerald-500' : market.win_rate >= 60 ? 'bg-blue-500' : 'bg-slate-500'}`}
                        style={{ width: `${market.win_rate}%` }}
                      />
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 text-slate-300">{market.avg_confidence}%</td>
                <td className={`px-6 py-4 font-bold ${market.roi_potential >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {market.roi_potential >= 0 ? '+' : ''}{market.roi_potential}%
                </td>
                <td className="px-6 py-4 text-slate-400 text-right">{market.total_bets}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
