"use client";

import { useState } from 'react';
import { Calendar, Play, Loader2, CheckCircle2, XCircle } from 'lucide-react';

interface ScannerControlsProps {
  onScanComplete?: () => void;
}

export default function ScannerControls({ onScanComplete }: ScannerControlsProps) {
  const [selectedDate, setSelectedDate] = useState<string>('today');
  const [customDate, setCustomDate] = useState<string>('');
  const [isScanning, setIsScanning] = useState(false);
  const [scanStatus, setScanStatus] = useState<'idle' | 'running' | 'success' | 'error'>('idle');
  const [scanMessage, setScanMessage] = useState<string>('');

  const handleRunScanner = async () => {
    setIsScanning(true);
    setScanStatus('running');
    setScanMessage('Iniciando scanner...');

    try {
      const dateParam = selectedDate === 'custom' ? customDate : selectedDate;
      
      const response = await fetch('/api/scanner', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date: dateParam })
      });

      const data = await response.json();

      if (response.ok) {
        setScanStatus('success');
        setScanMessage(`✅ Scanner concluído! ${data.matchesProcessed || 0} jogos processados.`);
        setTimeout(() => {
          setScanStatus('idle');
          if (onScanComplete) onScanComplete();
        }, 3000);
      } else {
        throw new Error(data.error || 'Erro ao executar scanner');
      }
    } catch (error: any) {
      setScanStatus('error');
      setScanMessage(`❌ Erro: ${error.message}`);
      setTimeout(() => setScanStatus('idle'), 5000);
    } finally {
      setIsScanning(false);
    }
  };

  const getStatusIcon = () => {
    switch (scanStatus) {
      case 'running':
        return <Loader2 className="animate-spin" size={20} />;
      case 'success':
        return <CheckCircle2 size={20} className="text-emerald-500" />;
      case 'error':
        return <XCircle size={20} className="text-red-500" />;
      default:
        return <Play size={20} />;
    }
  };

  const isRunButtonDisabled = 
    isScanning || 
    (selectedDate === 'custom' && !customDate);

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 mb-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        {/* Date Selection */}
        <div className="flex items-center gap-3">
          <Calendar size={20} className="text-slate-400" />
          <span className="text-sm text-slate-400 font-medium">Scan Date:</span>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSelectedDate('today')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                selectedDate === 'today'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              Today
            </button>
            <button
              onClick={() => setSelectedDate('tomorrow')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                selectedDate === 'tomorrow'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              Tomorrow
            </button>
            <button
              onClick={() => setSelectedDate('custom')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                selectedDate === 'custom'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              Custom
            </button>
          </div>

          {selectedDate === 'custom' && (
            <input
              type="date"
              value={customDate}
              onChange={(e) => setCustomDate(e.target.value)}
              className="px-3 py-1.5 bg-slate-700 text-white text-sm rounded-md border border-slate-600 focus:outline-none focus:border-blue-500"
            />
          )}
        </div>

        {/* Run Scanner Button */}
        <button
          onClick={handleRunScanner}
          disabled={isRunButtonDisabled}
          className={`flex items-center gap-2 px-6 py-2.5 rounded-lg font-medium text-sm transition-all ${
            isRunButtonDisabled
              ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
              : 'bg-gradient-to-r from-blue-600 to-blue-500 text-white hover:from-blue-700 hover:to-blue-600 shadow-lg hover:shadow-blue-500/50'
          }`}
        >
          {getStatusIcon()}
          {isScanning ? 'Scanning...' : 'Run Scanner'}
        </button>
      </div>

      {/* Status Message */}
      {scanStatus !== 'idle' && (
        <div className={`mt-3 p-3 rounded-lg text-sm ${
          scanStatus === 'success' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
          scanStatus === 'error' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
          'bg-blue-500/10 text-blue-400 border border-blue-500/20'
        }`}>
          {scanMessage}
        </div>
      )}
    </div>
  );
}
