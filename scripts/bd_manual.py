#!/usr/bin/env python3
"""
Manual Build Detective - PULSE-FFMPEG-MCP CI Analysis
Provides Build Detective functionality without relying on Claude Code agent system
"""

import subprocess
import json
import sys
import re
from typing import Dict, List, Any

def run_gh_command(cmd: List[str]) -> str:
    """Run GitHub CLI command and return output"""
    try:
        result = subprocess.run(['gh'] + cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"GitHub CLI error: {e}")
        return ""

def analyze_pr_failures(repo: str, pr_number: str) -> Dict[str, Any]:
    """Analyze PR failures and return structured analysis"""
    
    # Get PR status
    pr_data = run_gh_command(['pr', 'view', pr_number, '--repo', repo, '--json', 'statusCheckRollup'])
    
    if not pr_data:
        return {"error": "Could not fetch PR data"}
    
    try:
        pr_json = json.loads(pr_data)
        status_checks = pr_json.get('statusCheckRollup', [])
        
        failures = [check for check in status_checks if check.get('conclusion') == 'FAILURE']
        
        analysis_results = []
        
        for failure in failures:
            run_id = failure.get('detailsUrl', '').split('/')[-3] if 'detailsUrl' in failure else None
            if run_id:
                # Get logs for this failure
                logs = run_gh_command(['run', 'view', run_id, '--repo', repo, '--log'])
                
                # Apply Build Detective patterns
                analysis = apply_bd_patterns(logs, failure['name'])
                analysis['workflow_name'] = failure.get('workflowName', 'Unknown')
                analysis['job_name'] = failure['name']
                analysis['run_id'] = run_id
                
                analysis_results.append(analysis)
        
        return {
            "status": "SUCCESS",
            "total_failures": len(failures),
            "analysis_results": analysis_results
        }
        
    except json.JSONDecodeError:
        return {"error": "Could not parse PR data JSON"}

def apply_bd_patterns(logs: str, job_name: str) -> Dict[str, Any]:
    """Apply Build Detective error patterns to logs"""
    
    # PULSE-FFMPEG-MCP specific patterns
    patterns = {
        "docker_python_not_found": r'exec: "python": executable file not found in \$PATH',
        "docker_build_missing_file": r"ERROR: failed to calculate checksum.*not found",
        "pytest_missing": r"Failed to spawn.*pytest.*No such file",
        "uv_dependency": r"uv.*not available",
        "docker_copy_fail": r"COPY.*not found",
        "mcp_import_fail": r"MCP module imports failed",
        "docker_strange_files": r"=\d+\.\d+\.\d+",  # Strange version files
    }
    
    errors_found = []
    primary_error = "Unknown failure"
    error_type = "unknown"
    confidence = 5
    
    # Check for specific patterns (most specific first)
    if re.search(patterns["docker_python_not_found"], logs):
        primary_error = "Docker container missing 'python' executable - Ubuntu uses 'python3'"
        error_type = "docker_python_path"
        confidence = 10
        errors_found.append("Container has python3 but CI script uses 'python' command")
        
    elif re.search(patterns["docker_build_missing_file"], logs):
        primary_error = "Docker build failed - missing source files for COPY commands"
        error_type = "docker_build"
        confidence = 9
        errors_found.append("Missing test files for Docker COPY")
        
    elif re.search(patterns["pytest_missing"], logs):
        primary_error = "pytest not available in UV environment"
        error_type = "dependency"
        confidence = 9
        errors_found.append("UV missing --extra dev flag")
        
    elif re.search(patterns["mcp_import_fail"], logs):
        primary_error = "MCP modules failed to import in Docker"
        error_type = "python_import"  
        confidence = 8
        errors_found.append("Docker Python environment issues")
        
    elif re.search(patterns["docker_strange_files"], logs):
        primary_error = "Docker dependency installation created malformed files"
        error_type = "docker_dependency"
        confidence = 7
        errors_found.append("UV/pip command parsing issue in Docker")
    
    # Determine suggested action
    suggested_action = "Check logs manually"
    if error_type == "docker_python_path":
        suggested_action = "Change CI script from 'python' to 'python3' command in Docker exec"
    elif error_type == "docker_build":
        suggested_action = "Add missing test files or fix Dockerfile COPY paths"
    elif error_type == "dependency":
        suggested_action = "Add --extra dev flag to uv sync commands"
    elif error_type == "python_import":
        suggested_action = "Fix Docker Python environment and dependency installation"
    elif error_type == "docker_dependency":
        suggested_action = "Fix Docker UV/pip installation commands"
    
    return {
        "primary_error": primary_error,
        "error_type": error_type,
        "confidence": confidence,
        "errors_found": errors_found,
        "suggested_action": suggested_action,
        "blocking_vs_warning": "BLOCKING" if confidence >= 7 else "WARNING"
    }

def main():
    if len(sys.argv) != 3:
        print("Usage: python bd_manual.py <repo> <pr_number>")
        print("Example: python bd_manual.py ismailubts/pulse-ffmpeg-mcp 16")
        sys.exit(1)
    
    repo = sys.argv[1]
    pr_number = sys.argv[2]
    
    print(f"🔍 Build Detective Analysis - {repo} PR#{pr_number}")
    print("=" * 60)
    
    analysis = analyze_pr_failures(repo, pr_number)
    
    if "error" in analysis:
        print(f"❌ Error: {analysis['error']}")
        sys.exit(1)
    
    print(f"📊 Found {analysis['total_failures']} failed checks")
    print()
    
    for i, result in enumerate(analysis['analysis_results'], 1):
        print(f"🚨 Failure #{i}: {result['job_name']}")
        print(f"   Workflow: {result['workflow_name']}")
        print(f"   Primary Error: {result['primary_error']}")
        print(f"   Type: {result['error_type']}")
        print(f"   Status: {result['blocking_vs_warning']}")
        print(f"   Confidence: {result['confidence']}/10")
        print(f"   🔧 Action: {result['suggested_action']}")
        if result['errors_found']:
            print(f"   📋 Details: {', '.join(result['errors_found'])}")
        print(f"   🔗 Run ID: {result['run_id']}")
        print()

if __name__ == "__main__":
    main()