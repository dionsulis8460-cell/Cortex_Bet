import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = 'http://127.0.0.1:8000';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const fromDate = searchParams.get('from_date');
    const toDate = searchParams.get('to_date');

    const query = new URLSearchParams();
    if (fromDate) query.set('from_date', fromDate);
    if (toDate) query.set('to_date', toDate);

    const response = await fetch(`${API_BASE_URL}/api/performance?${query.toString()}`, {
      cache: 'no-store',
    });
    const data = await response.json();

    if (!response.ok) {
      const errorMessage = data?.detail || data?.error || 'Failed to load performance data';
      return NextResponse.json({ success: false, error: errorMessage }, { status: response.status });
    }

    return NextResponse.json({
      success: true,
      data
    });

  } catch (error: any) {
    console.error('Performance API error:', error);
    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Internal server error'
      },
      { status: 500 }
    );
  }
}
