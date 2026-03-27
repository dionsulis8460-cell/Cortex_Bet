from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import asyncio
import json
from src.application.analysis_service import MatchAnalysisService
from src.infrastructure.persistence.sqlite_repository import SQLiteMatchRepository
from src.database.db_manager import DBManager

app = FastAPI(title="Cortex Bet API", version="1.0.0")

# Dependency Injection Setup
db_manager = DBManager()
repository = SQLiteMatchRepository(db_manager)
analysis_service = MatchAnalysisService(repository=repository, ml_model=None) # ML model to be integrated

@app.get("/")
async def root():
    return {"status": "online", "message": "Cortex Bet API V1.0 - PhD Edition"}

@app.get("/scanner/live")
async def scanner_live():
    """Triggers a live scan across monitored leagues."""
    # This would typically be a background task, but for now returned as direct call
    from src.infrastructure.scrapers.sofascore_adapter import SofaScoreScraperAdapter
    scraper = SofaScoreScraperAdapter()
    matches = await scraper.get_live_matches()
    return {"count": len(matches), "matches": matches}

@app.get("/matches/history")
async def get_match_history():
    """Returns historical match data for analysis."""
    # Logic to fetch from repository
    return {"message": "Endpoint in development - will return historical data"}

@app.post("/matches/{match_id}/analyze")
async def analyze_match(match_id: int):
    """Triggers a PhD-level analysis for a specific match."""
    result = await analysis_service.analyze_match(match_id)
    if not result:
        raise HTTPException(status_code=404, detail="Match not found or analysis failed")
    return result

# --- REAL-TIME LIVE DATA (WebSockets) ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

async def broadcast_live_matches():
    """Background task to poll matches and broadcast updates."""
    while True:
        try:
            matches = await repository.get_live_matches()
            if matches:
                data = {
                    "type": "matches_update",
                    "matches": [
                        {
                            "id": m.id,
                            "league": m.home_team.league,
                            "homeTeam": m.home_team.name,
                            "awayTeam": m.away_team.name,
                            "score": m.current_score or {"home": 0, "away": 0},
                            "minute": "Live", # Dynamic minute logic needed
                            "prediction": "Analyzing...",
                            "probability": 75
                        } for m in matches
                    ]
                }
                await manager.broadcast(json.dumps(data))
        except Exception as e:
            print(f"Broadcast error: {e}")
        await asyncio.sleep(10)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_live_matches())

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
