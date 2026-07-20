#!/usr/bin/env python3
"""
Java environment setup for MCP server
"""
import os
import subprocess
import sys
from pathlib import Path

def set_java_environment():
    """Set Java environment variables"""
    # Preferred Java 23 from Homebrew
    java_home = "/usr/local/opt/openjdk/libexec/openjdk.jdk/Contents/Home"
    java_bin = "/usr/local/opt/openjdk/bin"
    
    if Path(java_home).exists():
        os.environ['JAVA_HOME'] = java_home
        # Prepend to PATH to override system Java
        current_path = os.environ.get('PATH', '')
        if java_bin not in current_path:
            os.environ['PATH'] = f"{java_bin}:{current_path}"
        
        print(f"✅ Java environment set:")
        print(f"   JAVA_HOME: {java_home}")
        print(f"   Java binary: {java_bin}/java")
        
        # Verify Java version
        try:
            result = subprocess.run([f"{java_bin}/java", "-version"], 
                                 capture_output=True, text=True)
            version_info = result.stderr.split('\n')[0] if result.stderr else "Unknown"
            print(f"   Version: {version_info}")
            return True
        except Exception as e:
            print(f"❌ Failed to verify Java version: {e}")
            return False
    else:
        print(f"❌ Java 23 not found at {java_home}")
        
        # Try alternative Java locations
        alternatives = [
            "/Library/Java/JavaVirtualMachines/openjdk-21.jdk/Contents/Home",
            "/usr/libexec/java_home -v 21",
        ]
        
        for alt in alternatives:
            if alt.startswith("/usr/libexec"):
                try:
                    result = subprocess.run(alt.split(), capture_output=True, text=True)
                    if result.returncode == 0:
                        alt_home = result.stdout.strip()
                        if Path(alt_home).exists():
                            os.environ['JAVA_HOME'] = alt_home
                            print(f"✅ Using alternative Java: {alt_home}")
                            return True
                except:
                    continue
            elif Path(alt).exists():
                os.environ['JAVA_HOME'] = alt
                print(f"✅ Using alternative Java: {alt}")
                return True
        
        print("❌ No suitable Java version found")
        return False

def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path(".env")
    if env_file.exists():
        print("📁 Loading .env file...")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        # Expand PATH references
                        if key == 'PATH' and '$PATH' in value:
                            value = value.replace('$PATH', os.environ.get('PATH', ''))
                        os.environ[key] = value
                        print(f"   {key}={value}")
        return True
    return False

def start_mcp_server():
    """Start MCP server with proper environment"""
    print("\n🚀 Starting MCP server...")
    
    # Ensure we have Python virtual environment
    venv_python = ".venv/bin/python"
    if not Path(venv_python).exists():
        print("❌ Virtual environment not found at .venv/")
        return False
    
    try:
        # Start server as module
        cmd = [venv_python, "-m", "src.server"]
        print(f"   Command: {' '.join(cmd)}")
        
        # Run with proper environment
        env = os.environ.copy()
        print(f"   JAVA_HOME: {env.get('JAVA_HOME', 'Not set')}")
        print(f"   Java in PATH: {'yes' if '/openjdk/bin' in env.get('PATH', '') else 'no'}")
        
        process = subprocess.Popen(cmd, env=env)
        print(f"   PID: {process.pid}")
        
        # Let it start
        import time
        time.sleep(3)
        
        # Check if still running
        if process.poll() is None:
            print("✅ MCP server started successfully")
            return process
        else:
            print("❌ MCP server exited immediately")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start MCP server: {e}")
        return None

if __name__ == "__main__":
    print("🔧 Setting up Java environment for MCP server")
    print("=" * 50)
    
    # Load .env if available
    load_env_file()
    
    # Set Java environment
    java_ok = set_java_environment()
    
    if java_ok:
        print("\n" + "=" * 50)
        server_process = start_mcp_server()
        
        if server_process:
            try:
                print("\n📝 MCP server is running. Press Ctrl+C to stop...")
                server_process.wait()
            except KeyboardInterrupt:
                print("\n🛑 Stopping MCP server...")
                server_process.terminate()
                server_process.wait()
                print("✅ MCP server stopped")
        else:
            print("❌ Failed to start MCP server")
            sys.exit(1)
    else:
        print("❌ Java environment setup failed")
        sys.exit(1)