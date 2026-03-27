import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const limit = searchParams.get('limit') || '50';

    const pythonPath = 'C:\\Users\\OEM\\Desktop\\Cortex_Bet\\venv\\Scripts\\python.exe';
    const scriptPath = 'C:\\Users\\OEM\\Desktop\\Cortex_Bet\\Cortex_Bet\\src\\web\\bankroll_api.py';

    const result = await new Promise<string>((resolve, reject) => {
      // Args: PUBLIC_FEED <limit>
      const childProcess = spawn(pythonPath, [scriptPath, 'PUBLIC_FEED', limit], {
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
          reject(new Error(`Feed fetch failed: ${stderr}`));
        }
      });

      childProcess.on('error', (err) => {
        reject(new Error(`Failed to start python script: ${err.message}`));
      });
    });

    const data = JSON.parse(result.trim());
    return NextResponse.json({ success: true, data });

  } catch (error: any) {
    console.error('Feed GET error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
