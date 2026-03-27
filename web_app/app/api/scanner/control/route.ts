import { NextResponse } from 'next/server';
 
const API_BASE_URL = 'http://127.0.0.1:8000';

export async function POST(request: Request) {
  try {
    const { action } = await request.json();

    const response = await fetch(`${API_BASE_URL}/api/scanner/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action }),
      cache: 'no-store',
    });
    const payload = await response.json();

    if (!response.ok) {
      const errorMessage = payload?.detail || payload?.error || 'Scanner control request failed';
      return NextResponse.json({ error: errorMessage }, { status: response.status });
    }

    return NextResponse.json(payload);

  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function GET() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/scanner/control`, {
      method: 'GET',
      cache: 'no-store',
    });
    const payload = await response.json();

    if (!response.ok) {
      const errorMessage = payload?.detail || payload?.error || 'Scanner status request failed';
      return NextResponse.json({ error: errorMessage }, { status: response.status });
    }

    return NextResponse.json(payload);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
