import { useBetSlip } from '../contexts/BetSlipContext';
import { X, Trash2, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { placeBet } from '../lib/api';
import { cn } from '../lib/utils';

export function BetSlip() {
    const { items, isOpen, toggleSlip, removeFromSlip, clearSlip } = useBetSlip();
    const [stake, setStake] = useState<string>('');
    const [isMultiple, setIsMultiple] = useState(false);
    const [loading, setLoading] = useState(false);

    if (!isOpen) {
        return (
            <button
                onClick={toggleSlip}
                className="fixed bottom-6 right-6 bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-500 transition-all z-50 flex items-center gap-2"
            >
                <div className="bg-white text-blue-600 text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center">
                    {items.length}
                </div>
                <span className="font-bold">Boletim</span>
            </button>
        );
    }

    const totalOdds = items.reduce((acc, item) => acc * item.odds, 1);
    const numericStake = parseFloat(stake) || 0;
    const possibleWin = numericStake * (isMultiple ? totalOdds : 0); // Logic simplification for MVP

    const handlePlaceBet = async () => {
        if (numericStake <= 0) return;
        setLoading(true);
        try {
            if (isMultiple) {
                await placeBet({
                    stake: numericStake,
                    bet_type: 'MULTIPLE',
                    items
                });
            } else {
                // Place individual bets
                for (const item of items) {
                    await placeBet({
                        stake: numericStake, // Assumption: Stake is per bet for Single
                        bet_type: 'SINGLE',
                        items: [item]
                    });
                }
            }
            clearSlip();
            toggleSlip();
            alert('Aposta realizada com sucesso!');
        } catch (e) {
            alert('Erro ao realizar aposta');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed top-0 right-0 h-screen w-80 bg-card border-l border-border shadow-2xl z-50 flex flex-col animate-in slide-in-from-right duration-300">
            <div className="p-4 border-b border-border flex items-center justify-between bg-zinc-900">
                <div className="flex items-center gap-2">
                    <div className="bg-blue-600 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white">
                        {items.length}
                    </div>
                    <h3 className="font-bold">Boletim de Apostas</h3>
                </div>
                <button onClick={toggleSlip} className="text-muted-foreground hover:text-white">
                    <ChevronRight />
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {items.length === 0 ? (
                    <div className="text-center text-muted-foreground mt-10">
                        <p>Seu boletim está vazio.</p>
                        <p className="text-sm mt-2">Clique nas odds para adicionar.</p>
                    </div>
                ) : (
                    items.map((item) => (
                        <div key={item.id} className="bg-white/5 p-3 rounded-lg border border-white/10 relative group">
                            <button
                                onClick={() => removeFromSlip(item.id)}
                                className="absolute top-2 right-2 text-muted-foreground hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                                <X size={14} />
                            </button>
                            <div className="text-xs text-blue-400 font-bold mb-1">{item.selection}</div>
                            <div className="text-sm font-medium mb-1 line-clamp-1">{item.match_name}</div>
                            <div className="flex justify-between items-center mt-2">
                                <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded">
                                    Odd: {item.odds.toFixed(2)}
                                </span>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {items.length > 0 && (
                <div className="p-4 bg-zinc-900 border-t border-border space-y-4">

                    {items.length > 1 && (
                        <div className="flex items-center gap-2 mb-2">
                            <input
                                type="checkbox"
                                id="multiple"
                                checked={isMultiple}
                                onChange={(e) => setIsMultiple(e.target.checked)}
                                className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500"
                            />
                            <label htmlFor="multiple" className="text-sm font-medium cursor-pointer select-none">
                                Múltipla (Accumulator)
                                <span className="block text-xs text-muted-foreground">
                                    Odd Total: <span className="text-green-400">{totalOdds.toFixed(2)}</span>
                                </span>
                            </label>
                        </div>
                    )}

                    <div className="space-y-1">
                        <label className="text-xs uppercase font-bold text-muted-foreground">Valor da Aposta (Stake)</label>
                        <div className="relative">
                            <span className="absolute left-3 top-2.5 text-muted-foreground">R$</span>
                            <input
                                type="number"
                                value={stake}
                                onChange={(e) => setStake(e.target.value)}
                                className="w-full bg-black/20 border border-white/10 rounded-lg py-2 pl-9 pr-4 focus:outline-none focus:border-blue-500 transition-colors"
                                placeholder="0.00"
                            />
                        </div>
                    </div>

                    <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Retorno Potencial:</span>
                        <span className="font-bold text-green-500">
                            R$ {isMultiple ? possibleWin.toFixed(2) : ((items.length * numericStake).toFixed(2) + "*")}
                        </span>
                    </div>

                    <div className="flex gap-2">
                        <button
                            onClick={clearSlip}
                            className="p-3 rounded-lg border border-white/10 text-muted-foreground hover:bg-white/5 hover:text-white transition-colors"
                        >
                            <Trash2 size={20} />
                        </button>
                        <button
                            onClick={handlePlaceBet}
                            disabled={loading || numericStake <= 0}
                            className="flex-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-3 rounded-lg transition-all shadow-lg shadow-blue-900/20"
                        >
                            {loading ? 'Processando...' : 'Confirmar Aposta'}
                        </button>
                    </div>
                    {!isMultiple && items.length > 1 && (
                        <p className="text-[10px] text-center text-muted-foreground">*Calculado como soma de apostas simples</p>
                    )}
                </div>
            )}
        </div>
    );
}
