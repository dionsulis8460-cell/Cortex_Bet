import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = 'http://127.0.0.1:8000';

// GET - Fetch user's bets and bankroll
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const type = searchParams.get('type') || 'all'; // 'all', 'history', 'balance'
    // TODO: Get userId from Session/Auth. Defaulting to 1 for now.
    const userId = searchParams.get('userId') || '1';

    const response = await fetch(
      `${API_BASE_URL}/api/bankroll?type=${encodeURIComponent(type)}&user_id=${encodeURIComponent(userId)}`,
      { cache: 'no-store' },
    );
    const data = await response.json();

    if (!response.ok) {
      const errorMessage = data?.detail || data?.error || 'Failed to load bankroll data';
      return NextResponse.json({ success: false, error: errorMessage }, { status: response.status });
    }

    return NextResponse.json({ success: true, data });

  } catch (error: any) {
    console.error('Bankroll GET error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

// POST - Place new bet
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Inject userId into body if not present (Auth Middleware will do this later)
    if (!body.userId) {
      body.userId = 1;
    }

    const response = await fetch(`${API_BASE_URL}/api/bankroll`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      cache: 'no-store',
    });
    const data = await response.json();

    if (!response.ok) {
      const errorMessage = data?.detail || data?.error || 'Bankroll operation failed';
      return NextResponse.json({ success: false, error: errorMessage }, { status: response.status });
    }

    return NextResponse.json({ success: true, data });

  } catch (error: any) {
    console.error('Bankroll POST error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

// DELETE - Delete a bet / refund if pending
export async function DELETE(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const id = searchParams.get('id');
    const userId = searchParams.get('userId') || '1'; // Default to admin

    if (!id) {
      return NextResponse.json({ success: false, error: 'Missing bet ID' }, { status: 400 });
    }

    const response = await fetch(
      `${API_BASE_URL}/api/bankroll?id=${encodeURIComponent(id)}&user_id=${encodeURIComponent(userId)}`,
      {
        method: 'DELETE',
        cache: 'no-store',
      },
    );
    const data = await response.json();

    if (!response.ok) {
      const errorMessage = data?.detail || data?.error || 'Delete bet failed';
      return NextResponse.json({ success: false, error: errorMessage }, { status: response.status });
    }

    return NextResponse.json({ success: true, data });

  } catch (error: any) {
    console.error('Bankroll DELETE error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
