"use client";

import { useEffect } from 'react';

export default function AutoValidator() {
  useEffect(() => {
    // Run validation every 5 minutes
    const interval = setInterval(async () => {
      try {
        const res = await fetch('/api/validate-bets', { method: 'POST' });
        const data = await res.json();
        
        if (data.success && data.validated_count > 0) {
          console.log(`✅ Auto-validated ${data.validated_count} bets`);
          
          // Optional: Show notification to user
          // You could use a toast library here
        }
      } catch (err) {
        console.error('Auto-validation failed:', err);
      }
    }, 5 * 60 * 1000); // 5 minutes

    // Cleanup on unmount
    return () => clearInterval(interval);
  }, []);

  return null; // This component doesn't render anything
}
