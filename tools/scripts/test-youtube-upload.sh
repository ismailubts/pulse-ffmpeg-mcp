#!/bin/bash

# YouTube Upload Test Script
# Tests the complete YouTube upload workflow with the MCP server

set -e  # Exit on any error

echo "🎬 YouTube Upload Test Script"
echo "============================="

# Configuration
MCP_SERVER_PATH="."
VENV_PATH="$MCP_SERVER_PATH/.venv"
PYTHON_CMD="$VENV_PATH/bin/python"
TEST_DESCRIPTION="Create a 30-second YouTube Short with seamless looping"
VIDEO_TITLE="Test YouTube Short - MCP Generated"
VIDEO_DESCRIPTION="Test upload from MCP FFMPEG Server with automated video processing"
VIDEO_TAGS="test,mcp,youtube,shorts,ai"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if in correct directory
    if [[ ! -f "$MCP_SERVER_PATH/src/server.py" ]]; then
        log_error "MCP server not found at $MCP_SERVER_PATH"
        exit 1
    fi
    
    # Check virtual environment
    if [[ ! -f "$PYTHON_CMD" ]]; then
        log_error "Python virtual environment not found at $VENV_PATH"
        exit 1
    fi
    
    # Check YouTube credentials
    if [[ -z "$YOUTUBE_CREDENTIALS_FILE" ]]; then
        log_warning "YOUTUBE_CREDENTIALS_FILE not set. You'll need OAuth2 credentials for upload testing."
        log_info "Download client_secrets.json from Google Cloud Console and set:"
        log_info "export YOUTUBE_CREDENTIALS_FILE=/path/to/client_secrets.json"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_success "Prerequisites checked"
}

# Test MCP server availability
test_mcp_server() {
    log_info "Testing MCP server availability..."
    
    cd "$MCP_SERVER_PATH"
    PYTHONPATH="$MCP_SERVER_PATH" "$PYTHON_CMD" -c "
import sys
sys.path.insert(0, 'src')
try:
    from src.youtube_upload_service import YouTubeUploadService
    print('✅ YouTube upload service available')
    
    from src.file_manager import FileManager
    print('✅ File manager available')
    
    # Test MCP server functions availability
    from src import server
    print('✅ MCP server imports successfully')
    
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
" || {
        log_error "MCP server components not available"
        exit 1
    }
    
    log_success "MCP server is available"
}

# List available source files
list_source_files() {
    log_info "Listing available source files..."
    
    cd "$MCP_SERVER_PATH"
    PYTHONPATH="$MCP_SERVER_PATH" "$PYTHON_CMD" -c "
import asyncio
import sys
sys.path.insert(0, 'src')

async def list_files():
    try:
        from server import list_files as mcp_list_files
        result = await mcp_list_files()
        
        if result.get('success') and result.get('files'):
            print(f'📁 Found {len(result[\"files\"])} source files:')
            for i, file in enumerate(result['files'][:5]):  # Show first 5
                print(f'  {i+1}. {file[\"filename\"]} ({file[\"size\"]/1024/1024:.1f} MB)')
            
            if len(result['files']) > 5:
                print(f'  ... and {len(result[\"files\"])-5} more files')
        else:
            print('⚠️  No source files found')
            
    except Exception as e:
        print(f'❌ Error listing files: {e}')
        return False
    return True

success = asyncio.run(list_files())
if not success:
    sys.exit(1)
"
}

# Create a test YouTube Short
create_test_short() {
    log_info "Creating test YouTube Short..."
    
    cd "$MCP_SERVER_PATH"
    PYTHONPATH="$MCP_SERVER_PATH" "$PYTHON_CMD" -c "
import asyncio
import sys
sys.path.insert(0, 'src')

async def create_video():
    try:
        from server import create_video_from_description
        
        description = '$TEST_DESCRIPTION'
        print(f'🎬 Creating video: {description}')
        
        result = await create_video_from_description(description)
        
        if result.get('success'):
            print('✅ Video created successfully!')
            print(f'📱 File ID: {result.get(\"final_video_file_id\", \"unknown\")}')
            
            workflow = result.get('workflow_summary', {})
            if workflow:
                print('📊 Workflow Summary:')
                for key, value in workflow.items():
                    print(f'   {key}: {value}')
            
            # Save file ID for next step
            with open('/tmp/test_video_id.txt', 'w') as f:
                f.write(result.get('final_video_file_id', ''))
                
        else:
            error = result.get('error', 'Unknown error')
            print(f'❌ Video creation failed: {error}')
            return False
            
    except Exception as e:
        print(f'❌ Exception during video creation: {e}')
        return False
        
    return True

success = asyncio.run(create_video())
if not success:
    sys.exit(1)
" || {
        log_error "Failed to create test video"
        exit 1
    }
    
    log_success "Test video created"
}

