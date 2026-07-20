#!/usr/bin/env python3
"""
Debug Komposteur output to understand what's actually happening
"""
import sys
import json
import subprocess
from pathlib import Path

# Create a very simple kompost.json that should work
def create_minimal_kompost():
    """Create absolute minimal kompost.json"""
    test_dir = Path("/tmp/kompost_debug")
    test_dir.mkdir(exist_ok=True)
    
    kompost_config = {
        "version": "1.0",
        "metadata": {
            "name": "debug_test"
        },
        "sources": [
            {
                "id": "video1",
                "type": "video",
                "path": str(Path(__file__).parent / "tests/files/JJVtt947FfI_136.mp4")
            }
        ],
        "segments": [
            {
                "source": "video1",
                "start_beat": 0,
                "end_beat": 8
            }
        ]
    }
    
    kompost_file = test_dir / "debug_kompost.json"
    with open(kompost_file, 'w') as f:
        json.dump(kompost_config, f, indent=2)
    
    return kompost_file

def debug_komposteur_directly():
    """Call Komposteur directly to see raw output"""
    print("🔍 Debugging Komposteur Output")
    print("=" * 50)
    
    # Create test file
    kompost_file = create_minimal_kompost()
    print(f"📄 Created test file: {kompost_file}")
    
    # Check that source video exists
    source_video = Path(__file__).parent / "tests/files/JJVtt947FfI_136.mp4"
    if source_video.exists():
        print(f"✅ Source video exists: {source_video} ({source_video.stat().st_size:,} bytes)")
    else:
        print(f"❌ Source video missing: {source_video}")
        return
    
    # Create Java wrapper with more debugging
    jar_path = Path.home() / ".m2/repository/no/lau/kompost/komposteur-core/0.8-SNAPSHOT/komposteur-core-0.8-SNAPSHOT-jar-with-dependencies.jar"
    
    java_wrapper = f'''
import no.lau.komposteur.core.KomposteurEntryPoint;
import java.nio.file.Path;
import java.nio.file.Paths;

public class DebugWrapper {{
    public static void main(String[] args) {{
        try {{
            System.out.println("DEBUG: Starting Komposteur...");
            System.out.println("DEBUG: Input file: " + args[0]);
            System.out.println("DEBUG: Working directory: " + System.getProperty("user.dir"));
            
            Path inputPath = Paths.get(args[0]);
            System.out.println("DEBUG: Input path resolved: " + inputPath.toAbsolutePath());
            System.out.println("DEBUG: Input file exists: " + inputPath.toFile().exists());
            
            KomposteurEntryPoint komposteur = new KomposteurEntryPoint();
            komposteur.initialize();
            System.out.println("DEBUG: Komposteur initialized");
            
            String result = komposteur.processKompost(args[0]);
            System.out.println("RESULT:" + result);
            
            komposteur.shutdown();
            System.out.println("DEBUG: Komposteur shutdown");
        }} catch (Exception e) {{
            System.err.println("ERROR:" + e.getMessage());
            e.printStackTrace();
        }}
    }}
}}
'''
    
    # Write and compile wrapper
    wrapper_file = Path("/tmp/DebugWrapper.java")
    with open(wrapper_file, 'w') as f:
        f.write(java_wrapper)
    
    print(f"\n🔧 Compiling Java wrapper...")
    compile_cmd = ["javac", "-cp", str(jar_path), str(wrapper_file)]
    compile_result = subprocess.run(compile_cmd, capture_output=True, text=True)
    
    if compile_result.returncode != 0:
        print(f"❌ Compilation failed: {compile_result.stderr}")
        return
    
    print(f"✅ Compilation successful")
    
    # Run wrapper with detailed output
    print(f"\n🚀 Running Komposteur...")
    print(f"Command: java -cp {jar_path}:/tmp DebugWrapper {kompost_file}")
    
    run_cmd = ["java", "-cp", f"{jar_path}:/tmp", "DebugWrapper", str(kompost_file)]
    run_result = subprocess.run(run_cmd, capture_output=True, text=True)
    
    print(f"\n📊 RESULTS:")
    print(f"Return code: {run_result.returncode}")
    print(f"\nSTDOUT:")
    print(run_result.stdout)
    print(f"\nSTDERR:")
    print(run_result.stderr)
    
    # Check for any files created
    print(f"\n📁 Checking for output files...")
    test_dir = kompost_file.parent
    for file in test_dir.iterdir():
        if file.suffix in ['.mp4', '.avi', '.mov']:
            print(f"✅ Found video: {file} ({file.stat().st_size:,} bytes)")
        elif file.name != kompost_file.name and file.suffix != '.java':
            print(f"📄 Found file: {file}")

if __name__ == "__main__":
    debug_komposteur_directly()