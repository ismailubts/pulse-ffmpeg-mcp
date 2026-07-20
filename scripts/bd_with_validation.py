#!/usr/bin/env python3
"""
Build Detective with Enhanced Validation
Combines standard BD analysis with time-based validation and takeover protocol
"""
import sys
import subprocess
from bd_enhanced_analysis import analyze_pr_with_time_detection, cross_validate_bd_results
from bd_takeover_protocol import should_takeover, takeover_analysis

def run_standard_bd(repo: str, pr_number: str) -> dict:
    """Run the standard BD manual analysis"""
    try:
        result = subprocess.run([
            'uv', 'run', 'python', 'scripts/bd_manual.py', repo, pr_number
        ], capture_output=True, text=True, timeout=60)
        
        # Parse BD confidence from output (basic heuristic)
        bd_confidence = 5  # Default medium confidence
        
        if 'BLOCKING' in result.stdout:
            bd_confidence = 3
        elif 'WARNING' in result.stdout:
            bd_confidence = 6
        elif 'Found 0 failed checks' in result.stdout:
            bd_confidence = 9
        
        return {
            'output': result.stdout,
            'confidence': bd_confidence,
            'success': result.returncode == 0
        }
    except Exception as e:
        return {
            'output': f'BD Error: {e}',
            'confidence': 1,
            'success': False
        }

def enhanced_bd_analysis(repo: str, pr_number: str) -> dict:
    """Run BD analysis with enhanced validation and takeover protocol"""
    
    print("🔍 Running Build Detective with Enhanced Validation")
    print("=" * 60)
    
    # Step 1: Run standard BD analysis
    print("📊 Step 1: Standard Build Detective Analysis")
    bd_result = run_standard_bd(repo, pr_number)
    print(bd_result['output'])
    
    # Step 2: Run enhanced time-based analysis
    print("\n⏱️ Step 2: Enhanced Time-Based Analysis")
    enhanced_result = analyze_pr_with_time_detection(repo, pr_number)
    
    if enhanced_result.get('critical_issues'):
        print("🚨 CRITICAL ISSUES DETECTED:")
        for issue in enhanced_result['critical_issues']:
            print(f"   - {issue['job']}: {issue['issue']}")
    
    if enhanced_result.get('time_analysis'):
        print("⏱️ LONG-RUNNING JOBS:")
        for job, info in enhanced_result['time_analysis'].items():
            print(f"   - {job}: {info['runtime_minutes']:.1f} minutes ({info['state']})")
    
    # Step 3: Cross-validate BD results
    print(f"\n🔄 Step 3: Cross-Validation")
    validation = cross_validate_bd_results(repo, pr_number, bd_result['confidence'])
    
    print(f"BD Confidence: {validation['bd_confidence']}/10")
    print(f"Enhanced Confidence: {validation['enhanced_confidence']}/10")
    print(f"Validation Status: {validation['validation_status']}")
    
    if validation.get('discrepancies'):
        print("⚠️ Discrepancies Found:")
        for discrepancy in validation['discrepancies']:
            print(f"   - {discrepancy}")
    
    # Step 4: Determine if takeover is needed
    should_take_over = should_takeover(bd_result['confidence'], enhanced_result)
    
    if should_take_over:
        print("\n🔄 Step 4: TAKING OVER FROM BUILD DETECTIVE")
        print("Reason: Low confidence or critical issues detected")
        
        takeover_result = takeover_analysis(repo, pr_number)
        
        if takeover_result.get('critical_jobs'):
            print("\n🚨 CRITICAL JOBS REQUIRING IMMEDIATE ACTION:")
            for job in takeover_result['critical_jobs']:
                print(f"   - {job['job']}")
                print(f"     Diagnosis: {job['diagnosis']}")
                print(f"     Action: {job['recommended_action']}")
        
        if takeover_result.get('immediate_actions'):
            print("\n⚡ IMMEDIATE ACTIONS REQUIRED:")
            for i, action in enumerate(takeover_result['immediate_actions'], 1):
                print(f"   {i}. {action['action']}")
                print(f"      Priority: {action['priority']}")
        
        return {
            'status': 'TAKEOVER_COMPLETED',
            'confidence': enhanced_result.get('confidence', 0),
            'bd_confidence': bd_result['confidence'],
            'enhanced_analysis': enhanced_result,
            'takeover_analysis': takeover_result,
            'recommendation': 'Manual intervention required based on takeover analysis'
        }
    
    else:
        print(f"\n✅ Step 4: Build Detective Analysis Validated")
        print(f"Final Confidence: {validation['enhanced_confidence']}/10")
        print("No takeover required - BD analysis appears accurate")
        
        return {
            'status': 'BD_VALIDATED',
            'confidence': validation['enhanced_confidence'],
            'bd_confidence': bd_result['confidence'],
            'enhanced_analysis': enhanced_result,
            'recommendation': 'BD analysis validated - proceed with BD recommendations'
        }

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python bd_with_validation.py <repo> <pr_number>")
        print("Example: python bd_with_validation.py ismailubts/pulse-ffmpeg-mcp 21")
        sys.exit(1)
    
    repo = sys.argv[1]
    pr_number = sys.argv[2]
    
    result = enhanced_bd_analysis(repo, pr_number)
    
    print(f"\n📋 FINAL SUMMARY")
    print("=" * 30)
    print(f"Status: {result['status']}")
    print(f"Final Confidence: {result['confidence']}/10")
    print(f"Recommendation: {result['recommendation']}")
    
    # Exit with appropriate code
    if result['status'] == 'TAKEOVER_COMPLETED':
        print("\n🚨 CRITICAL: Manual intervention required!")
        sys.exit(2)  # Critical issues found
    elif result['confidence'] < 7:
        print("\n⚠️ WARNING: Low confidence, monitor closely")
        sys.exit(1)  # Warning
    else:
        print("\n✅ SUCCESS: Analysis completed successfully")
        sys.exit(0)  # Success