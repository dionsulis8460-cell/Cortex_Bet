import sys
import os
from pathlib import Path
from typing import Optional

# Add project root to path to allow imports
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT_DIR))

# Also add web_app to path to easily import dashboard_data
WEB_APP_DIR = ROOT_DIR / "web_app"
sys.path.append(str(WEB_APP_DIR))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Try to import Provider
try:
    from web_app.lib.dashboard_data import DashboardDataProvider
    print("Successfully imported DashboardDataProvider")
except ImportError as e:
    print(f"Error importing DashboardDataProvider: {e}")
    # Fallback to try finding it via direct path if needed, but sys.path above should work.
    # If the module is strictly inside lib, we might need: from lib.dashboard_data ...
    try:
        sys.path.append(str(WEB_APP_DIR / "lib"))
        from dashboard_data import DashboardDataProvider
        print("Successfully imported DashboardDataProvider from lib")
    except ImportError as e2:
         print(f"Critical Error importing DashboardDataProvider: {e2}")
         raise e2


from contextlib import asynccontextmanager

# Global Provider Instance
provider = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global provider
    print("Initializing Cortex Bet Data Provider...")
    try:
        from web_app.lib.dashboard_data import DashboardDataProvider
        # Initialize
        provider = DashboardDataProvider() 
        print("Data Provider Ready! Models Loaded.")
    except Exception as e:
        print(f"Failed to initialize provider: {e}")
        import traceback
        traceback.print_exc()
    
    yield
    # Cleanup code can go here if needed

app = FastAPI(title="Cortex Bet API", version="1.0.0", lifespan=lifespan)

# Enable CORS for Next.js (Port 3000) and Streamlit (8501)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "provider_loaded": provider is not None}

@app.get("/api/predictions")
async def get_predictions(
    date: str = 'today',
    league: str = 'all',
    status: str = 'all',
    top7_only: bool = False,
    sort_by: str = 'confidence'
):
    if not provider:
         raise HTTPException(status_code=503, detail="Provider not initialized")
    
    try:
        # The provider logic is synchronous, identifying N+1 bottleneck
        # In a real async microservice, we'd run this in a threadpool if it blocks,
        # but for now, just removing the process-spawn overhead is the big win.
        data = provider.get_predictions_with_reasoning(
            date_str=date,
            league=league,
            status=status,
            top7_only=top7_only,
            sort_by=sort_by
        )
        return data
    except Exception as e:
        print(f"Error fetching predictions: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Run slightly different config for direct execution
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True)
