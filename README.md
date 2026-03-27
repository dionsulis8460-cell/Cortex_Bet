# Cortex Bet V3/V4 Pro

Cortex Bet is an advanced AI-powered soccer prediction system specializing in corner markets. It combines real-time data from SofaScore, professional-grade machine learning models, and complex statistical analysis (Monte Carlo simulations) to provide high-probability betting opportunities.

## Key Features

- **Real-time Scanning**: Monitors live and scheduled matches for high-value opportunities.
- **Cyborg V1.0 (Neural-Hybrid)**: New prediction engine where Deep Learning guides Statistical Distributions (Neural Point Process).
- **AI V6 Pro (V2.1 Calibrated)**: Advanced ML model utilizing "Temperature Scaling" for perfectly calibrated win probabilities.
- **Neural Fair Price**: A second opinion engine (Neural Challenger) that audits odd prices.
- **Monte Carlo Engine**: Simulates match events 10,000 times based on Neural Parameters.
- **Dynamic Bankroll Management**: Real-time tracking of ROI, win rates, and RPS (Ranked Probability Score).
- **Match Insights**: Detailed analysis including recent form, H2H, and tactical momentum graphs.

## Architecture

- **Frontend**: Next.js (React) + Tailwind CSS + Lucide Icons.
- **Backend API**: Next.js API Routes + Python (subprocess).
- **Core Engine**: Python 3.10+ (Hybrid: XGBoost + MLPRegressor).
- **Database**: SQLite (Highly optimized for time-series match data).
- **Scraper**: Playwright-based SofaScore scraper with network interception.

## Getting Started

1. **Setup**: Run `setup_windows.bat` to install dependencies and configure the environment.
2. **Scanner**: Run `python scripts/run_scanner.py` to start the AI analysis for today's games.
3. **Web App**: Run `npm run dev` in the `web_app` directory to open the dashboard.
4. **Train AI (Weekly)**:
   - Main Model: `python scripts/train_model.py`
   - Neural Brain: `python src/ml/train_neural.py` (Required for Cyborg Engine)
5. **Updates**: Run `python scripts/update_results.py` to sync results and calculate performance.

## Documentation

- [README_ML.md](file:///c:/Users/OEM/Desktop/Cortex_Bet/Cortex_Bet/README_ML.md): Deep dive into the machine learning and statistical layers.
- [Roadmap](file:///c:/Users/OEM/Desktop/Cortex_Bet/Cortex_Bet/CORTEX_BET_REVISION_ROADMAP.md): Project evolution and future plans.
