import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { BetSlipProvider } from './contexts/BetSlipContext';
import { BetSlip } from './components/BetSlip';
import { Bankroll } from './pages/Bankroll';
import { LiveScanner } from './pages/LiveScanner';

// Placeholders for now
const Dashboard = () => <div className="p-8"><h1 className="text-3xl font-bold">Dashboard</h1><p>Em construção...</p></div>;
const MachineLearning = () => <div className="p-8"><h1 className="text-3xl font-bold">Machine Learning</h1><p>Em construção...</p></div>;
const Config = () => <div className="p-8"><h1 className="text-3xl font-bold">Configurações</h1><p>Em construção...</p></div>;

function App() {
  return (
    <Router>
      <BetSlipProvider>
        <div className="flex bg-background min-h-screen text-foreground font-sans antialiased text-white">
          <Sidebar />
          <main className="flex-1 ml-64">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/scanner" element={<LiveScanner />} />
              <Route path="/ml" element={<MachineLearning />} />
              <Route path="/bankroll" element={<Bankroll />} />
              <Route path="/config" element={<Config />} />
            </Routes>
          </main>
          <BetSlip />
        </div>
      </BetSlipProvider>
    </Router>
  );
}

export default App;
