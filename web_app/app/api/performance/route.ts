import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const fromDate = searchParams.get('from_date') || 'None';
    const toDate = searchParams.get('to_date') || 'None';

    // Paths - using absolute paths like predictions API
    // Dynamic Paths
    const path = require('path');
    const projectRoot = path.resolve(process.cwd(), '..');
    const pythonPath = path.join(projectRoot, '.venv', 'Scripts', 'python.exe');
    const scriptPath = path.join(projectRoot, 'src', 'web', 'performance_api.py');

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
        { error: `Performance script not found at: ${scriptPath}` },
        { status: 500 }
      );
    }

    // Execute performance calculator
    const result = await new Promise<{ stdout: string; stderr: string }>((resolve, reject) => {
      const childProcess = spawn(pythonPath, [scriptPath, fromDate, toDate], {
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
          resolve({ stdout, stderr });
        } else {
          reject(new Error(`Performance calculator failed (code ${code}): ${stderr}`));
        }
      });

      childProcess.on('error', (err) => {
        reject(new Error(`Failed to start calculator: ${err.message}`));
      });
    });

    // Parse JSON output
    const data = JSON.parse(result.stdout.trim());

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
