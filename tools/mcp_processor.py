#!/usr/bin/env python3
"""
MCP Processor for Komposteur Integration
Captures and logs all communication from Komposteur
"""
import sys
import json
import os
from datetime import datetime

def log_interaction(message):
    """Log interaction to debug file"""
    log_file = "/tmp/mcp_processor_debug.log"
    timestamp = datetime.now().isoformat()
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def main():
    log_interaction("🚀 MCP Processor started")
    log_interaction(f"Arguments: {sys.argv}")
    log_interaction(f"Environment: {dict(os.environ)}")
    log_interaction(f"Working directory: {os.getcwd()}")
    
    # Check if we have stdin data
    try:
        if not sys.stdin.isatty():
            stdin_data = sys.stdin.read()
            log_interaction(f"STDIN data: {stdin_data}")
        else:
            log_interaction("No STDIN data")
    except Exception as e:
        log_interaction(f"STDIN error: {e}")
    
    # Process arguments
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv[1:], 1):
            log_interaction(f"Arg {i}: {arg}")
            
            # Try to parse as JSON if it looks like JSON
            if arg.startswith('{') or arg.endswith('.json'):
                try:
                    if arg.endswith('.json'):
                        with open(arg, 'r') as f:
                            data = json.load(f)
                            log_interaction(f"JSON file content: {json.dumps(data, indent=2)}")
                    else:
                        data = json.loads(arg)
                        log_interaction(f"JSON argument: {json.dumps(data, indent=2)}")
                except Exception as e:
                    log_interaction(f"JSON parse error: {e}")
    
    # Return success for now
    log_interaction("✅ MCP Processor completed successfully")
    print("SUCCESS: MCP processor executed")
    return 0

if __name__ == "__main__":
    sys.exit(main())