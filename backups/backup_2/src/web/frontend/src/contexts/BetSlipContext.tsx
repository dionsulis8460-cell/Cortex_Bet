import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { BetItem } from '../lib/api';

interface BetSlipItem extends BetItem {
    id: string; // Unique ID for keying (match_id + selection usually)
}

interface BetSlipContextType {
    items: BetSlipItem[];
    isOpen: boolean;
    addToSlip: (item: Omit<BetSlipItem, 'id'>) => void;
    removeFromSlip: (id: string) => void;
    clearSlip: () => void;
    toggleSlip: () => void;
}

const BetSlipContext = createContext<BetSlipContextType | undefined>(undefined);

export const BetSlipProvider = ({ children }: { children: ReactNode }) => {
    const [items, setItems] = useState<BetSlipItem[]>([]);
    const [isOpen, setIsOpen] = useState(false);

    // Load from local storage on mount
    useEffect(() => {
        const saved = localStorage.getItem('betSlip');
        if (saved) setItems(JSON.parse(saved));
    }, []);

    // Save to local storage on change
    useEffect(() => {
        localStorage.setItem('betSlip', JSON.stringify(items));
    }, [items]);

    const addToSlip = (item: Omit<BetSlipItem, 'id'>) => {
        const id = `${item.match_id}-${item.selection}`;
        if (items.find(i => i.id === id)) return; // Prevent duplicates

        setItems(prev => [...prev, { ...item, id }]);
        setIsOpen(true); // Auto open
    };

    const removeFromSlip = (id: string) => {
        setItems(prev => prev.filter(i => i.id !== id));
    };

    const clearSlip = () => setItems([]);
    const toggleSlip = () => setIsOpen(prev => !prev);

    return (
        <BetSlipContext.Provider value={{ items, isOpen, addToSlip, removeFromSlip, clearSlip, toggleSlip }}>
            {children}
        </BetSlipContext.Provider>
    );
};

export const useBetSlip = () => {
    const context = useContext(BetSlipContext);
    if (!context) throw new Error('useBetSlip must be used within a BetSlipProvider');
    return context;
};
