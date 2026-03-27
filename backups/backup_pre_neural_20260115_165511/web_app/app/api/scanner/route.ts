import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

export async function POST(request: NextRequest) {
  try {
    const { date } = await request.json();

    if (!date) {
      return NextResponse.json(
        { error: 'Date parameter is required' },
        { status: 400 }
      );
    }

    // Paths
    // Paths
    // process.cwd() is web_app/
    // projectRoot is Cortex_Bet/ (the repo root)
    const projectRoot = path.resolve(process.cwd(), '..');
    
    // Venv is likely one level UP from projectRoot (Cortex_Bet/../venv) based on structure
    const pythonPath = path.join(projectRoot, '..', 'venv', 'Scripts', 'python.exe');
    
    // Script is in scripts/run_scanner.py
    const scriptPath = path.join(projectRoot, 'scripts', 'run_scanner.py');

    // Validate paths
    const fs = require('fs');
    if (!fs.existsSync(pythonPath)) {
      return NextResponse.json(
        { error: `Python not found at: ${pythonPath}` },
        { status: 500 }
      );
    }

    if (!fs.existsSync(scriptPath)) {
      return NextResponse.json(
        { error: `Scanner script not found at: ${scriptPath}` },
        { status: 500 }
      );
    }

    // Execute scanner
    const result = await new Promise<{ success: boolean; output: string; matchesProcessed: number }>((resolve, reject) => {
      const childProcess = spawn(pythonPath, [scriptPath, '--date', date], {
        cwd: projectRoot,
        env: { ...process.env, PYTHONUNBUFFERED: '1' }
      });

      let stdout = '';
      let stderr = '';

      childProcess.stdout.on('data', (data) => {
        const text = data.toString();
        // Log to server terminal for user to see
        process.stdout.write(text);
        stdout += text;
      });

      childProcess.stderr.on('data', (data) => {
        const text = data.toString();
        // Log to server error stream
        process.stderr.write(text);
        stderr += text;
      });

      childProcess.on('close', (code) => {
        if (code === 0) {
          try {
            // Try to parse JSON output from scanner
            const lines = stdout.trim().split('\n');
            const lastLine = lines[lines.length - 1];
            const result = JSON.parse(lastLine);
            resolve({
              success: true,
              output: stdout,
              matchesProcessed: result.matches_processed || 0
            });
          } catch {
            // Fallback if no JSON output
            resolve({
              success: true,
              output: stdout,
              matchesProcessed: 0
            });
          }
        } else {
          reject(new Error(`Scanner failed with code ${code}: ${stderr}`));
        }
      });

      childProcess.on('error', (err) => {
        reject(new Error(`Failed to start scanner: ${err.message}`));
      });
    });

    return NextResponse.json({
      success: true,
      message: 'Scanner completed successfully',
      matchesProcessed: result.matchesProcessed,
      output: result.output
    });

  } catch (error: any) {
    console.error('Scanner API error:', error);
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}
