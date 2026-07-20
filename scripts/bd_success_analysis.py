#!/usr/bin/env python3
"""
Build Detective Success Analysis
Find last 10 successful CI builds and compare with current failures
"""
import subprocess
import json
import sys
from typing import Dict, List, Any
from datetime import datetime

def run_gh_command(cmd: List[str]) -> str:
    """Run GitHub CLI command and return output"""
    try:
        result = subprocess.run(['gh'] + cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"GitHub CLI error: {e}")
        return ""

def get_recent_workflow_runs(repo: str, limit: int = 50) -> List[Dict]:
    """Get recent workflow runs with their status"""
    runs_data = run_gh_command([
        'run', 'list', '--repo', repo, '--limit', str(limit), '--json',
        'status,conclusion,workflowName,number,createdAt,headBranch,event'
    ])
    
    if not runs_data:
        return []
    
    try:
        runs = json.loads(runs_data)
        return runs
    except json.JSONDecodeError:
        print("Failed to parse workflow runs data")
        return []

def find_successful_builds(repo: str, count: int = 10) -> List[Dict]:
    """Find the last N successful CI builds"""
    print(f"🔍 Searching for last {count} successful CI builds...")
    
    runs = get_recent_workflow_runs(repo, limit=100)
    successful_builds = []
    
    for run in runs:
        if (run.get('conclusion') == 'success' and 
            run.get('status') == 'completed' and
            'CI' in run.get('workflowName', '')):
            
            successful_builds.append({
                'run_number': run['number'],
                'workflow_name': run['workflowName'],
                'branch': run['headBranch'],
                'created_at': run['createdAt'],
                'event': run['event']
            })
            
            if len(successful_builds) >= count:
                break
    
    return successful_builds

def find_recent_failures(repo: str, limit: int = 20) -> List[Dict]:
    """Find recent failed CI builds"""
    print(f"🔍 Searching for recent failed CI builds...")
    
    runs = get_recent_workflow_runs(repo, limit=limit)
    failed_builds = []
    
    for run in runs:
        if (run.get('conclusion') == 'failure' and 
            run.get('status') == 'completed' and
            'CI' in run.get('workflowName', '')):
            
            failed_builds.append({
                'run_number': run['number'],
                'workflow_name': run['workflowName'],
                'branch': run['headBranch'],
                'created_at': run['createdAt'],
                'event': run['event']
            })
    
    return failed_builds

def get_workflow_details(repo: str, run_number: int) -> Dict:
    """Get detailed information about a specific workflow run"""
    run_data = run_gh_command([
        'run', 'view', str(run_number), '--repo', repo, '--json',
        'jobs,conclusion,status,workflowName,headBranch,createdAt'
    ])
    
    if not run_data:
        return {}
    
    try:
        return json.loads(run_data)
    except json.JSONDecodeError:
        return {}

def analyze_build_differences(successful_builds: List[Dict], failed_builds: List[Dict], repo: str) -> Dict:
    """Compare successful and failed builds to find differences"""
    print("🔍 Analyzing differences between successful and failed builds...")
    
    analysis = {
        'successful_patterns': {},
        'failed_patterns': {},
        'key_differences': [],
        'missing_special_sauce': []
    }
    
    # Analyze successful builds
    for build in successful_builds[:3]:  # Analyze last 3 successful
        details = get_workflow_details(repo, build['run_number'])
        if details:
            jobs = details.get('jobs', [])
            job_names = [job.get('name', '') for job in jobs]
            analysis['successful_patterns'][build['run_number']] = {
                'branch': build['branch'],
                'jobs': job_names,
                'job_count': len(jobs),
                'created_at': build['created_at']
            }
    
    # Analyze failed builds
    for build in failed_builds[:3]:  # Analyze last 3 failed
        details = get_workflow_details(repo, build['run_number'])
        if details:
            jobs = details.get('jobs', [])
            job_names = [job.get('name', '') for job in jobs]
            analysis['failed_patterns'][build['run_number']] = {
                'branch': build['branch'],
                'jobs': job_names,
                'job_count': len(jobs),
                'created_at': build['created_at']
            }
    
    # Find differences
    if analysis['successful_patterns'] and analysis['failed_patterns']:
        success_job_sets = [set(data['jobs']) for data in analysis['successful_patterns'].values()]
        failed_job_sets = [set(data['jobs']) for data in analysis['failed_patterns'].values()]
        
        # Find common successful jobs
        if success_job_sets:
            common_success_jobs = set.intersection(*success_job_sets) if len(success_job_sets) > 1 else success_job_sets[0]
        else:
            common_success_jobs = set()
            
        # Find common failed jobs
        if failed_job_sets:
            common_failed_jobs = set.intersection(*failed_job_sets) if len(failed_job_sets) > 1 else failed_job_sets[0]
        else:
            common_failed_jobs = set()
        
        # Identify missing jobs (in success but not in failed)
        missing_jobs = common_success_jobs - common_failed_jobs
        if missing_jobs:
            analysis['missing_special_sauce'].extend(list(missing_jobs))
        
        # Identify new jobs (in failed but not in success)
        new_jobs = common_failed_jobs - common_success_jobs
        if new_jobs:
            analysis['key_differences'].append(f"New jobs in failed builds: {list(new_jobs)}")
        
        # Branch differences
        success_branches = {data['branch'] for data in analysis['successful_patterns'].values()}
        failed_branches = {data['branch'] for data in analysis['failed_patterns'].values()}
        
        if success_branches != failed_branches:
            analysis['key_differences'].append(f"Branch difference - Success: {success_branches}, Failed: {failed_branches}")
    
    return analysis

