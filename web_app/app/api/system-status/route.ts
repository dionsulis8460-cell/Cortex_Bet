import { NextResponse } from 'next/server';

const API_BASE_URL = 'http://127.0.0.1:8000';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/system-status`, {
      method: 'GET',
      cache: 'no-store',
    });
    const data = await response.json();

    if (!response.ok) {
      const errorMessage = data?.detail || data?.error || 'Failed to fetch system status';
      return NextResponse.json({ error: errorMessage, status: 'error' }, { status: response.status });
    }

    return NextResponse.json(data);

  } catch (error: any) {
    console.error('Error fetching system status:', error);
    return NextResponse.json(
      { error: error.message, status: 'error' },
      { status: 500 }
    );
  }
}
