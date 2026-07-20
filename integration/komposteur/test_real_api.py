#!/usr/bin/env python3
"""
Test the real Komposteur API directly to understand what it does
"""
import json
import sys
import os
from pathlib import Path

# Add integration to path  
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def create_simple_kompost():
    """Create a minimal kompost.json for testing"""
    kompost_config = {
        "version": "1.0",
        "metadata": {
            "name": "simple_test",
            "description": "Simple test for Komposteur API"
        },
        "sources": [
            {
                "id": "test_video",
                "type": "video", 
                "path": "tests/files/JJVtt947FfI_136.mp4"
            }
        ],
        "segments": [
            {
                "source": "test_video",
                "start_beat": 0,
                "end_beat": 16,
                "effects": []
            }
        ],
        "output": {
            "format": "mp4",
            "codec": "h264"
        }
    }
    
    test_file = Path("simple_kompost_test.json")
    with open(test_file, 'w') as f:
        json.dump(kompost_config, f, indent=2)
    
    return test_file

def test_komposteur_directly():
    """Test Komposteur API directly with detailed logging"""
    print("🧪 Testing real Komposteur API...")
    
    # Create test file
    kompost_file = create_simple_kompost()
    print(f"✅ Created test file: {kompost_file}")
    
    try:
        from integration.komposteur.bridge.komposteur_bridge import KomposteurBridge
        
        bridge = KomposteurBridge()
        print(f"🔌 Initializing bridge...")
        
        if not bridge.initialize():
            print("❌ Bridge initialization failed")
            return
            
        print(f"✅ Bridge initialized successfully")
        print(f"📋 JAR path: {bridge.jar_path}")
        
        # Test the processing
        print(f"\n🎬 Processing kompost.json...")
        kompost_path = str(kompost_file.absolute())
        print(f"   Input: {kompost_path}")
        
        result = bridge.process_kompost_json(kompost_path)
        
        print(f"\n📊 RESULT:")
        print(f"   Success: {result.get('success')}")
        
        if result.get('success'):
            print(f"   ✅ Processing completed!")
            print(f"   📁 Output path: {result.get('output_video_path')}")
            print(f"   📝 Processing log: {result.get('processing_log')}")
            print(f"   🎨 Effects used: {result.get('curated_effects_used')}")
            print(f"   🔧 Raw result: {result.get('raw_result')}")
            
            # Check if output file exists
            raw_result = result.get('raw_result', '')
            if raw_result and Path(raw_result).exists():
                file_size = Path(raw_result).stat().st_size
                print(f"   ✅ Output file exists: {file_size} bytes")
            else:
                print(f"   ⚠️  Output file not found at: {raw_result}")
                
        else:
            print(f"   ❌ Processing failed")
            print(f"   🐛 Error: {result.get('error')}")
            if 'stdout' in result:
                print(f"   📤 Stdout: {result['stdout']}")
            if 'stderr' in result:
                print(f"   📥 Stderr: {result['stderr']}")
        
        bridge.shutdown()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if kompost_file.exists():
            kompost_file.unlink()

if __name__ == "__main__":
    test_komposteur_directly()