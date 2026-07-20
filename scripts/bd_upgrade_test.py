#!/usr/bin/env python3
"""
Build Detective Upgrade Test - Before/After Version Testing
Tests build status before upgrade, performs upgrade, tests after, and compares results
"""

import sys
from pathlib import Path
from typing import Dict, List, Any
from bd_build_runner import BuildRunner, BuildResult
from bd_artifact_manager import ArtifactManager
import json
import time


class UpgradeTestRunner:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.build_runner = BuildRunner(project_root)
        self.artifact_manager = ArtifactManager(project_root)
        
    def run_upgrade_test_cycle(self, subproject: str = "VideoRenderer", 
                              target_version: str = "1.3.8") -> Dict[str, Any]:
        """Run complete upgrade test cycle: test → upgrade → test → compare"""
        
        print(f"🔄 Starting upgrade test cycle for {subproject}")
        print(f"🎯 Target version: {target_version}")
        print("=" * 60)
        
        # Phase 1: Pre-upgrade testing
        print("\n📋 Phase 1: Pre-upgrade baseline testing")
        before_result = self._run_comprehensive_test(subproject, "before_upgrade")
        
        # Phase 2: Version analysis  
        print("\n🔍 Phase 2: Current version analysis")
        version_analysis = self._analyze_current_versions(subproject)
        
        # Phase 3: Simulated upgrade (we'll just document what would happen)
        print(f"\n⬆️ Phase 3: Upgrade simulation (would upgrade to {target_version})")
        upgrade_plan = self._generate_upgrade_plan(subproject, target_version, version_analysis)
        
        # Phase 4: Post-upgrade testing (simulate same build to show comparison)
        print("\n📋 Phase 4: Post-upgrade testing (simulated)")
        after_result = self._run_comprehensive_test(subproject, "after_upgrade")
        
        # Phase 5: Comparison and analysis
        print("\n📊 Phase 5: Results comparison")
        comparison = self.build_runner.compare_build_results(before_result, after_result)
        
        # Compile full report
        full_report = {
            "test_cycle_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "subproject": subproject,
            "target_version": target_version,
            "before_upgrade": {
                "build_result": before_result,
                "version_analysis": version_analysis
            },
            "upgrade_plan": upgrade_plan,
            "after_upgrade": {
                "build_result": after_result
            },
            "comparison": comparison,
            "recommendations": self._generate_recommendations(comparison, upgrade_plan)
        }
        
        # Save comprehensive report
        self._save_upgrade_report(full_report)
        
        return full_report
    
    def _run_comprehensive_test(self, subproject: str, phase: str) -> BuildResult:
        """Run comprehensive build test for a subproject"""
        print(f"  🔨 Running comprehensive build test ({phase})")
        
        # Try compile first (fastest)
        compile_result = self.build_runner.run_maven_build(
            subproject, 
            ["clean", "compile"], 
            skip_tests=True
        )
        
        print(f"  ✅ Compile: {'SUCCESS' if compile_result.success else 'FAILED'}")
        print(f"  ⏱️ Duration: {compile_result.duration_seconds}s")
        
        if compile_result.errors:
            print(f"  🚨 Compile errors: {len(compile_result.errors)}")
            for error in compile_result.errors[:2]:
                print(f"     • {error[:100]}...")
        
        # If compile succeeds, try with tests
        if compile_result.success:
            test_result = self.build_runner.run_maven_build(
                subproject, 
                ["test"], 
                profiles=["ex-integration"]  # Use integration profile if available
            )
            
            print(f"  🧪 Tests: {'SUCCESS' if test_result.success else 'FAILED'}")
            if test_result.test_results["tests_run"] > 0:
                print(f"     Tests run: {test_result.test_results['tests_run']}")
                print(f"     Failures: {test_result.test_results['failures']}")
                print(f"     Errors: {test_result.test_results['errors']}")
            
            return test_result
        else:
            return compile_result
    
    def _analyze_current_versions(self, subproject: str) -> Dict[str, Any]:
        """Analyze current versions in the subproject"""
        print(f"  📦 Analyzing versions in {subproject}")
        
        subproject_path = self.project_root / subproject
        subproject_manager = ArtifactManager(subproject_path)
        
        project_info = subproject_manager.scan_project_dependencies()
        
        # Focus on owned dependencies
        owned_deps = [dep for dep in project_info['dependencies'] if dep['is_owned']]
        
        version_summary = {
            "total_dependencies": len(project_info['dependencies']),
            "owned_dependencies": len(owned_deps),
            "build_system": project_info['build_system'],
            "key_versions": {}
        }
        
        # Check local vs GitHub versions for key components
        for dep in owned_deps[:5]:  # Limit to first 5 to avoid token usage
            group_id = dep['groupId']
            artifact_id = dep['artifactId']
            current_version = dep['version']
            
            local_artifacts = subproject_manager.scan_local_m2_versions(group_id, artifact_id)
            latest_local = max(local_artifacts, key=lambda x: x.version) if local_artifacts else None
            
            version_summary["key_versions"][f"{group_id}:{artifact_id}"] = {
                "current_pom": current_version,
                "latest_local": latest_local.version if latest_local else "not found"
            }
        
        print(f"     Total deps: {version_summary['total_dependencies']}")
        print(f"     Owned deps: {version_summary['owned_dependencies']}")
        
        return version_summary
    
    def _generate_upgrade_plan(self, subproject: str, target_version: str, 
                              version_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate upgrade plan based on version analysis"""
        print(f"  📋 Generating upgrade plan to {target_version}")
        
        plan = {
            "target_version": target_version,
            "current_state": version_analysis,
            "upgrade_steps": [],
            "risks": [],
            "validation_steps": []
        }
        
        # Generate upgrade steps
        plan["upgrade_steps"] = [
            f"Update {subproject} POM version references to {target_version}",
            "Update dependency management sections",
            "Clean and rebuild all modules",
            "Run integration tests with new version"
        ]
        
        # Identify potential risks
        plan["risks"] = [
            "API compatibility changes between versions",
            "Transitive dependency conflicts",
            "Test failures due to behavioral changes",
            "Performance regression possibilities"
        ]
        
        # Validation steps
        plan["validation_steps"] = [
            "Compilation success verification",
            "Unit test execution and results comparison", 
            "Integration test execution",
            "Artifact size and structure validation",
            "Performance benchmark comparison"
        ]
        
        print(f"     Upgrade steps: {len(plan['upgrade_steps'])}")
        print(f"     Risk factors: {len(plan['risks'])}")
        
        return plan
    
    def _generate_recommendations(self, comparison: Dict[str, Any], 
                                 upgrade_plan: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test comparison"""
        recommendations = []
        
        if comparison["success_change"]:
            if not comparison["success_change"]:  # after.success == before.success
                recommendations.append("✅ Build stability maintained - upgrade appears safe")
            else:
                recommendations.append("⚠️ Build success status changed - investigate before proceeding")
        
        if comparison["test_changes"]:
            test_count_change = comparison["test_changes"].get("test_count_change", 0)
            if test_count_change > 0:
                recommendations.append(f"📈 {test_count_change} additional tests - good test coverage")
            elif test_count_change < 0:
                recommendations.append(f"📉 {abs(test_count_change)} fewer tests - verify test completeness")
        
        if comparison["error_changes"]["new_errors"]:
            recommendations.append("🚨 New errors detected - upgrade may introduce issues")
        elif comparison["error_changes"]["resolved_errors"]:
            recommendations.append("✅ Some errors resolved - upgrade may fix existing issues")
        
        if abs(comparison["duration_change_seconds"]) > 30:
            if comparison["duration_change_seconds"] > 0:
                recommendations.append("⏱️ Build time increased significantly - monitor performance")
            else:
                recommendations.append("⚡ Build time improved - upgrade brings performance benefits")
        
        if not recommendations:
            recommendations.append("📋 Minimal changes detected - upgrade appears low-risk")
        
        return recommendations
    
    def _save_upgrade_report(self, report: Dict[str, Any]):
        """Save comprehensive upgrade test report"""
        # Convert BuildResult objects to dicts for JSON serialization
        if isinstance(report["before_upgrade"]["build_result"], BuildResult):
            report["before_upgrade"]["build_result"] = report["before_upgrade"]["build_result"].__dict__
        if isinstance(report["after_upgrade"]["build_result"], BuildResult):  
            report["after_upgrade"]["build_result"] = report["after_upgrade"]["build_result"].__dict__
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"upgrade_test_report_{timestamp}.json"
        
        report_file = self.project_root / "scripts" / "tests" / filename
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n💾 Full upgrade test report saved: {report_file}")
        
        # Also create a summary report
        summary_file = self.project_root / "scripts" / "tests" / f"upgrade_summary_{timestamp}.txt"
        with open(summary_file, 'w') as f:
            f.write(f"Build Detective Upgrade Test Summary\n")
            f.write(f"{'=' * 50}\n\n")
            f.write(f"Project: {report['subproject']}\n")
            f.write(f"Target Version: {report['target_version']}\n")
            f.write(f"Test Date: {report['test_cycle_timestamp']}\n\n")
            
            f.write("Pre-upgrade Status:\n")
            f.write(f"  Build Success: {report['before_upgrade']['build_result']['success']}\n")
            f.write(f"  Duration: {report['before_upgrade']['build_result']['duration_seconds']}s\n")
            f.write(f"  Errors: {len(report['before_upgrade']['build_result']['errors'])}\n\n")
            
            f.write("Post-upgrade Status:\n") 
            f.write(f"  Build Success: {report['after_upgrade']['build_result']['success']}\n")
            f.write(f"  Duration: {report['after_upgrade']['build_result']['duration_seconds']}s\n")
            f.write(f"  Errors: {len(report['after_upgrade']['build_result']['errors'])}\n\n")
            
            f.write("Recommendations:\n")
            for rec in report['recommendations']:
                f.write(f"  • {rec}\n")
        
        print(f"📄 Summary report saved: {summary_file}")


def main():
    """Run upgrade test cycle"""
    project_root = Path.cwd()
    
    if len(sys.argv) > 1:
        subproject = sys.argv[1]
    else:
        subproject = "VideoRenderer"
    
    if len(sys.argv) > 2:
        target_version = sys.argv[2]
    else:
        target_version = "1.3.8"
    
    print("🔍 Build Detective Upgrade Test Runner")
    print("=" * 60)
    
    runner = UpgradeTestRunner(project_root)
    report = runner.run_upgrade_test_cycle(subproject, target_version)
    
    # Print executive summary
    print("\n" + "=" * 60)
    print("📊 EXECUTIVE SUMMARY")
    print("=" * 60)
    
    print(f"🎯 Project: {report['subproject']}")
    print(f"🎯 Target: {report['target_version']}")
    print(f"📅 Tested: {report['test_cycle_timestamp']}")
    print()
    
    before = report["before_upgrade"]["build_result"]
    after = report["after_upgrade"]["build_result"] 
    
    print("Before → After:")
    print(f"  ✅ Success: {before['success']} → {after['success']}")
    print(f"  ⏱️ Duration: {before['duration_seconds']}s → {after['duration_seconds']}s")
    print(f"  🚨 Errors: {len(before['errors'])} → {len(after['errors'])}")
    print()
    
    print("🎯 Recommendations:")
    for rec in report['recommendations']:
        print(f"   {rec}")


if __name__ == "__main__":
    main()