def main():
    if len(sys.argv) != 2:
        print("Usage: python bd_success_analysis.py <repo>")
        print("Example: python bd_success_analysis.py ismailubts/pulse-ffmpeg-mcp")
        sys.exit(1)
    
    repo = sys.argv[1]
    
    print("🔍 Build Detective Success Analysis")
    print("=" * 50)
    
    # Find successful builds
    successful_builds = find_successful_builds(repo, 10)
    print(f"✅ Found {len(successful_builds)} successful CI builds:")
    for i, build in enumerate(successful_builds, 1):
        created_date = datetime.fromisoformat(build['created_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
        print(f"   {i}. Run #{build['run_number']} - {build['branch']} - {created_date}")
    
    # Find failed builds
    failed_builds = find_recent_failures(repo, 10)
    print(f"\n❌ Found {len(failed_builds)} recent failed CI builds:")
    for i, build in enumerate(failed_builds, 1):
        created_date = datetime.fromisoformat(build['created_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
        print(f"   {i}. Run #{build['run_number']} - {build['branch']} - {created_date}")
    
    # Analyze differences
    if successful_builds and failed_builds:
        print(f"\n🔍 Comparing successful vs failed builds...")
        analysis = analyze_build_differences(successful_builds, failed_builds, repo)
        
        if analysis['key_differences']:
            print(f"\n🚨 KEY DIFFERENCES FOUND:")
            for diff in analysis['key_differences']:
                print(f"   - {diff}")
        
        if analysis['missing_special_sauce']:
            print(f"\n🎯 MISSING 'SPECIAL SAUCE' (Jobs in successful but not in failed):")
            for job in analysis['missing_special_sauce']:
                print(f"   - {job}")
        
        print(f"\n📊 SUCCESSFUL BUILD PATTERNS:")
        for run_num, data in analysis['successful_patterns'].items():
            print(f"   Run #{run_num} ({data['branch']}): {data['job_count']} jobs")
            for job in data['jobs'][:5]:  # Show first 5 jobs
                print(f"     • {job}")
        
        print(f"\n📊 FAILED BUILD PATTERNS:")
        for run_num, data in analysis['failed_patterns'].items():
            print(f"   Run #{run_num} ({data['branch']}): {data['job_count']} jobs")
            for job in data['jobs'][:5]:  # Show first 5 jobs
                print(f"     • {job}")
        
        # Summary
        print(f"\n📋 SUMMARY:")
        if analysis['missing_special_sauce']:
            print(f"🎯 LIKELY CAUSE: Missing jobs that were present in successful builds")
            print(f"🔧 ACTION: Investigate why these jobs are no longer running:")
            for job in analysis['missing_special_sauce']:
                print(f"   - {job}")
        elif analysis['key_differences']:
            print(f"🎯 LIKELY CAUSE: Build configuration or branch differences")
            print(f"🔧 ACTION: Review the differences found above")
        else:
            print(f"🤔 No obvious structural differences found")
            print(f"🔧 ACTION: May need deeper log analysis of specific job failures")
    
    else:
        print("\n⚠️ Insufficient data to perform comparison")

if __name__ == "__main__":
    main()