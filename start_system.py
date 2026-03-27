import subprocess
import sys
import time
import os
import signal
import socket

def get_local_ip():
    try:
        # Connect to a public DNS to get the local IP (doesn't actually send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def main():
    print("🚀 Starting Cortex Bet System (Microservice Architecture)...")
    
    local_ip = get_local_ip()
    print(f"🌍 Local Network IP: {local_ip}")

    processes = []

    try:
        # 1. Start API Server (FastAPI)
        print("🔵 Starting Python API Server (Port 8000)...")
        # specific for Windows python
        api = subprocess.Popen([sys.executable, "src/api/server.py"])
        processes.append(api)
        print(f"   PID: {api.pid}")
        time.sleep(5) # Wait for imports (Neural Engine loading takes time)

        # 2. Start Data Scanner (Background Loop)
        print("🟢 Starting Data Scanner (Quick Scan)...")
        scanner = subprocess.Popen([sys.executable, "scripts/quick_scan.py"])
        processes.append(scanner)
        
        # Write PID to file so web app thinks it is "ON" (ScannerControls.tsx checks this)
        try:
            # Check if web_app dir exists (it should), write .scanner.pid inside it
            pid_path = os.path.join("web_app", ".scanner.pid")
            with open(pid_path, "w") as f:
                f.write(str(scanner.pid))
        except Exception as e:
            print(f"⚠️ Could not write .scanner.pid: {e}")
        
        # Write PID to file so web app thinks it is "ON" (ScannerControls.tsx checks this)
        try:
            with open("web_app/.scanner.pid", "w") as f:
                f.write(str(scanner.pid))
        except Exception as e:
            print(f"⚠️ Could not write .scanner.pid: {e}")

        # 3. Start Frontend (Next.js)
        print("🟠 Starting Web App (Next.js)...")
        # npm needs shell=True on Windows usually to find the executable
        frontend = subprocess.Popen(["npm", "run", "dev"], cwd="web_app", shell=True)
        processes.append(frontend)

        print("\n✅ ALL SYSTEMS GO!")
        print("---------------------------------------")
        print(f"📡 API Server: http://{local_ip}:8000")
        print(f"💻 Web App:    http://{local_ip}:8501")
        print("🔍 Scanner:    Active (Background)")
        print("---------------------------------------")
        print("🏠 Home Assistant: Settings > Dashboards > Add > Webpage")
        print(f"URL: http://{local_ip}:8501")
        print("---------------------------------------")
        print("Press CTRL+C to stop all services.\n")

        while True:
            time.sleep(1)
            # Check if critical processes died
            if api.poll() is not None:
                print("❌ API Server died! Exiting...")
                break

    except KeyboardInterrupt:
        print("\n🛑 Stopping all services...")
    finally:
        for p in processes:
            try:
                # Basic terminate
                p.terminate()
                # If shell=True (frontend), we might need stronger kill on Windows
            except Exception:
                pass
        
        # Force kill for Windows if needed (taskkill)
        # os.system("taskkill /bf /im python.exe") # Too aggressive?
        print("Create a new terminal if ports remain in use.")

if __name__ == "__main__":
    main()
