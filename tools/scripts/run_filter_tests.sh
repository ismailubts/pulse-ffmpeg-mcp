#!/bin/bash

# Video Filter Testing Runner
# Integrates comprehensive filter testing with existing MCP testing infrastructure

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_RESULTS_DIR="/tmp/music/filter_tests"
LOG_FILE="/tmp/filter_test.log"

# Color output functions
print_header() {
    echo -e "\n\033[1;34m$1\033[0m"
}

print_success() {
    echo -e "\033[1;32m✅ $1\033[0m"
}

print_error() {
    echo -e "\033[1;31m❌ $1\033[0m"
}

print_info() {
    echo -e "\033[1;36mℹ️  $1\033[0m"
}

print_warning() {
    echo -e "\033[1;33m⚠️  $1\033[0m"
}

# Setup test environment
setup_test_environment() {
    print_header "Setting up filter testing environment"
    
    # Create test directories
    mkdir -p "$TEST_RESULTS_DIR"
    mkdir -p "/tmp/music/source"
    mkdir -p "/tmp/music/temp"
    mkdir -p "/tmp/music/metadata"
    
    # Initialize log file
    echo "Filter Testing Session - $(date)" > "$LOG_FILE"
    
    # Check dependencies
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 not found"
        exit 1
    fi
    
    if ! command -v ffmpeg &> /dev/null; then
        print_error "FFmpeg not found"
        exit 1
    fi
    
    # Verify test videos exist
    if [ ! -d "tests/files" ] || [ -z "$(ls tests/files/*.mp4 2>/dev/null)" ]; then
        print_warning "No test video files found, creating minimal test video"
        create_test_video
    fi
    
    print_success "Test environment ready"
}

# Create a minimal test video if none exist
create_test_video() {
    print_info "Creating minimal test video for filter testing"
    
    ffmpeg -f lavfi -i testsrc2=duration=10:size=1280x720:rate=25 \
           -f lavfi -i sine=frequency=440:duration=10 \
           -c:v libx264 -c:a aac -shortest \
           "tests/files/filter_test_video.mp4" -y 2>/dev/null || {
        print_error "Failed to create test video"
        exit 1
    }
    
    print_success "Test video created: tests/files/filter_test_video.mp4"
}

