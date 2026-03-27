import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = 'http://127.0.0.1:8000';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const limit = searchParams.get('limit') || '50';

    const response = await fetch(`${API_BASE_URL}/api/feed?limit=${encodeURIComponent(limit)}`, {
      cache: 'no-store',
    });
    const payload = await response.json();

    if (!response.ok) {
      const errorMessage = payload?.detail || payload?.error || 'Failed to load feed';
      return NextResponse.json({ success: false, error: errorMessage }, { status: response.status });
    }

    return NextResponse.json({ success: true, data: payload });

  } catch (error: any) {
    console.error('Feed GET error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
