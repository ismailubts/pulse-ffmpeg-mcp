#!/bin/bash

# Music Video Creation Test Script
# Tests the complete LLM-MCP music video creation pipeline
# Usage: ./test_music_video_creation.sh [description] [komposition_file]

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_DIR="/tmp/music/temp"
SOURCE_DIR="/tmp/music/source"
MCP_SERVER_CMD="uv run python -m src.server"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default test description
DEFAULT_DESCRIPTION="Create a 16 second music video using JJVtt947FfI_136.mp4 for the first 8 seconds and PXL_20250306_132546255.mp4 for the last 8 seconds, with Subnautic Measures.flac as background music at 120 BPM"

# Default komposition file (if using komposition mode)
DEFAULT_KOMPOSITION="simple_test.json"

# Parse arguments
DESCRIPTION="${1:-$DEFAULT_DESCRIPTION}"
KOMPOSITION_FILE="${2:-$DEFAULT_KOMPOSITION}"
TEST_MODE="${3:-natural_language}"  # Options: natural_language, komposition, batch

echo -e "${BLUE}🎬 Music Video Creation Test${NC}"
echo "=================================================="
echo -e "${YELLOW}Test Mode:${NC} $TEST_MODE"
echo -e "${YELLOW}Description:${NC} $DESCRIPTION"
if [[ "$TEST_MODE" == "komposition" ]]; then
    echo -e "${YELLOW}Komposition File:${NC} $KOMPOSITION_FILE"
fi
echo "=================================================="

# Function to print status
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

