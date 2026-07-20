#!/usr/bin/env python3
"""
Simple transition test to debug parameter issues
"""

import asyncio
import sys
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from server import process_file
from server import list_files

async def test_simple_transition():
    """Test basic transition using MCP server functions directly"""
    
    print("🧪 Simple Transition Test")
    print("=" * 30)
    
    # List available files
    files_result = await list_files()
    print(f"Available files: {len(files_result['files'])}")
    
    # Find two video files
    video_files = [f for f in files_result['files'] if f['file_id'].endswith('.mp4') or f['media_type'] == 'video']
    
    if len(video_files) < 2:
        print("❌ Need at least 2 video files")
        return
    
    file1 = video_files[0]['file_id']
    file2 = video_files[1]['file_id']
    
    print(f"Using files: {file1}, {file2}")
    
    # Test direct crossfade operation
    try:
        print("Testing crossfade_transition operation directly...")
        result = await process_file(
            input_file_id=file1,
            operation="crossfade_transition",
            output_extension="mp4",
            params=f"second_video={file2} duration=2.0 offset=1.0"
        )
        
        if result.success:
            print(f"✅ Crossfade test successful: {result.output_file_id}")
            print(f"   Output size: {result.processing_details.get('output_size_bytes', 'unknown')} bytes")
        else:
            print(f"❌ Crossfade test failed: {result.error}")
            
    except Exception as e:
        print(f"❌ Exception during crossfade test: {e}")
    
    # Test gradient wipe
    try:
        print("\nTesting gradient_wipe operation directly...")
        result = await process_file(
            input_file_id=file1,
            operation="gradient_wipe",
            output_extension="mp4", 
            params=f"second_video={file2} duration=1.5 offset=0.5"
        )
        
        if result.success:
            print(f"✅ Gradient wipe test successful: {result.output_file_id}")
        else:
            print(f"❌ Gradient wipe test failed: {result.error}")
            
    except Exception as e:
        print(f"❌ Exception during gradient wipe test: {e}")

if __name__ == "__main__":
    asyncio.run(test_simple_transition())