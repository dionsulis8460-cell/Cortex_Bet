import { NextResponse } from 'next/server';
import { spawn, exec } from 'child_process';
import fs from 'fs';
import path from 'path';

// File to store the PID
const PID_FILE = path.join(process.cwd(), '.scanner.pid');
const SCANNER_SCRIPT = 'scripts/quick_scan.py';

// Helper to check if PID is running (Windows specific)
const isRunning = async (pid: number) => {
  return new Promise((resolve) => {
    exec(`tasklist /FI "PID eq ${pid}"`, (error, stdout) => {
      // If found, stdout will contain the Image Name (python.exe)
      // If not found, it says "No tasks are running..."
      resolve(stdout.toLowerCase().includes('python'));
    });
  });
};

export async function POST(request: Request) {
  try {
    const { action } = await request.json();

    if (action === 'start') {
      // Check if already running
      if (fs.existsSync(PID_FILE)) {
        const oldPid = parseInt(fs.readFileSync(PID_FILE, 'utf-8'));
        if (await isRunning(oldPid)) {
          return NextResponse.json({ message: 'Scanner already running', status: 'running' });
        }
      }

      // Start Process
      // We are in Cortex_Bet/web_app, venv is in Cortex_Bet/../venv (two levels up)
      const cortexRoot = path.join(process.cwd(), '..'); // Cortex_Bet/
      const venvRoot = path.join(process.cwd(), '..', '..'); // Cortex_Bet parent/
      const pythonPath = path.join(venvRoot, 'venv', 'Scripts', 'python.exe');
      const scriptPath = path.join(cortexRoot, SCANNER_SCRIPT);

      console.log('Spawning scanner:', pythonPath, scriptPath);

      const subprocess = spawn(pythonPath, [scriptPath, '--loop'], {
        detached: true,
        stdio: 'ignore', // Don't block parent
        cwd: cortexRoot // Run from Cortex_Bet root so imports work
      });

      subprocess.unref(); // Allow parent to exit independently

      // Save PID
      fs.writeFileSync(PID_FILE, subprocess.pid?.toString() || '');

      return NextResponse.json({ message: 'Scanner started', status: 'started', pid: subprocess.pid });
    }

    if (action === 'stop') {
      if (fs.existsSync(PID_FILE)) {
        const pid = fs.readFileSync(PID_FILE, 'utf-8');
        
        // Kill process (Windows)
        exec(`taskkill /PID ${pid} /F /T`, (err) => {
           // Ignore errors (process might be gone already)
        });
        
        fs.unlinkSync(PID_FILE);
        return NextResponse.json({ message: 'Scanner stopped', status: 'stopped' });
      }
      return NextResponse.json({ message: 'No scanner running', status: 'stopped' });
    }

    if (action === 'status') {
       let isActive = false;
       if (fs.existsSync(PID_FILE)) {
         const pid = parseInt(fs.readFileSync(PID_FILE, 'utf-8'));
         isActive = (await isRunning(pid)) as boolean;
         if (!isActive) {
           // Clean up stale file
           fs.unlinkSync(PID_FILE);
         }
       }
       return NextResponse.json({ active: isActive });
    }

    return NextResponse.json({ error: 'Invalid action' }, { status: 400 });

  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function GET() {
    // Alias for status check
    let isActive = false;
    if (fs.existsSync(PID_FILE)) {
        const pid = parseInt(fs.readFileSync(PID_FILE, 'utf-8'));
        isActive = (await isRunning(pid)) as boolean;
    }
    return NextResponse.json({ active: isActive });
}
