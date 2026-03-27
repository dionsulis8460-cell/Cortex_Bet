import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';

export async function POST(request: NextRequest) {
  try {
    const pythonPath = 'C:\\Users\\OEM\\Desktop\\Cortex_Bet\\venv\\Scripts\\python.exe';
    const scriptPath = 'C:\\Users\\OEM\\Desktop\\Cortex_Bet\\Cortex_Bet\\src\\analysis\\bet_validator.py';

    const result = await new Promise<{ stdout: string; stderr: string }>((resolve, reject) => {
      const childProcess = spawn(pythonPath, [scriptPath], {
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
          resolve({ stdout, stderr });
        } else {
          reject(new Error(`Validator failed (code ${code}): ${stderr}`));
        }
      });

      childProcess.on('error', (err) => {
        reject(new Error(`Failed to start validator: ${err.message}`));
      });
    });

    // Parse output to get count
    const lines = result.stdout.trim().split('\n');
    const successLine = lines.find(l => l.includes('[SUCCESS]'));
    const match = successLine?.match(/(\d+) bets processed/);
    const validatedCount = match ? parseInt(match[1]) : 0;

    return NextResponse.json({
      success: true,
      validated_count: validatedCount,
      output: result.stdout
    });

  } catch (error: any) {
    console.error('Validator API error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
