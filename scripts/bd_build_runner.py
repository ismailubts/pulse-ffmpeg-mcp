#!/usr/bin/env python3
"""
Build Detective Build Runner - Local Build Testing and Validation
Handles Maven builds, test execution, and result comparison to save expensive tokens
"""

import subprocess
import json
import time
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class BuildResult:
    timestamp: str
    project_path: str
    build_command: str
    success: bool
    duration_seconds: float
    exit_code: int
    stdout_lines: int
    stderr_lines: int
    test_results: Dict[str, Any]
    artifact_info: Dict[str, Any]
    build_hash: str
    errors: List[str]
    warnings: List[str]


class BuildRunner:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results_cache = {}
        
    def run_maven_build(self, subproject: str = "", 
                       goals: List[str] = None, 
                       profiles: List[str] = None,
                       skip_tests: bool = False) -> BuildResult:
        """Run Maven build and capture comprehensive results"""
        if goals is None:
            goals = ["clean", "package"]
        
        build_path = self.project_root / subproject if subproject else self.project_root
        
        # Build Maven command
        cmd = ["mvn"] + goals
        
        if profiles:
            cmd.extend([f"-P{','.join(profiles)}"])
        
        if skip_tests:
            cmd.append("-DskipTests")
        
        cmd_str = " ".join(cmd)
        print(f"🔨 Running: {cmd_str}")
        print(f"📁 In: {build_path}")
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=build_path,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            duration = time.time() - start_time
            
            # Parse output for key information
            test_results = self._parse_test_results(result.stdout, result.stderr)
            artifact_info = self._parse_artifact_info(result.stdout, build_path)
            errors = self._extract_errors(result.stderr, result.stdout)
            warnings = self._extract_warnings(result.stderr, result.stdout)
            
            # Generate build hash for comparison
            build_hash = self._generate_build_hash(result.stdout, result.stderr)
            
            build_result = BuildResult(
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                project_path=str(build_path),
                build_command=cmd_str,
                success=result.returncode == 0,
                duration_seconds=round(duration, 2),
                exit_code=result.returncode,
                stdout_lines=len(result.stdout.split('\n')),
                stderr_lines=len(result.stderr.split('\n')),
                test_results=test_results,
                artifact_info=artifact_info,
                build_hash=build_hash,
                errors=errors,
                warnings=warnings
            )
            
            # Cache result
            cache_key = f"{subproject}:{cmd_str}"
            self.results_cache[cache_key] = build_result
            
            return build_result
            
        except subprocess.TimeoutExpired:
            return BuildResult(
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                project_path=str(build_path),
                build_command=cmd_str,
                success=False,
                duration_seconds=600,
                exit_code=-1,
                stdout_lines=0,
                stderr_lines=0,
                test_results={"error": "Build timeout after 10 minutes"},
                artifact_info={},
                build_hash="timeout",
                errors=["Build timeout after 10 minutes"],
                warnings=[]
            )
    
    def _parse_test_results(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Extract test results from Maven output with multi-module support"""
        test_info = {
            "tests_run": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "test_classes": [],
            "failed_tests": [],
            "duration_seconds": 0,
            "module_results": {},
            "reactor_summary": {}
        }
        
        # Look for Surefire test results (aggregate across all modules)
        surefire_pattern = r"Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)"
        matches = re.findall(surefire_pattern, stdout)
        
        for match in matches:
            test_info["tests_run"] += int(match[0])
            test_info["failures"] += int(match[1])
            test_info["errors"] += int(match[2])
            test_info["skipped"] += int(match[3])
        
        # Parse per-module test results
        module_test_pattern = r"Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+).*?in (.+)"
        module_matches = re.findall(module_test_pattern, stdout)
        
        for match in module_matches:
            module_name = match[4].strip()
            test_info["module_results"][module_name] = {
                "tests_run": int(match[0]),
                "failures": int(match[1]),
                "errors": int(match[2]), 
                "skipped": int(match[3])
            }
        
        # Extract failed test names with module context
        failed_test_pattern = r"FAILURE.*?(\w+\.\w+\.\w+)\(\)"
        failed_tests = re.findall(failed_test_pattern, stdout + stderr)
        test_info["failed_tests"] = list(set(failed_tests))
        
        # Parse multi-module reactor summary
        test_info["reactor_summary"] = self._parse_reactor_summary(stdout)
        
        # Extract test duration (prefer reactor total time)
        if test_info["reactor_summary"].get("total_build_time"):
            test_info["duration_seconds"] = test_info["reactor_summary"]["total_build_time"]
        else:
            time_pattern = r"Total time:\s+(\d+\.?\d*)\s*s"
            time_match = re.search(time_pattern, stdout)
            if time_match:
                test_info["duration_seconds"] = float(time_match.group(1))
        
        return test_info
    
    def _parse_reactor_summary(self, stdout: str) -> Dict[str, Any]:
        """Parse Maven reactor summary for multi-module builds"""
        reactor_info = {
            "total_modules": 0,
            "successful_modules": 0,
            "failed_modules": 0,
            "skipped_modules": 0,
            "module_results": [],
            "total_build_time": 0,
            "build_status": "UNKNOWN"
        }
        
        # Parse reactor summary section
        summary_pattern = r"Reactor Summary for (.+?):\s*\n([\s\S]*?)BUILD (SUCCESS|FAILURE)"
        summary_match = re.search(summary_pattern, stdout)
        
        if summary_match:
            project_name = summary_match.group(1)
            summary_content = summary_match.group(2)
            reactor_info["build_status"] = summary_match.group(3)
            
            # Parse individual module results
            module_pattern = r"\[INFO\]\s+(.+?)\s+\.+\s+(SUCCESS|FAILURE|SKIPPED)\s+\[\s*([0-9.]+)\s*s\s*\]"
            modules = re.findall(module_pattern, summary_content)
            
            for module_name, status, duration in modules:
                module_info = {
                    "name": module_name.strip(),
                    "status": status,
                    "duration_seconds": float(duration)
                }
                reactor_info["module_results"].append(module_info)
                reactor_info["total_modules"] += 1
                
                if status == "SUCCESS":
                    reactor_info["successful_modules"] += 1
                elif status == "FAILURE":
                    reactor_info["failed_modules"] += 1
                elif status == "SKIPPED":
                    reactor_info["skipped_modules"] += 1
        
        # Parse total time
        total_time_pattern = r"Total time:\s+([0-9.]+)\s*s"
        time_match = re.search(total_time_pattern, stdout)
        if time_match:
            reactor_info["total_build_time"] = float(time_match.group(1))
        
        return reactor_info
    
    def _parse_artifact_info(self, stdout: str, build_path: Path) -> Dict[str, Any]:
        """Extract information about generated artifacts"""
        artifact_info = {
            "jars_created": [],
            "target_size_mb": 0,
            "main_artifact": None
        }
        
        # Look for JAR creation messages
        jar_pattern = r"Building jar: (.+\.jar)"
        jar_matches = re.findall(jar_pattern, stdout)
        
        for jar_path in jar_matches:
            jar_file = Path(jar_path)
            if jar_file.exists():
                size_mb = jar_file.stat().st_size / (1024 * 1024)
                artifact_info["jars_created"].append({
                    "path": str(jar_file),
                    "size_mb": round(size_mb, 2),
                    "name": jar_file.name
                })
        
        # Calculate total target directory size
        target_dir = build_path / "target"
        if target_dir.exists():
            total_size = sum(f.stat().st_size for f in target_dir.rglob('*') if f.is_file())
            artifact_info["target_size_mb"] = round(total_size / (1024 * 1024), 2)
        
        # Identify main artifact (usually the largest JAR)
        if artifact_info["jars_created"]:
            main_jar = max(artifact_info["jars_created"], key=lambda x: x["size_mb"])
            artifact_info["main_artifact"] = main_jar["name"]
        
        return artifact_info
    
    def _extract_errors(self, stderr: str, stdout: str) -> List[str]:
        """Extract error messages from build output"""
        errors = []
        
        # Common Maven error patterns
        error_patterns = [
            r"\[ERROR\]\s+(.+)",
            r"COMPILATION ERROR.*?:\s*(.+)",
            r"BUILD FAILURE",
            r"Failed to execute goal.*?:\s*(.+)",
            r".*Exception.*?:\s*(.+)"
        ]
        
        combined_output = stderr + "\n" + stdout
        
        for pattern in error_patterns:
            matches = re.findall(pattern, combined_output, re.MULTILINE)
            errors.extend(matches)
        
        # Clean and deduplicate
        cleaned_errors = []
        for error in errors:
            clean_error = error.strip()
            if clean_error and clean_error not in cleaned_errors and len(clean_error) > 10:
                cleaned_errors.append(clean_error)
        
        return cleaned_errors[:10]  # Limit to top 10 errors
    
    def _extract_warnings(self, stderr: str, stdout: str) -> List[str]:
        """Extract warning messages from build output"""
        warnings = []
        
        warning_patterns = [
            r"\[WARNING\]\s+(.+)",
            r"warning:\s*(.+)",
            r"deprecated.*?:\s*(.+)"
        ]
        
        combined_output = stderr + "\n" + stdout
        
        for pattern in warning_patterns:
            matches = re.findall(pattern, combined_output, re.MULTILINE | re.IGNORECASE)
            warnings.extend(matches)
        
        # Clean and deduplicate
        cleaned_warnings = []
        for warning in warnings:
            clean_warning = warning.strip()
            if clean_warning and clean_warning not in cleaned_warnings and len(clean_warning) > 10:
                cleaned_warnings.append(clean_warning)
        
        return cleaned_warnings[:5]  # Limit to top 5 warnings
    
    def _generate_build_hash(self, stdout: str, stderr: str) -> str:
        """Generate hash of key build output for comparison"""
        # Focus on key indicators that would change between builds
        key_content = []
        
        # Extract test results, compilation info, artifact creation
        for line in stdout.split('\n'):
            if any(keyword in line.lower() for keyword in 
                   ['tests run:', 'building jar:', 'compilation error', 'build success', 'build failure']):
                key_content.append(line.strip())
        
        content_str = '\n'.join(key_content)
        return hashlib.md5(content_str.encode()).hexdigest()[:12]
    
    def compare_build_results(self, before: BuildResult, after: BuildResult) -> Dict[str, Any]:
        """Compare two build results and highlight differences"""
        comparison = {
            "timestamp_comparison": f"{before.timestamp} → {after.timestamp}",
            "success_change": before.success != after.success,
            "duration_change_seconds": round(after.duration_seconds - before.duration_seconds, 2),
            "test_changes": {},
            "artifact_changes": {},
            "error_changes": {},
            "hash_changed": before.build_hash != after.build_hash,
            "summary": []
        }
        
        # Test result changes
        if before.test_results != after.test_results:
            comparison["test_changes"] = {
                "before": before.test_results,
                "after": after.test_results,
                "test_count_change": after.test_results.get("tests_run", 0) - before.test_results.get("tests_run", 0),
                "failure_count_change": after.test_results.get("failures", 0) - before.test_results.get("failures", 0)
            }
        
        # Artifact changes
        before_artifacts = {a["name"]: a["size_mb"] for a in before.artifact_info.get("jars_created", [])}
        after_artifacts = {a["name"]: a["size_mb"] for a in after.artifact_info.get("jars_created", [])}
        
        if before_artifacts != after_artifacts:
            comparison["artifact_changes"] = {
                "before": before_artifacts,
                "after": after_artifacts,
                "size_changes": {name: after_artifacts.get(name, 0) - before_artifacts.get(name, 0) 
                                for name in set(before_artifacts.keys()) | set(after_artifacts.keys())}
            }
        
        # Error changes
        comparison["error_changes"] = {
            "before_errors": len(before.errors),
            "after_errors": len(after.errors),
            "new_errors": [e for e in after.errors if e not in before.errors],
            "resolved_errors": [e for e in before.errors if e not in after.errors]
        }
        
        # Generate summary
        if comparison["success_change"]:
            if after.success:
                comparison["summary"].append("✅ Build now succeeds (was failing)")
            else:
                comparison["summary"].append("❌ Build now fails (was succeeding)")
        
        if comparison["test_changes"]:
            test_change = comparison["test_changes"]["test_count_change"]
            if test_change != 0:
                comparison["summary"].append(f"🧪 Test count changed by {test_change}")
        
        if comparison["duration_change_seconds"] > 10:
            comparison["summary"].append(f"⏱️ Build time increased by {comparison['duration_change_seconds']}s")
        elif comparison["duration_change_seconds"] < -10:
            comparison["summary"].append(f"⚡ Build time decreased by {abs(comparison['duration_change_seconds'])}s")
        
        if comparison["error_changes"]["new_errors"]:
            comparison["summary"].append(f"🚨 {len(comparison['error_changes']['new_errors'])} new errors")
        
        if comparison["error_changes"]["resolved_errors"]:
            comparison["summary"].append(f"✅ {len(comparison['error_changes']['resolved_errors'])} errors resolved")
        
        if not comparison["summary"]:
            comparison["summary"].append("📋 No significant changes detected")
        
        return comparison
    
    def save_results(self, results: List[BuildResult], filename: str = "build_results.json"):
        """Save build results to file for later analysis"""
        results_data = [asdict(result) for result in results]
        
        output_file = self.project_root / "scripts" / "tests" / filename
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"💾 Build results saved to {output_file}")
    
    def load_results(self, filename: str = "build_results.json") -> List[BuildResult]:
        """Load previously saved build results"""
        results_file = self.project_root / "scripts" / "tests" / filename
        
        if not results_file.exists():
            return []
        
        with open(results_file, 'r') as f:
            data = json.load(f)
        
        return [BuildResult(**item) for item in data]


def main():
    """Test build runner functionality"""
    import sys
    
    project_root = Path.cwd()
    if len(sys.argv) > 1:
        project_root = Path(sys.argv[1])
    
    runner = BuildRunner(project_root)
    
    print("🔍 Build Detective Build Runner Test")
    print("=" * 50)
    
    # Test VideoRenderer subproject
    print("\n🎥 Testing VideoRenderer build...")
    vr_result = runner.run_maven_build("VideoRenderer", ["clean", "compile"], skip_tests=True)
    
    print(f"✅ Success: {vr_result.success}")
    print(f"⏱️ Duration: {vr_result.duration_seconds}s")
    print(f"🧪 Tests: {vr_result.test_results}")
    print(f"📦 Artifacts: {len(vr_result.artifact_info.get('jars_created', []))} JARs")
    print(f"🚨 Errors: {len(vr_result.errors)}")
    print(f"⚠️ Warnings: {len(vr_result.warnings)}")
    
    if vr_result.errors:
        print("\n🚨 Error Details:")
        for error in vr_result.errors[:3]:
            print(f"   • {error}")
    
    # Save results
    runner.save_results([vr_result], "test_build_results.json")


if __name__ == "__main__":
    main()