
"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface LabsContextType {
  isShadowMode: boolean;
  toggleShadowMode: () => void;
}

const LabsContext = createContext<LabsContextType | undefined>(undefined);

export function LabsProvider({ children }: { children: ReactNode }) {
  const [isShadowMode, setIsShadowMode] = useState(false);

  // Persist preference
  useEffect(() => {
    const saved = localStorage.getItem('labs_shadow_mode');
    if (saved) {
        setIsShadowMode(saved === 'true');
    }
  }, []);

  const toggleShadowMode = () => {
    const newVal = !isShadowMode;
    setIsShadowMode(newVal);
    localStorage.setItem('labs_shadow_mode', String(newVal));
  };

  return (
    <LabsContext.Provider value={{ isShadowMode, toggleShadowMode }}>
      {children}
    </LabsContext.Provider>
  );
}

export function useLabs() {
  const context = useContext(LabsContext);
  if (context === undefined) {
    throw new Error('useLabs must be used within a LabsProvider');
  }
  return context;
}
