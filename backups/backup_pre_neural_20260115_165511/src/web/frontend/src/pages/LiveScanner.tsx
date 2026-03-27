import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { MatchCard } from '../components/MatchCard';
import { RefreshCw, Search } from 'lucide-react';

export function LiveScanner() {
    const [matches, setMatches] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('');

    const fetchMatches = async () => {
        setLoading(true);
        try {
            const res = await api.get('/api/analyses');
            // Normalize data if necessary
            setMatches(res.data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMatches();
    }, []);

    const filteredMatches = matches.filter(m =>
        m.home_team_name.toLowerCase().includes(filter.toLowerCase()) ||
        m.away_team_name.toLowerCase().includes(filter.toLowerCase()) ||
        m.tournament_name.toLowerCase().includes(filter.toLowerCase())
    );

    return (
        <div className="p-8 space-y-6">
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Live Scanner</h2>
                    <p className="text-muted-foreground">Oportunidades de Valor em Tempo Real</p>
                </div>

                <div className="flex items-center gap-2">
                    <div className="relative">
                        <Search className="absolute left-3 top-2.5 text-muted-foreground w-4 h-4" />
                        <input
                            type="text"
                            placeholder="Buscar time ou liga..."
                            value={filter}
                            onChange={(e) => setFilter(e.target.value)}
                            className="bg-card border border-border rounded-full pl-9 pr-4 py-2 text-sm w-64 focus:ring-1 focus:ring-blue-500 outline-none"
                        />
                    </div>
                    <button
                        onClick={fetchMatches}
                        className="bg-primary text-primary-foreground p-2 rounded-full hover:opacity-90 transition-opacity"
                    >
                        <RefreshCw className={loading ? "animate-spin" : ""} size={20} />
                    </button>
                </div>
            </header>

            {loading && matches.length === 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {[1, 2, 3, 4, 5, 6].map(i => (
                        <div key={i} className="h-40 bg-card/50 animate-pulse rounded-xl" />
                    ))}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredMatches.map((match) => (
                        <MatchCard key={match.match_id} match={match} />
                    ))}
                </div>
            )}

            {!loading && filteredMatches.length === 0 && (
                <div className="text-center py-20 text-muted-foreground">
                    <p>Nenhuma oportunidade encontrada no momento.</p>
                </div>
            )}
        </div>
    );
}
