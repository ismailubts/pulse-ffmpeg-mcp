#!/bin/bash
# Multi-LLM Music Video Creator
# Compare different LLMs (Haiku, Gemini) for music video creation

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}🎬 $1${NC}"
    echo "================================"
}

print_step() {
    echo -e "${YELLOW}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check API keys
print_step "Checking API keys..."

if [[ -z "$ANTHROPIC_API_KEY" ]]; then
    print_error "ANTHROPIC_API_KEY not set"
    echo "Run: export ANTHROPIC_API_KEY='your-anthropic-key'"
    echo ""
    echo "To get an API key:"
    echo "1. Go to: https://console.anthropic.com/account/keys"
    echo "2. Create a new API key"
    echo "3. Export it: export ANTHROPIC_API_KEY='sk-ant-api03-...'"
    exit 1
else
    print_success "ANTHROPIC_API_KEY is set (${#ANTHROPIC_API_KEY} chars)"
fi

if [[ -z "$GEMINI_API_KEY" ]]; then
    print_error "GEMINI_API_KEY not set (fallback LLM)"
    echo "Run: export GEMINI_API_KEY='your-google-api-key'"
    echo ""
    echo "To get a Google API key:"
    echo "1. Go to: https://aistudio.google.com/app/apikey"
    echo "2. Create a new API key"
    echo "3. Export it: export GEMINI_API_KEY='your-key-here'"
    echo ""
    echo "⚠️  Continuing with only Anthropic API key (may cause fallback failures)"
else
    print_success "GEMINI_API_KEY is set (${#GEMINI_API_KEY} chars)"
fi

print_header "Multi-LLM Music Video Creator"

# Get user request
if [[ $# -eq 0 ]]; then
    echo "Examples:"
    echo "  './multi-llm-music-video.sh \"Create a 15-second energetic video\"'"
    echo "  './multi-llm-music-video.sh \"Make a cinematic video with slow fades\"'"
    echo ""
    read -p "🎬 Your request: " USER_REQUEST
else
    USER_REQUEST="$*"
fi

echo "Request: \"$USER_REQUEST\""
echo ""

# Create output directory
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p /tmp/pulse/ffmpeg-mcp/generated-videos

print_step "Getting available LLM models..."

# Get LLM stats to see available models
cat > test_llms.ts << EOF
import { HaikuMCPClient } from './client.ts';

async function testMultipleLLMs() {
  const client = new HaikuMCPClient();
  
  try {
    await client.connect();
    
    // Get available files
    const filesList = await client.callTool('list_files', {});
    const files = JSON.parse(filesList.content[0].text).files;
    
    const videoFile = files.find(f => f.mediaType === 'video');
    const audioFile = files.find(f => f.mediaType === 'audio');
    
    if (!videoFile || !audioFile) {
      throw new Error('No video or audio files found');
    }
    
    console.log('🎬 Files selected:');
    console.log('📹 Video:', videoFile.id, '-', videoFile.path.split('/').pop());
    console.log('🎵 Audio:', audioFile.id, '-', audioFile.path.split('/').pop());
    console.log('');
    
    // Get LLM stats
    const statsResponse = await client.callTool('get_llm_stats', {});
    const stats = JSON.parse(statsResponse.content[0].text);
    
    console.log('🤖 Available Models:');
    console.log('Primary:', stats.primary_model.provider, stats.primary_model.model, '(\$' + stats.estimated_costs.primary_per_1k_tokens + '/1k tokens)');
    console.log('Fallback:', stats.fallback_model.provider, stats.fallback_model.model, '(\$' + stats.estimated_costs.fallback_per_1k_tokens + '/1k tokens)');
    console.log('');
    
    // Create music video (using primary model - Haiku)
    console.log('🎬 Creating video with', stats.primary_model.model, '...');
    const response = await client.callTool('create_music_video', {
      video_file: videoFile.id,
      audio_file: audioFile.id,
      output_file: '/tmp/pulse/ffmpeg-mcp/generated-videos/multi_llm_${TIMESTAMP}.mp4',
      duration: 18,
      start_time: 0
    });
    
    const result = JSON.parse(response.content[0].text);
    
    console.log('');
    if (result.success) {
      console.log('✅ Success with', stats.primary_model.model);
      console.log('📁 Output: multi_llm_${TIMESTAMP}.mp4');
      console.log('💰 Cost: \$' + (result.llm_cost || 0).toFixed(6));
      console.log('⏱️  Processing: ' + (result.execution_time_ms || 0) + 'ms');
      console.log('🛠️  Generated Command:');
      console.log('   ', result.command_used);
    } else {
      console.log('❌ Failed with', stats.primary_model.model);
      console.log('Error:', result.error);
      console.log('Command attempted:', result.command_used);
    }
    
    await client.disconnect();
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

testMultipleLLMs();
EOF

# Run the test
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY npx tsx test_llms.ts

echo ""

# Check results
OUTPUT_FILE="/tmp/pulse/ffmpeg-mcp/generated-videos/multi_llm_${TIMESTAMP}.mp4"

if [[ -f "$OUTPUT_FILE" ]]; then
    FILE_SIZE=$(stat -f%z "$OUTPUT_FILE" 2>/dev/null || stat -c%s "$OUTPUT_FILE" 2>/dev/null || echo "0")
    SIZE_MB=$((FILE_SIZE / 1024 / 1024))
    
    print_success "Final video: $OUTPUT_FILE (${SIZE_MB}MB)"
    
    # Get duration if possible
    if command -v ffprobe >/dev/null 2>&1; then
        DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUTPUT_FILE" 2>/dev/null || echo "unknown")
        echo "Duration: ${DURATION}s"
    fi
    
    # Offer to play
    if [[ "$OSTYPE" == "darwin"* ]] && command -v open >/dev/null 2>&1; then
        echo ""
        read -p "🎬 Open video? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            open "$OUTPUT_FILE"
        fi
    fi
else
    print_error "Video was not created successfully"
fi

# Cleanup
rm -f test_llms.ts

print_header "Multi-LLM Test Complete"
echo "You can compare different LLM outputs by running this script multiple times"
echo "or by modifying the server configuration to switch between Haiku and Gemini."