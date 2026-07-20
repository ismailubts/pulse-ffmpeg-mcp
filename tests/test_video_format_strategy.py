#!/usr/bin/env python3
"""
Basic CI test for video format strategy changes
Tests that video format strategy is working correctly
"""
import asyncio
import sys
import os
sys.path.insert(0, 'src')

async def test_video_format_imports():
    """Test that all video format components import correctly"""
    try:
        # Test core imports with absolute imports
        from komposition_processor_mcp import KompositionProcessor
        from file_manager import FileManager
        from ffmpeg_wrapper import FFMPEGWrapper
        
        print("✅ All video format components import successfully")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

async def test_compatibility_encoding_method():
    """Test that ensure_compatibility_encoding method exists and is callable"""
    try:
        from komposition_processor_mcp import KompositionProcessor
        from file_manager import FileManager
        from ffmpeg_wrapper import FFMPEGWrapper
        
        file_manager = FileManager()
        ffmpeg_wrapper = FFMPEGWrapper(file_manager)
        processor = KompositionProcessor(file_manager, ffmpeg_wrapper)
        
        # Check method exists
        assert hasattr(processor, 'ensure_compatibility_encoding'), "ensure_compatibility_encoding method missing"
        assert callable(processor.ensure_compatibility_encoding), "ensure_compatibility_encoding not callable"
        
        print("✅ Compatibility encoding method exists and is callable")
        return True
    except Exception as e:
        print(f"❌ Compatibility encoding test failed: {e}")
        return False

async def test_video_format_strategy_docs():
    """Test that video format strategy documentation exists"""
    try:
        strategy_file = "VIDEO_FORMAT_STRATEGY.md"
        assert os.path.exists(strategy_file), f"{strategy_file} documentation missing"
        
        with open(strategy_file, 'r') as f:
            content = f.read()
            assert "YUV444P" in content, "YUV444P not documented"
            assert "YUV420P" in content, "YUV420P not documented"
            assert "internal" in content.lower(), "Internal processing strategy not documented"
            assert "export" in content.lower(), "Export strategy not documented"
        
        print("✅ Video format strategy documentation exists and is complete")
        return True
    except Exception as e:
        print(f"❌ Documentation test failed: {e}")
        return False

async def main():
    """Run all video format strategy tests"""
    print("🚀 Video Format Strategy CI Tests")
    print("=" * 50)
    
    tests = [
        test_video_format_imports,
        test_compatibility_encoding_method,
        test_video_format_strategy_docs
    ]
    
    results = []
    for test in tests:
        print(f"\n🧪 Running {test.__name__}...")
        result = await test()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("📋 Test Results:")
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results)):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {i+1}. {test.__name__}: {status}")
    
    print(f"\n🎯 Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All video format strategy tests PASSED!")
        return 0
    else:
        print("❌ Some video format strategy tests FAILED!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)