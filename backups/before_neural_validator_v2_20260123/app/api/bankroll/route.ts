import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

// GET - Fetch user's bets and bankroll
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const type = searchParams.get('type') || 'all'; // 'all', 'history', 'balance'
    // TODO: Get userId from Session/Auth. Defaulting to 1 for now.
    const userId = searchParams.get('userId') || '1'; 

    const pythonPath = 'C:\\Users\\OEM\\Desktop\\Cortex_Bet\\venv\\Scripts\\python.exe';
    const scriptPath = 'C:\\Users\\OEM\\Desktop\\Cortex_Bet\\Cortex_Bet\\src\\web\\bankroll_api.py';

    const result = await new Promise<string>((resolve, reject) => {
      // Args: GET <type> <userId>
      const childProcess = spawn(pythonPath, [scriptPath, 'GET', type, userId], {
        cwd: 'C:\\Users\\OEM\\Desktop\\Cortex_Bet\\Cortex_Bet',
        env: { ...process.env, PYTHONUNBUFFERED: '1' }
      });

      let stdout = '';
      let stderr = '';

      childProcess.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      childProcess.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      childProcess.on('close', (code) => {
        if (code === 0) {
          resolve(stdout);
        } else {
          reject(new Error(`Bankroll script failed: ${stderr}`));
        }
      });
      
      childProcess.on('error', (err) => {
        reject(new Error(`Failed to start python script: ${err.message}`));
      });
    });

    try {
      const data = JSON.parse(result.trim());
      if (data.error) {
        // If error is insufficient funds or similar, return 400 but valid JSON
        return NextResponse.json({ success: false, error: data.error }, { status: 400 });
      }
      return NextResponse.json({ success: true, data });
    } catch (e) {
      console.error('JSON Parse Error:', result);
      return NextResponse.json({ success: false, error: 'Invalid JSON response from backend' }, { status: 500 });
    }

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

    const pythonPath = 'C:\\Users\\OEM\\Desktop\\Cortex_Bet\\venv\\Scripts\\python.exe';
    const scriptPath = 'C:\\Users\\OEM\\Desktop\\Cortex_Bet\\Cortex_Bet\\src\\web\\bankroll_api.py';

    const result = await new Promise<string>((resolve, reject) => {
      // Check if it's a transaction
      if (body.action === 'transaction') {
         // Args: TRANSACTION <user_id> <type> <amount>
         const childProcess = spawn(pythonPath, [scriptPath, 'TRANSACTION', body.userId.toString(), body.type, body.amount.toString()], {
            cwd: 'C:\\Users\\OEM\\Desktop\\Cortex_Bet\\Cortex_Bet',
            env: { ...process.env, PYTHONUNBUFFERED: '1' }
         });
         
         handleSpawn(childProcess, resolve, reject, 'Transaction failed');

      } else {
         // Default: Place Bet
         // Args: POST <json_body>
         const childProcess = spawn(pythonPath, [scriptPath, 'POST', JSON.stringify(body)], {
            cwd: 'C:\\Users\\OEM\\Desktop\\Cortex_Bet\\Cortex_Bet',
            env: { ...process.env, PYTHONUNBUFFERED: '1' }
         });

         handleSpawn(childProcess, resolve, reject, 'Place bet failed');
      }
    });

    const data = JSON.parse(result.trim());
    return NextResponse.json({ success: true, data });

  } catch (error: any) {
    console.error('Bankroll POST error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

// Helper to avoid duplicate code
function handleSpawn(childProcess: any, resolve: any, reject: any, errorMsg: string) {
      let stdout = '';
      let stderr = '';

      childProcess.stdout.on('data', (data: any) => {
        stdout += data.toString();
      });

      childProcess.stderr.on('data', (data: any) => {
        stderr += data.toString();
      });

      childProcess.on('close', (code: number) => {
        if (code === 0) {
          resolve(stdout);
        } else {
          reject(new Error(`${errorMsg}: ${stderr}`));
        }
      });
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

    const pythonPath = 'C:\\Users\\OEM\\Desktop\\Cortex_Bet\\venv\\Scripts\\python.exe';
    const scriptPath = 'C:\\Users\\OEM\\Desktop\\Cortex_Bet\\Cortex_Bet\\src\\web\\bankroll_api.py';

    const result = await new Promise<string>((resolve, reject) => {
      // Args: DELETE <betId> <userId>
      const childProcess = spawn(pythonPath, [scriptPath, 'DELETE', id, userId], {
        cwd: 'C:\\Users\\OEM\\Desktop\\Cortex_Bet\\Cortex_Bet',
        env: { ...process.env, PYTHONUNBUFFERED: '1' }
      });

      let stdout = '';
      let stderr = '';

      childProcess.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      childProcess.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      childProcess.on('close', (code) => {
        if (code === 0) {
          resolve(stdout);
        } else {
          reject(new Error(`Delete bet failed: ${stderr}`));
        }
      });
    });

    const data = JSON.parse(result.trim());
    return NextResponse.json({ success: true, data });

  } catch (error: any) {
    console.error('Bankroll DELETE error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
