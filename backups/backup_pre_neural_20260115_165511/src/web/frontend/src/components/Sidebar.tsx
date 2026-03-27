import { Home, LineChart, Wallet, Settings, Activity } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '../lib/utils';

const menuItems = [
    { icon: Home, label: 'Dashboard', path: '/' },
    { icon: Activity, label: 'Live Scanner', path: '/scanner' },
    { icon: LineChart, label: 'Machine Learning', path: '/ml' },
    { icon: Wallet, label: 'Bankroll', path: '/bankroll' },
    { icon: Settings, label: 'Configurações', path: '/config' },
];

export function Sidebar() {
    const location = useLocation();

    return (
        <div className="h-screen w-64 bg-card border-r border-border flex flex-col fixed left-0 top-0">
            <div className="p-6">
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
                    Betting Engine
                </h1>
                <p className="text-xs text-muted-foreground mt-1">Professional Analytics</p>
            </div>

            <nav className="flex-1 px-4 space-y-2">
                {menuItems.map((item) => {
                    const isActive = location.pathname === item.path;
                    return (
                        <Link
                            key={item.path}
                            to={item.path}
                            className={cn(
                                "flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200",
                                isActive
                                    ? "bg-primary/10 text-blue-400"
                                    : "text-muted-foreground hover:bg-white/5 hover:text-white"
                            )}
                        >
                            <item.icon size={20} />
                            <span className="font-medium">{item.label}</span>
                        </Link>
                    );
                })}
            </nav>

            <div className="p-4 border-t border-border">
                <div className="flex items-center gap-2 px-4 py-2 text-xs text-muted-foreground">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    System Online
                </div>
            </div>
        </div>
    );
}
