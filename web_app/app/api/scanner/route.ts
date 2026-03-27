import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = 'http://127.0.0.1:8000';

export async function POST(request: NextRequest) {
  try {
    const { date } = await request.json();

    if (!date) {
      return NextResponse.json(
        { error: 'Date parameter is required' },
        { status: 400 }
      );
    }

    const response = await fetch(`${API_BASE_URL}/api/scanner`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date }),
      cache: 'no-store',
    });

    const payload = await response.json();
    if (!response.ok) {
      const errorMessage = payload?.detail || payload?.error || 'Scanner execution failed';
      return NextResponse.json({ error: errorMessage }, { status: response.status });
    }

    return NextResponse.json({
      success: true,
      message: 'Scanner completed successfully',
      matchesProcessed: payload.matchesProcessed || payload.matches_processed || 0,
      output: payload.output || ''
    });

  } catch (error: any) {
    console.error('Scanner API error:', error);
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}
