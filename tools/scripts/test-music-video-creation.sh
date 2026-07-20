#!/bin/bash
set -e

echo "🎵 PULSE FFMPEG MCP - Music Video Creation Test"
echo "=============================================="
echo ""

# Configuration
YOUTUBE_URLS=("Xjz9swW9Pg0" "tNCPEtMqGcM" "FrmUdNupdq4")
WAV_FILE="Set 21 Rec 2.wav"
BPM=120
SEGMENTS=12
BEATS_PER_SEGMENT=4

echo "📋 Test Configuration:"
echo "   YouTube Shorts: ${#YOUTUBE_URLS[@]} videos"
echo "   Audio File: $WAV_FILE"
echo "   BPM: $BPM"
echo "   Segments: $SEGMENTS x $BEATS_PER_SEGMENT beats each"
echo ""

# Start MCP server test
echo "🚀 Testing MCP Server Connection..."
PYTHONPATH=. .venv/bin/python -c "
import asyncio
import sys
sys.path.insert(0, 'src')

async def test_mcp_connection():
    try:
        from server import mcp
        result = await mcp.call_tool('list_files', {})
        print(f'✅ MCP Server responding - found {len(result.get(\"files\", []))} source files')
        return True
    except Exception as e:
        print(f'❌ MCP Server error: {e}')
        return False

success = asyncio.run(test_mcp_connection())
sys.exit(0 if success else 1)
"

if [ $? -ne 0 ]; then
    echo "❌ MCP Server not responding. Please start the server first."
    exit 1
fi

echo ""
echo "🎬 Creating Music Video with MCP Tools..."

# Create the music video using MCP
PYTHONPATH=. .venv/bin/python -c "
import asyncio
import sys
sys.path.insert(0, 'src')