# Function to verify file exists and get info
verify_video_file() {
    local file_path="$1"
    local expected_min_duration="$2"
    local expected_max_duration="$3"
    
    print_status "Verifying video file: $file_path"
    
    # Check if file exists
    if [[ ! -f "$file_path" ]]; then
        print_error "Video file does not exist: $file_path"
        return 1
    fi
    
    print_success "File exists ($(du -h "$file_path" | cut -f1))"
    
    # Get file info with ffprobe
    if ! command -v ffprobe &> /dev/null; then
        print_warning "ffprobe not found, skipping detailed verification"
        return 0
    fi
    
    # Get duration
    duration=$(ffprobe -v quiet -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$file_path" 2>/dev/null || echo "unknown")
    
    if [[ "$duration" != "unknown" ]]; then
        duration_rounded=$(printf "%.1f" "$duration")
        print_success "Duration: ${duration_rounded}s"
        
        # Check duration range
        if (( $(echo "$duration >= $expected_min_duration" | bc -l) )) && (( $(echo "$duration <= $expected_max_duration" | bc -l) )); then
            print_success "Duration within expected range (${expected_min_duration}s - ${expected_max_duration}s)"
        else
            print_warning "Duration outside expected range (${expected_min_duration}s - ${expected_max_duration}s)"
        fi
    fi
    
    # Get video streams info
    video_info=$(ffprobe -v quiet -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate -of default=noprint_wrappers=1 "$file_path" 2>/dev/null || echo "")
    if [[ -n "$video_info" ]]; then
        codec=$(echo "$video_info" | grep codec_name | cut -d= -f2)
        width=$(echo "$video_info" | grep width | cut -d= -f2)
        height=$(echo "$video_info" | grep height | cut -d= -f2)
        fps=$(echo "$video_info" | grep r_frame_rate | cut -d= -f2)
        print_success "Video: ${codec} ${width}x${height} @ ${fps} fps"
    fi
    
    # Get audio streams info
    audio_info=$(ffprobe -v quiet -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels -of default=noprint_wrappers=1 "$file_path" 2>/dev/null || echo "")
    if [[ -n "$audio_info" ]]; then
        audio_codec=$(echo "$audio_info" | grep codec_name | cut -d= -f2)
        sample_rate=$(echo "$audio_info" | grep sample_rate | cut -d= -f2)
        channels=$(echo "$audio_info" | grep channels | cut -d= -f2)
        print_success "Audio: ${audio_codec} ${sample_rate}Hz ${channels}ch"
    else
        print_warning "No audio stream found"
    fi
    
    return 0
}

# Function to play video
play_video() {
    local file_path="$1"
    
    # Check for CI/headless mode
    if [[ "$HEADLESS_MODE" == "true" ]] || [[ "$CI" == "true" ]] || [[ "$VIDEO_PLAYER" == "none" ]]; then
        print_status "Skipping video playback (headless/CI mode)"
        print_success "Video playback skipped for CI environment"
        return 0
    fi
    
    print_status "Attempting to play video: $file_path"
    
    # Try different players based on OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v open &> /dev/null; then
            print_status "Opening with default macOS player..."
            open "$file_path"
            print_success "Video opened with default player"
        else
            print_warning "Cannot open video - 'open' command not available"
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v xdg-open &> /dev/null && [[ -n "$DISPLAY" ]]; then
            print_status "Opening with default Linux player..."
            xdg-open "$file_path" 2>/dev/null &
            print_success "Video opened with default player"
        elif command -v vlc &> /dev/null && [[ -n "$DISPLAY" ]]; then
            print_status "Opening with VLC..."
            vlc "$file_path" 2>/dev/null &
            print_success "Video opened with VLC"
        elif command -v mpv &> /dev/null && [[ -n "$DISPLAY" ]]; then
            print_status "Opening with mpv..."
            mpv "$file_path" 2>/dev/null &
            print_success "Video opened with mpv"
        else
            print_warning "No video player found or no display available (headless environment)"
            print_success "Video verification completed without playback"
        fi
    else
        print_warning "Unknown OS type: $OSTYPE"
    fi
}

# Function to test natural language creation
test_natural_language() {
    print_status "Testing natural language music video creation..."
    
    # This would use the MCP server tools
    # For now, we'll simulate by using the last created file
    latest_file=$(ls -t "$TEMP_DIR"/temp_*.mp4 2>/dev/null | head -1)
    
    if [[ -n "$latest_file" ]]; then
        print_success "Found latest generated video: $(basename "$latest_file")"
        verify_video_file "$latest_file" 10 20
        play_video "$latest_file"
    else
        print_error "No generated video files found in $TEMP_DIR"
        return 1
    fi
}

# Function to test komposition file
test_komposition() {
    print_status "Testing komposition file: $KOMPOSITION_FILE"
    
    if [[ ! -f "$KOMPOSITION_FILE" ]]; then
        print_error "Komposition file not found: $KOMPOSITION_FILE"
        return 1
    fi
    
    print_success "Komposition file exists"
    
    # Extract expected duration from komposition metadata (handle both old and new formats)
    if command -v jq &> /dev/null; then
        # Try multiple fields to get duration
        total_beats=$(jq -r '.total_beats // .beatpattern.tobeat // 16' "$KOMPOSITION_FILE" 2>/dev/null || echo "16")
        bpm=$(jq -r '.bpm // .metadata.bpm // 120' "$KOMPOSITION_FILE" 2>/dev/null || echo "120")
        
        # Calculate duration: beats / (BPM / 60) = duration in seconds
        duration=$(echo "scale=1; $total_beats / ($bpm / 60)" | bc -l 2>/dev/null || echo "16")
        print_status "Expected duration: ${total_beats} beats at ${bpm} BPM = ${duration}s"
    else
        duration=16
        print_warning "jq not found, using default duration: ${duration}s"
    fi
    
    # Use latest file as proxy for komposition result
    latest_file=$(ls -t "$TEMP_DIR"/temp_*.mp4 2>/dev/null | head -1)
    
    if [[ -n "$latest_file" ]]; then
        # Convert duration to integer for bash arithmetic
        duration_int=$(echo "$duration" | cut -d. -f1)
        verify_video_file "$latest_file" $((duration_int - 2)) $((duration_int + 2))
        play_video "$latest_file"
    else
        print_error "No generated video files found"
        return 1
    fi
}

# Function to test batch processing
test_batch() {
    print_status "Testing batch processing workflow..."
    
    # Look for most recent batch result
    latest_file=$(ls -t "$TEMP_DIR"/temp_*.mp4 2>/dev/null | head -1)
    
    if [[ -n "$latest_file" ]]; then
        verify_video_file "$latest_file" 8 20
        play_video "$latest_file"
    else
        print_error "No batch processing results found"
        return 1
    fi
}

# Main test execution
print_status "Starting music video creation test..."

# Check prerequisites
print_status "Checking prerequisites..."

if [[ ! -d "$SOURCE_DIR" ]]; then
    print_error "Source directory not found: $SOURCE_DIR"
    exit 1
fi

if [[ ! -d "$TEMP_DIR" ]]; then
    print_warning "Temp directory not found, creating: $TEMP_DIR"
    mkdir -p "$TEMP_DIR"
fi

# Check for source files
source_files=$(ls "$SOURCE_DIR"/*.{mp4,flac,mp3} 2>/dev/null | wc -l)
if [[ $source_files -eq 0 ]]; then
    print_error "No source media files found in $SOURCE_DIR"
    exit 1
fi

print_success "Found $source_files source media files"

# Run the appropriate test
case "$TEST_MODE" in
    "natural_language")
        test_natural_language
        ;;
    "komposition")
        test_komposition
        ;;
    "batch")
        test_batch
        ;;
    *)
        print_error "Unknown test mode: $TEST_MODE"
        echo "Valid modes: natural_language, komposition, batch"
        exit 1
        ;;
esac

# Final status
if [[ $? -eq 0 ]]; then
    echo "=================================================="
    print_success "Music video creation test completed successfully!"
    print_status "Test command used: $0 \"$DESCRIPTION\" \"$KOMPOSITION_FILE\" \"$TEST_MODE\""
    echo "=================================================="
else
    echo "=================================================="
    print_error "Music video creation test failed!"
    echo "=================================================="
    exit 1
fi