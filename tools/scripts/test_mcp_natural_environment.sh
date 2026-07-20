#!/bin/bash

# MCP Server Natural Environment Test
# Tests music video creation through actual MCP tool calls
# This simulates how Claude Code would interact with the MCP server

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}🎬 $1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Test description (can be overridden)
TEST_DESCRIPTION="${1:-Create a 16 second music video using JJVtt947FfI_136.mp4 for the first 8 seconds and PXL_20250306_132546255.mp4 for the last 8 seconds, with Subnautic Measures.flac as background music at 120 BPM}"

print_header "MCP Server Natural Environment Test"
echo "Description: $TEST_DESCRIPTION"
echo ""

# Function to simulate MCP tool call via Claude Code
call_mcp_tool() {
    local tool_name="$1"
    local params="$2"
    local description="$3"
    
    print_status "Calling MCP tool: $tool_name"
    echo "Parameters: $params"
    echo "Purpose: $description"
    
    # This is where we would make the actual MCP call
    # In the real environment, Claude Code would call:
    # mcp__ffmpeg-mcp__${tool_name}(${params})
    
    echo "📞 MCP Call: mcp__ffmpeg-mcp__${tool_name}(${params})"
    
    # For simulation, we'll provide expected response format
    case "$tool_name" in
        "list_files")
            echo "Expected Response: List of available video/audio files with IDs"
            ;;
        "create_video_from_description")
            echo "Expected Response: Processing steps and output file ID"
            ;;
        "get_file_info")
            echo "Expected Response: Video metadata (duration, resolution, codecs)"
            ;;
        "list_generated_files")
            echo "Expected Response: List of generated files in temp directory"
            ;;
    esac
    
    echo ""
}

# Test Step 1: List Available Files
print_status "Step 1: Discovering available media files"
call_mcp_tool "list_files" "" "Get list of source videos and audio files"

# Test Step 2: Create Video from Natural Language
print_status "Step 2: Creating video from natural language description"
call_mcp_tool "create_video_from_description" "description='$TEST_DESCRIPTION', execution_mode='full'" "Convert natural language to music video"

# Test Step 3: List Generated Files
print_status "Step 3: Checking generated files"
call_mcp_tool "list_generated_files" "" "Find the created video file"

# Test Step 4: Get File Info
print_status "Step 4: Verifying video properties"
call_mcp_tool "get_file_info" "file_id='OUTPUT_FILE_ID'" "Validate video specs and quality"

# Test Step 5: Verification Script
print_status "Step 5: Running verification against actual file"
echo "🔍 This would run: ./test_music_video_creation.sh to verify the actual output"

print_header "Natural Environment Test Simulation Complete"

echo ""
echo "📋 To run this test in Claude Code natural environment:"
echo ""
echo "1. Ensure MCP server is configured in Claude Code settings"
echo "2. Start a conversation with Claude Code"
echo "3. Provide this natural language instruction:"
echo ""
echo "   '$TEST_DESCRIPTION'"
echo ""
echo "4. Claude Code should automatically:"
echo "   - Call mcp__ffmpeg-mcp__list_files()"
echo "   - Call mcp__ffmpeg-mcp__create_video_from_description()"
echo "   - Get the output file ID"
echo "   - Verify the result with get_file_info()"
echo ""
echo "5. Then run verification:"
echo "   ./test_music_video_creation.sh"
echo ""

# Create a test instruction file for Claude Code
cat > mcp_test_instruction.md << 'EOF'
# MCP Server Test Instruction for Claude Code

## Natural Language Test
Please create a music video using the following description:

**"Create a 16 second music video using JJVtt947FfI_136.mp4 for the first 8 seconds and PXL_20250306_132546255.mp4 for the last 8 seconds, with Subnautic Measures.flac as background music at 120 BPM"**

## Expected MCP Tool Workflow
1. `mcp__ffmpeg-mcp__list_files()` - Check available media
2. `mcp__ffmpeg-mcp__create_video_from_description()` - Generate video
3. `mcp__ffmpeg-mcp__get_file_info()` - Verify output
4. Run `./test_music_video_creation.sh` to validate result

## Success Criteria
- Video file created in `/tmp/music/temp/`
- Duration approximately 16 seconds
- Contains both video segments
- Background music integrated
- Passes verification script

## Alternative Test Scenarios
- "Make a short music video with smooth transitions"
- "Create beat-synchronized video at 135 BPM"
- "Build video montage with available files and music"
EOF

print_success "Created mcp_test_instruction.md for Claude Code testing"

echo ""
echo "🎯 Next Steps:"
echo "1. Open Claude Code in environment with MCP server configured"
echo "2. Copy instruction from mcp_test_instruction.md"
echo "3. Paste into Claude Code conversation"
echo "4. Watch MCP tools being called automatically"
echo "5. Run ./test_music_video_creation.sh to verify result"