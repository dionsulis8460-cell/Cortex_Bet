import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = 'http://127.0.0.1:8000';

// GET - Fetch Leaderboard
export async function GET(request: NextRequest) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/leaderboard`, { cache: 'no-store' });
    const payload = await response.json();

    if (!response.ok) {
      const errorMessage = payload?.detail || payload?.error || 'Failed to load leaderboard';
      return NextResponse.json({ success: false, error: errorMessage }, { status: response.status });
    }

    return NextResponse.json({ success: true, data: payload });

  } catch (error: any) {
    console.error('Leaderboard GET error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
