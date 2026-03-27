import { useEffect, useState } from 'react';
import { getHistory, getDashboard } from '../lib/api';
import { Card } from '../components/ui/card'; // I'll create a basic Card later or use div
import { format } from 'date-fns';
import { CheckCircle2, XCircle, Clock, PieChart, TrendingUp, DollarSign } from 'lucide-react';

export function Bankroll() {
    const [history, setHistory] = useState<any[]>([]);
    const [kpi, setKpi] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function load() {
            try {
                const [histData, kpiData] = await Promise.all([getHistory(), getDashboard()]);
                setHistory(histData);
                setKpi(kpiData);
            } catch (e) {
                console.error("Failed to load bankroll data", e);
            } finally {
                setLoading(false);
            }
        }
        load();
    }, []);

    if (loading) return <div className="p-8">Loading...</div>;

    return (
        <div className="space-y-8 p-8 animate-in fade-in duration-500">
            <header>
                <h2 className="text-3xl font-bold tracking-tight">Bankroll Management</h2>
                <p className="text-muted-foreground">Rastreamento de apostas reais e evolução de capital.</p>
            </header>

            {/* KPI Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <KpiCard title="Banca Atual" value={`R$ ${kpi?.current_bankroll?.toFixed(2)}`} icon={DollarSign} color="text-green-500" />
                <KpiCard title="Lucro/Prejuízo" value={`R$ ${kpi?.profit?.toFixed(2)}`} icon={TrendingUp} color={kpi?.profit >= 0 ? "text-green-500" : "text-red-500"} />
                <KpiCard title="ROI" value={`${kpi?.roi?.toFixed(1)}%`} icon={PieChart} color="text-blue-500" />
                <KpiCard title="Winrate" value={`${kpi?.winrate?.toFixed(1)}%`} icon={Activity} color="text-yellow-500" />
            </div>

            {/* Bets List */}
            <div className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
                <div className="p-6 border-b border-border">
                    <h3 className="text-lg font-semibold">Histórico de Apostas</h3>
                </div>
                <div className="divide-y divide-border">
                    {history.map((bet) => (
                        <div key={bet.id} className="p-6 hover:bg-white/5 transition-colors">
                            <div className="flex items-start justify-between">
                                <div className="space-y-1">
                                    <div className="flex items-center gap-2">
                                        <span className={`px-2 py-1 rounded text-xs font-bold ${bet.status === 'WON' ? 'bg-green-500/20 text-green-500' :
                                                bet.status === 'LOST' ? 'bg-red-500/20 text-red-500' :
                                                    'bg-yellow-500/20 text-yellow-500'
                                            }`}>
                                            {bet.status}
                                        </span>
                                        <span className="text-sm text-muted-foreground font-medium border border-border px-2 rounded">
                                            {bet.bet_type}
                                        </span>
                                        <span className="text-xs text-muted-foreground">
                                            {format(new Date(bet.created_at), 'dd/MM/yyyy HH:mm')}
                                        </span>
                                    </div>

                                    <div className="mt-2 space-y-2">
                                        {bet.items.map((item: any, idx: number) => (
                                            <div key={idx} className="flex items-center gap-3 text-sm">
                                                {item.status === 'WON' && <CheckCircle2 size={16} className="text-green-500" />}
                                                {item.status === 'LOST' && <XCircle size={16} className="text-red-500" />}
                                                {item.status === 'PENDING' && <Clock size={16} className="text-yellow-500" />}
                                                <span className="font-medium text-foreground">{item.match_name}</span>
                                                <span className="text-muted-foreground">•</span>
                                                <span className="text-blue-400">{item.selection}</span>
                                                <span className="text-muted-foreground">@ {item.odds.toFixed(2)}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="text-right">
                                    <div className="text-sm text-muted-foreground">Stake</div>
                                    <div className="font-medium">R$ {bet.stake.toFixed(2)}</div>
                                    <div className="mt-2 text-sm text-muted-foreground">Pot. Return</div>
                                    <div className={`font-bold ${bet.status === 'WON' ? 'text-green-500' : ''}`}>
                                        R$ {bet.potential_return.toFixed(2)}
                                    </div>
                                    <div className="text-xs text-muted-foreground mt-1">
                                        Odd Total: {bet.total_odds.toFixed(2)}
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                    {history.length === 0 && (
                        <div className="p-12 text-center text-muted-foreground">
                            Nenhuma aposta registrada ainda. Vá para o Scanner!
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function KpiCard({ title, value, icon: Icon, color }: any) {
    return (
        <div className="bg-card p-6 rounded-xl border border-border shadow-sm flex items-center justify-between">
            <div>
                <p className="text-sm font-medium text-muted-foreground">{title}</p>
                <h3 className="text-2xl font-bold mt-1">{value}</h3>
            </div>
            <div className={`p-3 rounded-full bg-white/5 ${color}`}>
                <Icon size={24} />
            </div>
        </div>
    );
}

import { Activity } from 'lucide-react';
