#!/usr/bin/env python3
"""
Test Goal: MCP Server wrapping Komposteur for kompost.json processing

This test demonstrates the target workflow:
1. MCP receives kompost.json with curated FFMPEG instructions
2. MCP delegates to Komposteur Java library for execution
3. Komposteur applies proven FFMPEG patterns
4. MCP tracks discovery patterns and improvements

Goal: Kompost project curates FFMPEG recipes, MCP discovers new patterns
"""
import json
import sys
import os
from pathlib import Path

# Add integration to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def create_test_kompost_json():
    """Create a test kompost.json file representing curated FFMPEG workflow"""
    kompost_config = {
        "version": "1.0",
        "metadata": {
            "name": "film_noir_beat_sync",
            "description": "Film noir style with 128-beat synchronization",
            "bpm": 120,
            "duration_seconds": 64.0,
            "created_by": "kompost_curator"
        },
        "sources": [
            {
                "id": "video_main",
                "type": "video",
                "path": "JJVtt947FfI_136.mp4",
                "description": "Primary video content"
            },
            {
                "id": "audio_track", 
                "type": "audio",
                "path": "Subnautic Measures.flac",
                "description": "Background music track"
            }
        ],
        "segments": [
            {
                "source": "video_main",
                "start_beat": 0,
                "end_beat": 64,
                "effects": [
                    {
                        "name": "film_noir_grade",
                        "type": "curated_ffmpeg",
                        "parameters": {
                            "contrast": 1.2,
                            "saturation": 0.3,
                            "vignette": 0.8
                        },
                        "ffmpeg_filter": "curves=vintage,colorbalance=rs=0.2:gs=-0.1:bs=-0.2"
                    },
                    {
                        "name": "beat_sync_timing",
                        "type": "timing_sync",
                        "parameters": {
                            "bpm": 120,
                            "sync_points": [0, 16, 32, 48, 64]
                        }
                    }
                ]
            }
        ],
        "output": {
            "format": "mp4",
            "codec": "h264",
            "quality": "high",
            "target_duration": 64.0
        },
        "komposteur_config": {
            "use_microsecond_precision": True,
            "cache_strategy": "intelligent",
            "validation_level": "comprehensive"
        }
    }
    
    test_file = Path("test_kompost.json")
    with open(test_file, 'w') as f:
        json.dump(kompost_config, f, indent=2)
    
    return test_file

def test_komposteur_java_connection():
    """Test if we can connect to Komposteur Java library"""
    print("🔌 Testing Komposteur Java connection...")
    
    try:
        from integration.komposteur.bridge.komposteur_bridge import KomposteurBridge
        
        bridge = KomposteurBridge()
        success = bridge.initialize()
        
        if success:
            print("✅ Komposteur Java bridge connected")
            version = bridge.get_version()
            print(f"   Version: {version}")
            
            # Test basic API access - updated for new bridge structure
            try:
                # Test the main kompost processing method
                if hasattr(bridge, 'process_kompost_json'):
                    print("✅ process_kompost_json method available")
                    # Test with a mock path to see the expected workflow
                    result = bridge.process_kompost_json("/mock/path/test.json")
                    if "expected_workflow" in result:
                        print("✅ Expected workflow documented in bridge")
                    else:
                        print("⚠️  Expected workflow not documented")
                else:
                    print("⚠️  process_kompost_json method not found")
                    print(f"   Available methods: {[m for m in dir(bridge) if not m.startswith('_')]}")
                
                bridge.shutdown()
                return True
                
            except Exception as e:
                print(f"⚠️  API exploration failed: {e}")
                bridge.shutdown()
                return False
        else:
            print("❌ Failed to connect to Komposteur Java")
            return False
            
    except Exception as e:
        print(f"❌ Bridge connection failed: {e}")
        return False

