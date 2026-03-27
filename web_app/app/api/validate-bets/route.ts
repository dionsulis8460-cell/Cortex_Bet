import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = 'http://127.0.0.1:8000';

export async function POST(request: NextRequest) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/validate-bets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store',
    });

    const payload = await response.json();
    if (!response.ok) {
      const errorMessage = payload?.detail || payload?.error || 'Validation failed';
      return NextResponse.json({ success: false, error: errorMessage }, { status: response.status });
    }

    return NextResponse.json({
      success: true,
      validated_count: payload.validated_count || 0,
      output: payload.output || ''
    });

  } catch (error: any) {
    console.error('Validator API error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
