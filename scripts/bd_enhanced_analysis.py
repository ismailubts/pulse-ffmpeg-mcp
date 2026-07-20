#!/usr/bin/env python3
"""
Enhanced Build Detective - Cross-validation and IN_PROGRESS detection
Fixes the critical gap where BD missed long-running jobs
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from typing import Dict, List, Any

def run_gh_command(cmd: List[str]) -> Dict:
    """Run GitHub CLI command and return parsed JSON"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"❌ GitHub CLI error: {e}")
        return {}

def calculate_runtime_minutes(started_at: str) -> float:
    """Calculate how long a job has been running in minutes"""
    if started_at == "0001-01-01T00:00:00Z":
        return 0.0
    
    start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    return (now - start_time).total_seconds() / 60

def analyze_pr_with_time_detection(repo: str, pr_number: str) -> Dict:
    """Enhanced PR analysis with IN_PROGRESS and time-based detection"""
    
    # Get detailed check status with timing
    checks = run_gh_command([
        'gh', 'pr', 'checks', pr_number, '--repo', repo,
        '--json', 'name,state,completedAt,startedAt,description,link'
    ])
    
    if not checks:
        return {"error": "Failed to get PR checks"}
    
    analysis = {
        "critical_issues": [],
        "suspicious_patterns": [],
        "time_analysis": {},
        "confidence": 10,  # Start high, reduce for issues
        "takeover_recommended": False
    }
    
    for check in checks:
        name = check.get('name', 'Unknown')
        state = check.get('state', 'Unknown')
        started_at = check.get('startedAt', '0001-01-01T00:00:00Z')
        completed_at = check.get('completedAt', '0001-01-01T00:00:00Z')
        
        # Calculate runtime
        if state == 'IN_PROGRESS':
            runtime_mins = calculate_runtime_minutes(started_at)
            analysis['time_analysis'][name] = {
                'state': state,
                'runtime_minutes': runtime_mins,
                'started_at': started_at
            }
            
            # CRITICAL: Docker jobs running >5 minutes are suspicious
            if 'docker' in name.lower() and runtime_mins > 5:
                analysis['critical_issues'].append({
                    'job': name,
                    'issue': f'Docker build running {runtime_mins:.1f} minutes - likely Alpine build waste',
                    'severity': 'CRITICAL',
                    'pattern': 'ALPINE_BUILD_WASTE'
                })
                analysis['confidence'] -= 3
            
            # Any job running >10 minutes needs attention
            elif runtime_mins > 10:
                analysis['suspicious_patterns'].append({
                    'job': name,
                    'issue': f'Job running {runtime_mins:.1f} minutes - investigate',
                    'severity': 'WARNING'
                })
                analysis['confidence'] -= 1
        
        # Pattern detection for failed jobs
        elif state == 'FAILURE':
            if 'docker' in name.lower():
                analysis['suspicious_patterns'].append({
                    'job': name,
                    'issue': 'Docker build failure - check for Alpine compilation issues',
                    'pattern': 'DOCKER_FAILURE'
                })
                analysis['confidence'] -= 1
    
    # Recommend takeover if confidence is low or critical issues found
    if analysis['confidence'] < 7 or analysis['critical_issues']:
        analysis['takeover_recommended'] = True
        analysis['takeover_reason'] = 'Low confidence or critical issues detected'
    
    return analysis

def cross_validate_bd_results(repo: str, pr_number: str, bd_confidence: int) -> Dict:
    """Cross-validate BD results with enhanced time-based analysis"""
    enhanced = analyze_pr_with_time_detection(repo, pr_number)
    
    validation = {
        'bd_confidence': bd_confidence,
        'enhanced_confidence': enhanced.get('confidence', 0),
        'validation_status': 'PASSED',
        'discrepancies': [],
        'action_required': False
    }
    
    # Check for critical discrepancies
    if enhanced.get('critical_issues'):
        validation['validation_status'] = 'FAILED'
        validation['action_required'] = True
        validation['discrepancies'].append('Critical issues found that BD missed')
    
    if enhanced.get('confidence', 10) < bd_confidence - 2:
        validation['validation_status'] = 'QUESTIONABLE'  
        validation['discrepancies'].append('Enhanced analysis has much lower confidence than BD')
    
    validation['enhanced_analysis'] = enhanced
    return validation

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python bd_enhanced_analysis.py <repo> <pr_number>")
        sys.exit(1)
    
    repo = sys.argv[1]
    pr_number = sys.argv[2]
    
    # Run enhanced analysis
    result = analyze_pr_with_time_detection(repo, pr_number)
    
    print("🔍 Enhanced Build Detective Analysis")
    print("=" * 50)
    
    if result.get('critical_issues'):
        print("🚨 CRITICAL ISSUES DETECTED:")
        for issue in result['critical_issues']:
            print(f"   - {issue['job']}: {issue['issue']}")
    
    if result.get('suspicious_patterns'):
        print("⚠️ SUSPICIOUS PATTERNS:")
        for pattern in result['suspicious_patterns']:
            print(f"   - {pattern['job']}: {pattern['issue']}")
    
    if result.get('time_analysis'):
        print("⏱️ LONG-RUNNING JOBS:")
        for job, info in result['time_analysis'].items():
            print(f"   - {job}: {info['runtime_minutes']:.1f} minutes ({info['state']})")
    
    print(f"🎯 Confidence: {result.get('confidence', 0)}/10")
    
    if result.get('takeover_recommended'):
        print("🔄 RECOMMENDATION: Take over from BD for manual analysis")
        print(f"   Reason: {result.get('takeover_reason', 'Unknown')}")