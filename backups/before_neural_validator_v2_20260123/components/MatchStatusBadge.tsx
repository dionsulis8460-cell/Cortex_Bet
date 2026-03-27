/**
 * Match Status Badge Component
 * Shows live indicator, finished status, or scheduled time
 */

interface MatchStatusBadgeProps {
  status?: string;
  matchMinute?: string;
  kickoff: string;
}

export default function MatchStatusBadge({ status, matchMinute, kickoff }: MatchStatusBadgeProps) {
  // Check if match data is stale (kickoff passed but still showing as scheduled)
  const isStale = () => {
    if (status && status !== 'notstarted' && status !== 'scheduled') return false;
    
    try {
      const [hours, minutes] = kickoff.split(':').map(Number);
      const kickoffTime = new Date();
      kickoffTime.setHours(hours, minutes, 0, 0);
      
      const now = new Date();
      
      // CRITICAL: Only check staleness for matches TODAY
      // If kickoff is in the future (tomorrow+), don't mark as stale
      if (kickoffTime.getTime() > now.getTime()) {
        return false; // Future match, not stale
      }
      
      const timeDiff = now.getTime() - kickoffTime.getTime();
      const minutesPassed = timeDiff / (1000 * 60);
      
      // If more than 10 minutes past kickoff and still notstarted, data is stale
      return minutesPassed > 10;
    } catch {
      return false;
    }
  };
  
  // Show stale data warning
  if (isStale()) {
    return (
      <div className="flex items-center gap-2 mb-2">
        <span className="relative flex h-3 w-3">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-3 w-3 bg-orange-500"></span>
        </span>
        <span className="text-xs font-semibold text-orange-500 uppercase tracking-wider">Dados Desatualizados</span>
        <span className="text-xs text-slate-600">• {kickoff}</span>
      </div>
    );
  }
  
  // Live match
  if (status === 'inprogress') {
    return (
      <div className="flex items-center gap-2 mb-2">
        <span className="relative flex h-3 w-3">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
        </span>
        <span className="text-xs font-bold text-red-500 uppercase tracking-wider">Live</span>
        {matchMinute && (
          <span className="text-xs font-mono text-red-400 font-semibold">{matchMinute}</span>
        )}
        <span className="text-xs text-slate-500">• {kickoff}</span>
      </div>
    );
  }
  
  // Finished match
  if (status === 'finished') {
    return (
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Finalizado</span>
        <span className="text-xs text-slate-600">• {kickoff}</span>
      </div>
    );
  }
  
  // Scheduled/Not started
  return (
    <div className="mb-2">
      <span className="text-xs text-slate-400">⏱️ {kickoff}</span>
    </div>
  );
}
