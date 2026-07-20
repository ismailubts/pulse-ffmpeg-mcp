#!/usr/bin/env python3
"""
Build Detective Takeover Protocol
When BD confidence is low, take over with direct GitHub API analysis
"""
import json
import subprocess
from typing import Dict, List

def should_takeover(bd_confidence: int, enhanced_analysis: Dict) -> bool:
    """Determine if we should take over from BD"""
    
    # Always takeover if critical issues detected (Alpine build waste, etc.)
    if enhanced_analysis.get('critical_issues'):
        return True
    
    # Takeover if BD confidence is very low AND enhanced analysis agrees
    enhanced_conf = enhanced_analysis.get('confidence', 10)
    if bd_confidence < 5 and enhanced_conf < 7:
        return True
        
    # Takeover if enhanced confidence is much lower than BD (enhanced sees problems BD missed)
    if enhanced_conf < bd_confidence - 3:
        return True
        
    return False

def analyze_long_running_job(job_name: str, runtime_minutes: float, link: str) -> Dict:
    """Deep analysis of long-running jobs"""
    analysis = {
        'job': job_name,
        'runtime_minutes': runtime_minutes,
        'diagnosis': 'Unknown',
        'root_cause': 'Unknown', 
        'recommended_action': 'Unknown',
        'urgency': 'LOW'
    }
    
    # Docker build patterns
    if 'docker' in job_name.lower():
        if runtime_minutes > 30:
            analysis['diagnosis'] = 'Alpine compilation timeout - classic 2-6 hour build waste'
            analysis['root_cause'] = 'CI workflow still using Alpine Docker base with heavy compilation'
            analysis['recommended_action'] = 'Update CI workflow to use Ubuntu Docker base or disable Alpine build'
            analysis['urgency'] = 'CRITICAL'
        elif runtime_minutes > 10:
            analysis['diagnosis'] = 'Docker build taking unusually long'
            analysis['root_cause'] = 'Possible Alpine compilation or network issues'
            analysis['recommended_action'] = 'Check if workflow updated to use Ubuntu base'
            analysis['urgency'] = 'HIGH'
    
    # Integration test patterns  
    elif 'integration' in job_name.lower():
        if runtime_minutes > 15:
            analysis['diagnosis'] = 'Integration tests hanging or in infinite loop'
            analysis['root_cause'] = 'Possible service startup timeout or test framework issue'
            analysis['recommended_action'] = 'Check test logs for hanging processes'
            analysis['urgency'] = 'HIGH'
    
    return analysis

def takeover_analysis(repo: str, pr_number: str) -> Dict:
    """Full takeover analysis when BD fails"""
    print("🔄 Taking over from Build Detective...")
    print("=" * 50)
    
    # Get current PR status
    result = subprocess.run([
        'gh', 'pr', 'checks', pr_number, '--repo', repo,
        '--json', 'name,state,completedAt,startedAt,link'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        return {"error": "Failed to get PR status"}
    
    checks = json.loads(result.stdout)
    takeover_results = {
        'critical_jobs': [],
        'action_plan': [],
        'immediate_actions': []
    }
    
    for check in checks:
        name = check.get('name', '')
        state = check.get('state', '')
        link = check.get('link', '')
        
        if state == 'IN_PROGRESS':
            from bd_enhanced_analysis import calculate_runtime_minutes
            started_at = check.get('startedAt', '0001-01-01T00:00:00Z')
            runtime = calculate_runtime_minutes(started_at)
            
            if runtime > 5:  # Suspicious long-running job
                job_analysis = analyze_long_running_job(name, runtime, link)
                takeover_results['critical_jobs'].append(job_analysis)
                
                if job_analysis['urgency'] == 'CRITICAL':
                    takeover_results['immediate_actions'].append({
                        'action': f"KILL {name} job - it's in Alpine build waste cycle",
                        'reason': f"Running {runtime:.1f} minutes - will timeout after hours",
                        'priority': 1
                    })
                    
                    takeover_results['immediate_actions'].append({
                        'action': f"Find and update CI workflow for {name}",
                        'reason': "Replace Alpine Docker base with Ubuntu approach",
                        'priority': 2
                    })
    
    return takeover_results

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python bd_takeover_protocol.py <repo> <pr_number>")
        sys.exit(1)
        
    result = takeover_analysis(sys.argv[1], sys.argv[2])
    
    if result.get('critical_jobs'):
        print("🚨 CRITICAL JOBS IDENTIFIED:")
        for job in result['critical_jobs']:
            print(f"   - {job['job']}: {job['diagnosis']}")
            print(f"     Root Cause: {job['root_cause']}")
            print(f"     Action: {job['recommended_action']}")
    
    if result.get('immediate_actions'):
        print("\n⚡ IMMEDIATE ACTIONS REQUIRED:")
        for i, action in enumerate(result['immediate_actions'], 1):
            print(f"   {i}. {action['action']}")
            print(f"      Reason: {action['reason']}")