# Validate video for YouTube Shorts
validate_for_youtube() {
    log_info "Validating video for YouTube Shorts..."
    
    if [[ ! -f "/tmp/test_video_id.txt" ]]; then
        log_error "No video ID found from previous step"
        exit 1
    fi
    
    VIDEO_ID=$(cat /tmp/test_video_id.txt)
    
    cd "$MCP_SERVER_PATH"
    PYTHONPATH="$MCP_SERVER_PATH" "$PYTHON_CMD" -c "
import asyncio
import sys
sys.path.insert(0, 'src')

async def validate_video():
    try:
        from server import validate_youtube_video
        
        video_id = '$VIDEO_ID'
        print(f'🔍 Validating video: {video_id}')
        
        result = await validate_youtube_video(video_id)
        
        if result.get('valid'):
            print('✅ Video meets YouTube Shorts requirements!')
            
            # Show validation details
            print('📋 Validation Results:')
            print(f'   File Size: {result.get(\"file_size_mb\", \"unknown\")} MB')
            print(f'   Duration: {result.get(\"duration\", \"unknown\")} seconds')
            print(f'   Resolution: {result.get(\"resolution\", \"unknown\")}')
            print(f'   Aspect Ratio: {result.get(\"aspect_ratio\", \"unknown\")}')
            
            checks = result.get('checks', {})
            print('✅ Passed Checks:')
            for check, passed in checks.items():
                if passed:
                    print(f'   ✓ {check}')
                else:
                    print(f'   ✗ {check}')
            
            recommendations = result.get('recommendations', [])
            if recommendations:
                print('💡 Recommendations:')
                for rec in recommendations:
                    print(f'   • {rec}')
                    
        else:
            error = result.get('error', 'Validation failed')
            print(f'❌ Validation failed: {error}')
            return False
            
    except Exception as e:
        print(f'❌ Exception during validation: {e}')
        return False
        
    return True

success = asyncio.run(validate_video())
if not success:
    sys.exit(1)
" || {
        log_error "Video validation failed"
        exit 1
    }
    
    log_success "Video validation passed"
}

# Test upload to YouTube (dry run or actual)
test_youtube_upload() {
    local dry_run="${1:-true}"
    
    if [[ "$dry_run" == "true" ]]; then
        log_info "Testing YouTube upload (dry run - no actual upload)..."
    else
        log_info "Uploading to YouTube (REAL UPLOAD)..."
    fi
    
    if [[ ! -f "/tmp/test_video_id.txt" ]]; then
        log_error "No video ID found from previous step"
        exit 1
    fi
    
    VIDEO_ID=$(cat /tmp/test_video_id.txt)
    
    cd "$MCP_SERVER_PATH"
    PYTHONPATH="$MCP_SERVER_PATH" "$PYTHON_CMD" -c "
import asyncio
import sys
sys.path.insert(0, 'src')

async def test_upload():
    try:
        # Import the upload function
        from server import upload_youtube_video
        
        video_id = '$VIDEO_ID'
        title = '$VIDEO_TITLE'
        description = '$VIDEO_DESCRIPTION'
        tags = '$VIDEO_TAGS'.split(',')
        dry_run = '$dry_run' == 'true'
        
        print(f'📤 Testing upload for video: {video_id}')
        print(f'📝 Title: {title}')
        print(f'📄 Description: {description}')
        print(f'🏷️  Tags: {tags}')
        
        if dry_run:
            print('🧪 DRY RUN: Not performing actual upload')
            # For dry run, we'll just test the service initialization
            from youtube_upload_service import YouTubeUploadService
            service = YouTubeUploadService()
            print('✅ YouTube service can be initialized')
            print('✅ Upload function is available')
            print('ℹ️  To perform real upload, set YOUTUBE_CREDENTIALS_FILE and run with --upload flag')
            return True
        else:
            # Perform actual upload
            result = await upload_youtube_video(
                video_file_id=video_id,
                title=title,
                description=description,
                tags=tags,
                privacy_status='private',  # Always private for testing
                is_shorts=True
            )
            
            if result.get('success'):
                print('🎉 Upload successful!')
                print(f'🆔 Video ID: {result.get(\"video_id\", \"unknown\")}')
                print(f'🔗 URL: {result.get(\"video_url\", \"unknown\")}')
                shorts_url = result.get('shorts_url')
                if shorts_url:
                    print(f'📱 Shorts URL: {shorts_url}')
                print(f'📅 Uploaded: {result.get(\"upload_timestamp\", \"unknown\")}')
            else:
                error = result.get('error', 'Unknown error')
                print(f'❌ Upload failed: {error}')
                return False
        
    except Exception as e:
        print(f'❌ Exception during upload test: {e}')
        import traceback
        traceback.print_exc()
        return False
        
    return True

success = asyncio.run(test_upload())
if not success:
    sys.exit(1)
" || {
        if [[ "$dry_run" == "true" ]]; then
            log_error "Upload test failed"
        else
            log_error "YouTube upload failed"
        fi
        exit 1
    }
    
    if [[ "$dry_run" == "true" ]]; then
        log_success "Upload test completed (dry run)"
    else
        log_success "YouTube upload completed!"
    fi
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -f /tmp/test_video_id.txt
    log_success "Cleanup completed"
}

# Main execution
main() {
    echo "🚀 Starting YouTube Upload Test"
    echo
    
    # Parse command line arguments
    UPLOAD_FLAG=false
    while [[ $# -gt 0 ]]; do
        case $1 in
            --upload)
                UPLOAD_FLAG=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [--upload] [--help]"
                echo
                echo "Options:"
                echo "  --upload    Perform actual YouTube upload (requires credentials)"
                echo "  --help      Show this help message"
                echo
                echo "Environment Variables:"
                echo "  YOUTUBE_CREDENTIALS_FILE    Path to OAuth2 client_secrets.json"
                echo
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Execute test steps
    check_prerequisites
    test_mcp_server
    list_source_files
    create_test_short
    validate_for_youtube
    
    # Upload test (dry run by default)
    if [[ "$UPLOAD_FLAG" == "true" ]]; then
        test_youtube_upload "false"
    else
        test_youtube_upload "true"
    fi
    
    cleanup
    
    echo
    log_success "YouTube Upload Test Completed Successfully! 🎉"
    echo
    
    if [[ "$UPLOAD_FLAG" == "false" ]]; then
        echo "💡 To perform actual upload:"
        echo "   1. Set up YouTube API credentials:"
        echo "      export YOUTUBE_CREDENTIALS_FILE=/path/to/client_secrets.json"
        echo "   2. Run with upload flag:"
        echo "      ./test-youtube-upload.sh --upload"
    fi
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Run main function
main "$@"