import axios from 'axios';

// Detecta se está rodando em desenvolvimento (Vite) ou produção
const isDev = import.meta.env.DEV;
const BASE_URL = isDev ? 'http://127.0.0.1:5000' : '';

export const api = axios.create({
    baseURL: BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export interface BetItem {
    match_id: number;
    selection: string;
    odds: number;
    prediction_id?: number;
    match_name?: string;
}

export interface Bet {
    stake: number;
    bet_type: 'SINGLE' | 'MULTIPLE';
    items: BetItem[];
}

export const placeBet = async (bet: Bet) => {
    const response = await api.post('/api/bets/place', bet);
    return response.data;
};

export const getHistory = async () => {
    const response = await api.get('/api/bets/history');
    return response.data;
};

export const getDashboard = async () => {
    const response = await api.get('/api/bets/dashboard');
    return response.data;
};