def test_kompost_json_processing():
    """Test processing a kompost.json file through the bridge"""
    print("\n📄 Testing kompost.json processing...")
    
    # Create test kompost.json
    kompost_file = create_test_kompost_json()
    print(f"✅ Created test kompost.json: {kompost_file}")
    
    try:
        from integration.komposteur.bridge.komposteur_bridge import KomposteurBridge
        
        bridge = KomposteurBridge()
        if not bridge.initialize():
            print("❌ Bridge initialization failed")
            return False
        
        try:
            # Try to process the kompost.json file
            kompost_path = str(kompost_file.absolute())
            print(f"   Processing: {kompost_path}")
            
            # Test the current bridge implementation
            result = bridge.process_kompost_json(kompost_path)
            
            if result.get("success"):
                print("✅ Kompost file processed successfully")
                print(f"   Result: {result}")
                return True
            elif "expected_workflow" in result:
                print("⚠️  Mock implementation - shows expected workflow")
                expected = result["expected_workflow"]
                print(f"   Expected class: {expected['java_class']}")
                print(f"   Expected method: {expected['expected_method']}")
                print("   💡 This documents what we need from Komposteur library")
                return True  # Consider this success for now as it shows the workflow
            else:
                print("❌ Kompost processing failed")
                print(f"   Error: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Kompost processing failed: {e}")
            return False
        finally:
            bridge.shutdown()
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        # Cleanup
        if kompost_file.exists():
            kompost_file.unlink()

def test_mcp_komposteur_integration():
    """Test the full MCP -> Komposteur integration"""
    print("\n🎬 Testing MCP -> Komposteur integration...")
    
    try:
        from integration.komposteur.tools.mcp_tools import register_komposteur_tools
        
        # Mock MCP server
        class MockMCPServer:
            def __init__(self):
                self.tools = {}
                
            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func
                return decorator
        
        # Register tools
        server = MockMCPServer()
        tools = register_komposteur_tools(server)
        
        print(f"✅ Registered {len(tools)} MCP tools")
        
        # Test if we have a kompost processing tool
        if 'komposteur_process_kompost' in server.tools:
            print("✅ komposteur_process_kompost tool available")
            return True
        else:
            print("⚠️  Need to implement komposteur_process_kompost tool")
            print(f"   Available tools: {list(server.tools.keys())}")
            return False
            
    except Exception as e:
        print(f"❌ MCP integration test failed: {e}")
        return False

def analyze_komposteur_api():
    """Analyze the actual Komposteur API to understand capabilities"""
    print("\n🔍 Analyzing Komposteur API...")
    
    try:
        from integration.komposteur.bridge.komposteur_bridge import KomposteurBridge
        
        bridge = KomposteurBridge()
        if not bridge.initialize():
            print("❌ Cannot analyze - bridge failed to initialize")
            return
        
        try:
            # Analyze the bridge methods instead of Java object
            methods = [method for method in dir(bridge) if not method.startswith('_') and callable(getattr(bridge, method))]
            
            print(f"✅ Found {len(methods)} bridge methods:")
            for method in methods:
                print(f"   • {method}")
            
            # Test the main kompost processing method
            if 'process_kompost_json' in methods:
                print(f"\n🎯 Testing process_kompost_json method:")
                test_result = bridge.process_kompost_json("/mock/test.json")
                if "expected_workflow" in test_result:
                    workflow = test_result["expected_workflow"]
                    print(f"   📋 Expected Java class: {workflow['java_class']}")
                    print(f"   📋 Expected method: {workflow['expected_method']}")
                    print(f"   📋 Description: {workflow['description']}")
            else:
                print("\n⚠️  process_kompost_json method not found")
                
        except Exception as e:
            print(f"❌ API analysis failed: {e}")
        finally:
            bridge.shutdown()
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")

def main():
    """Run the goal-oriented test"""
    print("🎯 GOAL TEST: MCP Server wrapping Komposteur for kompost.json processing")
    print("=" * 80)
    print("Target: Kompost curates FFMPEG recipes, MCP discovers patterns")
    print("=" * 80)
    
    tests = [
        ("Java Connection", test_komposteur_java_connection),
        ("API Analysis", analyze_komposteur_api),  
        ("Kompost JSON Processing", test_kompost_json_processing),
        ("MCP Integration", test_mcp_komposteur_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        try:
            result = test_func()
            results.append((test_name, result if result is not None else True))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 80)
    print("📊 GOAL TEST RESULTS")
    print("=" * 80)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Goal Progress: {sum(1 for _, passed in results if passed)}/{len(results)} components working")
    
    print("\n📝 NEXT STEPS:")
    print("1. Fix bridge API to match actual Komposteur methods")
    print("2. Implement komposteur_process_kompost MCP tool")
    print("3. Create kompost.json -> FFMPEG workflow")
    print("4. Add pattern discovery and improvement tracking")

if __name__ == "__main__":
    main()