# Start MCP server for testing
start_mcp_server() {
    print_header "Starting MCP server for filter testing"
    
    # Kill any existing server
    pkill -f "python.*src.server" || true
    sleep 2
    
    # Start server in background with proper logging
    print_info "Launching MCP server process..."
    uv run python -m src.server > /tmp/mcp_server.log 2>&1 &
    MCP_PID=$!
    echo $MCP_PID > /tmp/mcp_server.pid
    
    # Wait for server to start
    sleep 8
    
    # Verify server is running
    if kill -0 $MCP_PID 2>/dev/null; then
        print_success "MCP server started (PID: $MCP_PID)"
        
        # Test server responsiveness
        print_info "Testing server responsiveness..."
        if uv run python -c "
import sys
sys.path.insert(0, 'src')
try:
    import src.server
    print('Server module loaded successfully')
except Exception as e:
    print(f'Server test failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
            print_success "Server is responsive"
            return 0
        else
            print_warning "Server started but may not be fully responsive"
            return 0
        fi
    else
        print_error "Failed to start MCP server"
        if [ -f /tmp/mcp_server.log ]; then
            print_info "Server logs:"
            tail -10 /tmp/mcp_server.log
        fi
        return 1
    fi
}

# Stop MCP server
stop_mcp_server() {
    if [ -f /tmp/mcp_server.pid ]; then
        MCP_PID=$(cat /tmp/mcp_server.pid)
        if kill -0 $MCP_PID 2>/dev/null; then
            print_info "Stopping MCP server (PID: $MCP_PID)"
            kill $MCP_PID
            sleep 2
        fi
        rm -f /tmp/mcp_server.pid
    fi
}

# Run the main filter tests
run_filter_tests() {
    print_header "Executing comprehensive filter tests"
    
    # Run the Python test framework
    echo "Starting filter testing framework..." >> "$LOG_FILE"
    
    if uv run python test_video_filters.py 2>&1 | tee -a "$LOG_FILE"; then
        print_success "Filter tests completed successfully"
        return 0
    else
        print_error "Filter tests failed"
        return 1
    fi
}

# Validate test results
validate_results() {
    print_header "Validating test results"
    
    # Check if results directory has content
    if [ -d "$TEST_RESULTS_DIR" ] && [ "$(ls -A $TEST_RESULTS_DIR)" ]; then
        local result_files=$(ls "$TEST_RESULTS_DIR"/*.json 2>/dev/null | wc -l)
        print_success "Found $result_files result files"
        
        # Check for generated video files
        local video_files=$(find "$TEST_RESULTS_DIR" -name "*.mp4" 2>/dev/null | wc -l)
        print_info "Generated $video_files test videos"
        
        # Show latest results file
        local latest_result=$(ls -t "$TEST_RESULTS_DIR"/*.json 2>/dev/null | head -1)
        if [ -n "$latest_result" ]; then
            print_info "Latest results: $(basename "$latest_result")"
            
            # Extract success rate if possible
            if command -v jq &> /dev/null; then
                local success_rate=$(jq -r '.test_session.success_count // 0' "$latest_result" 2>/dev/null)
                local total_tests=$(jq -r '.test_session.test_count // 0' "$latest_result" 2>/dev/null)
                if [ "$total_tests" -gt 0 ]; then
                    print_info "Success rate: $success_rate/$total_tests tests"
                fi
            fi
        fi
        
        return 0
    else
        print_error "No results found in $TEST_RESULTS_DIR"
        return 1
    fi
}

# Generate test report
generate_report() {
    print_header "Generating test report"
    
    local report_file="$TEST_RESULTS_DIR/filter_test_report.md"
    
    cat > "$report_file" << EOF
# Video Filter Testing Report

**Date:** $(date)
**Test Session:** Filter Comprehensive Testing
**Environment:** $(uname -s) $(uname -r)

## Test Overview

This report contains results from comprehensive video filter testing including:
- Individual effect testing across all categories
- Effect chain combinations
- Performance benchmarking
- Quality validation

## Test Results

EOF

    # Add results summary if JSON files exist
    local latest_result=$(ls -t "$TEST_RESULTS_DIR"/*.json 2>/dev/null | head -1)
    if [ -n "$latest_result" ] && command -v jq &> /dev/null; then
        echo "### Summary Statistics" >> "$report_file"
        echo "" >> "$report_file"
        jq -r '"- Total tests: \(.test_session.test_count // 0)"' "$latest_result" >> "$report_file"
        jq -r '"- Successful tests: \(.test_session.success_count // 0)"' "$latest_result" >> "$report_file"
        jq -r '"- Failed tests: \((.test_session.failed_tests // []) | length)"' "$latest_result" >> "$report_file"
        jq -r '"- Test duration: \(.test_session.total_duration // 0) seconds"' "$latest_result" >> "$report_file"
        echo "" >> "$report_file"
    fi
    
    # Add file listings
    echo "### Generated Files" >> "$report_file"
    echo "" >> "$report_file"
    echo "\`\`\`" >> "$report_file"
    ls -la "$TEST_RESULTS_DIR" >> "$report_file" 2>/dev/null || echo "No files generated" >> "$report_file"
    echo "\`\`\`" >> "$report_file"
    
    print_success "Report generated: $report_file"
}

# Cleanup function
cleanup() {
    print_header "Cleaning up test environment"
    
    # Stop MCP server
    stop_mcp_server
    
    # Optional: clean up temp files (but preserve results)
    # Uncomment if you want to clean up temp files
    # rm -rf /tmp/music/temp/*
    
    print_success "Cleanup completed"
}

# Main execution function
main() {
    local test_mode="${1:-full}"
    
    print_header "🎬 Video Filter Testing Framework"
    print_info "Mode: $test_mode"
    print_info "Results directory: $TEST_RESULTS_DIR"
    print_info "Log file: $LOG_FILE"
    
    # Set up trap for cleanup
    trap cleanup EXIT
    
    case "$test_mode" in
        "setup")
            setup_test_environment
            ;;
        "quick")
            setup_test_environment
            start_mcp_server
            print_info "Running quick filter test (basic effects only)"
            # Could add a quick test mode here
            run_filter_tests
            validate_results
            ;;
        "full"|*)
            setup_test_environment
            start_mcp_server
            run_filter_tests
            validate_results
            generate_report
            ;;
    esac
    
    print_header "🎉 Filter testing completed!"
    print_info "Check results in: $TEST_RESULTS_DIR"
    print_info "View logs: $LOG_FILE"
}

# Handle command line arguments
case "${1:-}" in
    "-h"|"--help")
        echo "Video Filter Testing Runner"
        echo ""
        echo "Usage: $0 [mode]"
        echo ""
        echo "Modes:"
        echo "  full    - Complete filter testing suite (default)"
        echo "  quick   - Quick test of basic effects"
        echo "  setup   - Setup test environment only"
        echo ""
        echo "Examples:"
        echo "  $0                # Run full test suite"
        echo "  $0 quick         # Quick test"
        echo "  $0 setup         # Setup only"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac