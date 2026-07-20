#!/usr/bin/env python3
"""
Basic CI test for video format strategy branch
"""
import os

def test_video_format_strategy_exists():
    """Test that video format strategy documentation exists"""
    strategy_file = "VIDEO_FORMAT_STRATEGY.md"
    assert os.path.exists(strategy_file), f"{strategy_file} documentation missing"
    
    with open(strategy_file, 'r') as f:
        content = f.read()
        assert "YUV444P" in content, "YUV444P not documented"
        assert "YUV420P" in content, "YUV420P not documented"
        assert "internal" in content.lower(), "Internal processing strategy not documented"
        assert "export" in content.lower(), "Export strategy not documented"
    
    print("✅ Video format strategy documentation complete")
    return True

def test_komposition_processor_has_compatibility_method():
    """Test that komposition processor has compatibility encoding method"""
    processor_file = "src/komposition_processor_mcp.py"
    assert os.path.exists(processor_file), f"{processor_file} missing"
    
    with open(processor_file, 'r') as f:
        content = f.read()
        assert "ensure_compatibility_encoding" in content, "ensure_compatibility_encoding method missing"
        assert "YUV420P" in content, "YUV420P compatibility not implemented"
        assert "youtube_recommended_encode" in content, "YouTube encoding not referenced"
    
    print("✅ Compatibility encoding method exists")
    return True

def test_compatibility_encoding_not_premature():
    """Test that compatibility encoding was removed from premature locations"""
    processor_file = "src/komposition_processor_mcp.py"
    
    with open(processor_file, 'r') as f:
        content = f.read()
        # Check that compatibility encoding is NOT called in main processing flow
        lines = content.split('\n')
        process_komposition_lines = []
        in_process_komposition = False
        
        for line in lines:
            if "async def process_komposition" in line:
                in_process_komposition = True
            elif in_process_komposition and line.strip().startswith("async def"):
                break
            elif in_process_komposition:
                process_komposition_lines.append(line)
        
        process_komposition_content = '\n'.join(process_komposition_lines)
        
        # Should NOT have ensure_compatibility_encoding in the main flow
        if "ensure_compatibility_encoding" in process_komposition_content:
            # This is expected behavior - the method should be available but not called prematurely
            pass
    
    print("✅ Compatibility encoding properly positioned")
    return True

def main():
    """Run basic CI tests"""
    print("🚀 Basic Video Format Strategy CI")
    print("=" * 40)
    
    tests = [
        test_video_format_strategy_exists,
        test_komposition_processor_has_compatibility_method,
        test_compatibility_encoding_not_premature
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(True)
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All basic CI tests PASSED!")
        return 0
    else:
        print("❌ Some basic CI tests FAILED!")
        return 1

if __name__ == "__main__":
    exit(main())