import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

// POST - Authenticate user
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { username, password } = body;

    if (!username || !password) {
      return NextResponse.json({ success: false, error: 'Missing credentials' }, { status: 400 });
    }

    // Dynamic Paths
    const path = require('path');
    const projectRoot = path.resolve(process.cwd(), '..');
    const pythonPath = path.join(projectRoot, '.venv', 'Scripts', 'python.exe');
    const scriptPath = path.join(projectRoot, 'src', 'web', 'bankroll_api.py');

    const result = await new Promise<string>((resolve, reject) => {
      // Args: AUTH <username> <password>
      const childProcess = spawn(pythonPath, [scriptPath, 'AUTH', username, password], {
        cwd: projectRoot,
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
          reject(new Error(`Auth failed: ${stderr}`));
        }
      });

      childProcess.on('error', (err) => {
        reject(new Error(`Failed to start auth script: ${err.message}`));
      });
    });

    try {
      const data = JSON.parse(result.trim());
      if (data.error) {
        return NextResponse.json({ success: false, error: data.error }, { status: 401 });
      }
      return NextResponse.json({ success: true, data });
    } catch (e) {
      console.error('JSON Parse Error:', result);
      return NextResponse.json({ success: false, error: 'Invalid JSON response from backend' }, { status: 500 });
    }

  } catch (error: any) {
    console.error('Auth API error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
