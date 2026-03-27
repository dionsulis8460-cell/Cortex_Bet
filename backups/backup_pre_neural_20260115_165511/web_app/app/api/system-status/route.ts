import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const venvPython = 'C:\\Users\\OEM\\Desktop\\Cortex_Bet\\venv\\Scripts\\python.exe';
    const scriptPath = 'C:\\Users\\OEM\\Desktop\\Cortex_Bet\\Cortex_Bet\\web_app\\lib\\api_bridge.py';
    
    // Call with 'system-status' type
    const command = `"${venvPython}" "${scriptPath}" "system-status"`;
    
    const { stdout, stderr } = await execAsync(command, { 
      cwd: 'C:\\Users\\OEM\\Desktop\\Cortex_Bet\\Cortex_Bet',
      maxBuffer: 1024 * 1024 * 10,
      encoding: 'utf8'
    });

    if (!stdout || stdout.trim().length === 0) {
      console.error('Python stderr:', stderr);
      throw new Error('Python script returned empty output');
    }

    const data = JSON.parse(stdout.trim());
    
    if (data.error && data.type === 'python_error') {
      throw new Error(`Python Error: ${data.error}`);
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