async def create_music_video():
    try:
        from server import mcp
        
        # Step 1: Download YouTube shorts
        print('📥 Downloading YouTube shorts...')
        youtube_urls = [
            'https://www.youtube.com/watch?v=Xjz9swW9Pg0',
            'https://www.youtube.com/watch?v=tNCPEtMqGcM', 
            'https://www.youtube.com/watch?v=FrmUdNupdq4'
        ]
        
        download_result = await mcp.call_tool('batch_download_urls', {
            'urls': youtube_urls,
            'quality': '720p',
            'max_concurrent': 3
        })
        
        if not download_result.get('success'):
            print('❌ Failed to download YouTube videos')
            return False
            
        downloaded_files = download_result.get('successful_downloads', [])
        print(f'✅ Downloaded {len(downloaded_files)} YouTube videos')
        
        # Step 2: List all available files
        files_result = await mcp.call_tool('list_files', {})
        files = files_result.get('files', [])
        audio_file = None
        
        for file in files:
            if file['name'] == 'Set 21 Rec 2.wav':
                audio_file = file['id']
                break
                
        if not audio_file:
            print('❌ Audio file Set 21 Rec 2.wav not found')
            return False
            
        print(f'✅ Found audio file: {audio_file}')
        
        # Step 3: Analyze video content
        print('🧠 Analyzing video content with AI...')
        video_analyses = []
        for download in downloaded_files:
            file_id = download['file_id']
            analysis = await mcp.call_tool('analyze_video_content', {
                'file_id': file_id,
                'force_reanalysis': False
            })
            video_analyses.append({
                'file_id': file_id,
                'analysis': analysis
            })
            print(f'✅ Analyzed video {file_id}')
        
        # Step 4: Generate komposition from natural language description
        description = '''
        Create a music video from these YouTube shorts: Xjz9swW9Pg0, tNCPEtMqGcM, FrmUdNupdq4. 
        Add Set 21 Rec 2.wav as background music at 120 BPM. 
        Extract segments from the shorts and take 12 of those segments, playing for 4 beats each. 
        Create an old school vibe over it all, and fade to white between the segments.
        '''
        
        print('📝 Generating komposition JSON from natural language...')
        komposition_result = await mcp.call_tool('generate_komposition_from_description', {
            'description': description.strip(),
            'title': 'YouTube Shorts Old School Music Video',
            'custom_bpm': 120
        })
        
        if not komposition_result.get('success'):
            print('❌ Failed to generate komposition JSON')
            return False
            
        komposition_file = komposition_result.get('komposition_file')
        print(f'✅ Generated komposition: {komposition_file}')
        
        # Step 5: Process komposition with Komposteur
        print('🎬 Processing komposition with Komposteur...')
        video_result = await mcp.call_tool('process_komposition_file', {
            'komposition_path': komposition_file
        })
        
        if video_result.get('success'):
            print('✅ Music video created successfully!')
            print(f'   Komposition segments: {komposition_result.get(\"summary\", {}).get(\"segments\", 0)}')
            print(f'   Komposition effects: {komposition_result.get(\"summary\", {}).get(\"effects\", 0)}')
            print(f'   Video processing time: {video_result.get(\"processing_time\", 0):.1f}s')
            
            # Show komposition file content preview
            print('\\n📋 Generated Komposition JSON Preview:')
            try:
                import json
                with open(komposition_file, 'r') as f:
                    komposition_data = json.load(f)
                    print(f'   Title: {komposition_data.get(\"metadata\", {}).get(\"title\", \"N/A\")}')
                    print(f'   BPM: {komposition_data.get(\"metadata\", {}).get(\"bpm\", \"N/A\")}')
                    print(f'   Duration: {komposition_data.get(\"metadata\", {}).get(\"estimatedDuration\", \"N/A\")}s')
                    segments = komposition_data.get(\"segments\", [])
                    print(f'   Segments: {len(segments)}')
                    if segments:
                        print(f'   First segment: {segments[0].get(\"id\", \"unknown\")}')
            except Exception as e:
                print(f'   Error reading komposition: {e}')
                
            return True
        else:
            print('❌ Music video creation failed')
            print(f'   Komposition generation: {\"✅\" if komposition_result.get(\"success\") else \"❌\"}')
            print(f'   Video processing error: {video_result}')
            return False
            
    except Exception as e:
        print(f'❌ Unexpected error: {e}')
        import traceback
        traceback.print_exc()
        return False

success = asyncio.run(create_music_video())
sys.exit(0 if success else 1)
"

TEST_EXIT_CODE=$?

echo ""
echo "📊 Test Results:"
echo "================"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ Music video creation test PASSED!"
    echo ""
    echo "🎯 Generated files:"
    
    # List generated files
    PYTHONPATH=. .venv/bin/python -c "
import asyncio
import sys
sys.path.insert(0, 'src')

async def list_generated():
    try:
        from server import mcp
        result = await mcp.call_tool('list_generated_files', {})
        files = result.get('generated_files', [])
        
        # Show most recent 5 files
        recent_files = sorted(files, key=lambda x: x.get('created', 0), reverse=True)[:5]
        
        for i, file in enumerate(recent_files, 1):
            size_mb = file.get('size', 0) / (1024*1024)
            print(f'   {i}. {file.get(\"name\", \"unknown\")} ({size_mb:.1f}MB)')
            
    except Exception as e:
        print(f'   Error listing files: {e}')

asyncio.run(list_generated())
"
    
    echo ""
    echo "✨ Next steps:"
    echo "   - Check generated videos in /tmp/music/temp/"
    echo "   - Use list_generated_files() to get file IDs"
    echo "   - Apply additional effects or export"
    
else
    echo "❌ Music video creation test FAILED!"
    echo ""
    echo "🔍 Troubleshooting:"
    echo "   - Check MCP server is running: uv run python -m src.server"
    echo "   - Verify YouTube URLs are accessible"
    echo "   - Check audio file exists: ls -la /tmp/music/source/"
    echo "   - Review error messages above"
fi

echo ""
echo "🏁 Test completed with exit code: $TEST_EXIT_CODE"
exit $TEST_EXIT_CODE