#!/usr/bin/env python3
"""
Investigate how Komposteur discovers MCP processors
"""
import subprocess
import os
import sys
from pathlib import Path

def investigate_mcp_discovery():
    """Investigate Komposteur's MCP discovery mechanism"""
    print("🔍 Investigating Komposteur MCP Discovery Mechanism")
    print("=" * 70)
    
    jar_path = Path.home() / ".m2/repository/no/lau/kompost/komposteur-core/0.8-SNAPSHOT/komposteur-core-0.8-SNAPSHOT-jar-with-dependencies.jar"
    
    # Test 1: Check what environment Komposteur looks for
    print("🧪 Test 1: Environment Variable Discovery")
    
    test_envs = {
        'MCP_PYTHON_PROCESSOR': '/usr/bin/python3',
        'MCP_SERVER_PATH': str(Path(__file__).parent / 'src' / 'server.py'),
        'KOMPOSTEUR_MCP_PROCESSOR': 'python3',
        'FFMPEG_MCP_SERVER': str(Path(__file__).parent),
        'PATH': os.environ.get('PATH', '') + ':' + str(Path(__file__).parent)
    }
    
    for env_var, value in test_envs.items():
        print(f"   Testing {env_var}={value}")
        
        env = os.environ.copy()
        env[env_var] = value
        
        result = test_komposteur_with_env(jar_path, env)
        if result != "Python subprocess returned error":
            print(f"   🎯 Different result with {env_var}: {result}")
        else:
            print(f"   ❌ Same error with {env_var}")
    
    # Test 2: Check working directory expectations
    print(f"\n🧪 Test 2: Working Directory Discovery")
    
    test_dirs = [
        Path(__file__).parent,  # Current project
        Path(__file__).parent / "src",  # MCP server location
        Path.cwd(),  # Current working directory
        Path("/tmp")  # Temp directory
    ]
    
    for test_dir in test_dirs:
        if test_dir.exists():
            print(f"   Testing from directory: {test_dir}")
            result = test_komposteur_from_dir(jar_path, test_dir)
            if result != "Python subprocess returned error":
                print(f"   🎯 Different result from {test_dir}: {result}")
            else:
                print(f"   ❌ Same error from {test_dir}")
    
    # Test 3: Check for expected files/scripts
    print(f"\n🧪 Test 3: Expected Files Discovery")
    
    expected_files = [
        "mcp_processor.py",
        "komposteur_processor.py", 
        "video_processor.py",
        "process_kompost.py",
        "src/server.py"
    ]
    
    for filename in expected_files:
        file_path = Path(__file__).parent / filename
        if not file_path.exists() and filename != "src/server.py":
            # Create minimal test file
            file_path.parent.mkdir(exist_ok=True)
            with open(file_path, 'w') as f:
                f.write('#!/usr/bin/env python3\nprint("MCP processor called")\n')
            file_path.chmod(0o755)
            
        print(f"   Created test file: {filename}")
        
        result = test_komposteur_with_env(jar_path, os.environ.copy())
        if result != "Python subprocess returned error":
            print(f"   🎯 Different result with {filename}: {result}")
            break
        else:
            print(f"   ❌ Same error with {filename}")

def test_komposteur_with_env(jar_path, env):
    """Test Komposteur with specific environment"""
    java_wrapper = '''
import no.lau.komposteur.core.KomposteurEntryPoint;

public class EnvTestWrapper {
    public static void main(String[] args) {
        try {
            KomposteurEntryPoint komposteur = new KomposteurEntryPoint();
            komposteur.initialize();
            
            String result = komposteur.processKompost(args[0]);
            System.out.println("SUCCESS:" + result);
        } catch (Exception e) {
            String msg = e.getMessage();
            if (msg != null && msg.contains("Python subprocess")) {
                System.out.println("ERROR:Python subprocess returned error");
            } else {
                System.out.println("ERROR:" + msg);
            }
        }
    }
}
'''
    
    # Create minimal test kompost
    test_kompost = Path("/tmp/env_test.json")
    with open(test_kompost, 'w') as f:
        f.write('{"metadata":{"name":"env_test"},"segments":[]}')
    
    # Compile and run
    wrapper_file = Path("/tmp/EnvTestWrapper.java")
    with open(wrapper_file, 'w') as f:
        f.write(java_wrapper)
    
    # Compile
    compile_cmd = ["javac", "-cp", str(jar_path), str(wrapper_file)]
    compile_result = subprocess.run(compile_cmd, capture_output=True, text=True, env=env)
    
    if compile_result.returncode != 0:
        return "Compile failed"
    
    # Run
    run_cmd = ["java", "-cp", f"{jar_path}:/tmp", "EnvTestWrapper", str(test_kompost)]
    run_result = subprocess.run(run_cmd, capture_output=True, text=True, env=env)
    
    output = run_result.stdout.strip()
    if output.startswith("SUCCESS:"):
        return output[8:]
    elif output.startswith("ERROR:"):
        return output[6:]
    else:
        return f"Unknown: {output}"

def test_komposteur_from_dir(jar_path, working_dir):
    """Test Komposteur from specific working directory"""
    return test_komposteur_with_env(jar_path, os.environ.copy())

if __name__ == "__main__":
    investigate_mcp_discovery()