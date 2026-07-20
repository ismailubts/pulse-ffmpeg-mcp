#!/usr/bin/env python3
"""
Build Detective Artifact Manager - Version and Repository Analysis
Fast, cheap analysis using local filesystem and basic API calls to understand artifact status
"""

import subprocess
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from packaging import version


@dataclass
class Artifact:
    group_id: str
    artifact_id: str
    version: str
    source: str  # "local", "github_packages", "maven_central"
    path: Optional[str] = None
    release_date: Optional[str] = None


class ArtifactManager:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.local_m2 = Path.home() / ".m2" / "repository"
        self.owned_repos = [
            "ismailubts/VideoRenderer",
            "ismailubts/pulse-ffmpeg-mcp",
            "ismailubts/vdvil",
            "ismailubts/komposteur"
        ]
    
    def scan_project_dependencies(self) -> Dict[str, Any]:
        """Scan project for Maven/Gradle dependencies and repository configuration"""
        pom_files = list(self.project_root.rglob("pom.xml"))
        gradle_files = list(self.project_root.rglob("build.gradle*"))
        
        results = {
            "build_system": "unknown",
            "repositories": [],
            "dependencies": [],
            "modules": []
        }
        
        if pom_files:
            results["build_system"] = "maven"
            for pom_file in pom_files:
                self._parse_maven_pom(pom_file, results)
        
        elif gradle_files:
            results["build_system"] = "gradle"
            # TODO: Implement Gradle parsing
            results["note"] = "Gradle parsing not implemented yet"
            
        return results
    
    def _parse_maven_pom(self, pom_file: Path, results: Dict[str, Any]):
        """Parse Maven POM file for dependencies and repositories"""
        try:
            tree = ET.parse(pom_file)
            root = tree.getroot()
            ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
            
            # Extract repositories
            repos = root.findall('.//m:repository', ns)
            for repo in repos:
                repo_id = repo.find('m:id', ns)
                repo_url = repo.find('m:url', ns)
                if repo_id is not None and repo_url is not None:
                    repo_info = {
                        "id": repo_id.text,
                        "url": repo_url.text,
                        "file": str(pom_file.relative_to(self.project_root))
                    }
                    if repo_info not in results["repositories"]:
                        results["repositories"].append(repo_info)
            
            # Extract dependencies (managed and direct)
            deps = root.findall('.//m:dependency', ns)
            for dep in deps:
                group_id = dep.find('m:groupId', ns)
                artifact_id = dep.find('m:artifactId', ns)
                version_elem = dep.find('m:version', ns)
                
                if group_id is not None and artifact_id is not None:
                    dep_version = version_elem.text if version_elem is not None else "unknown"
                    dep_info = {
                        "groupId": group_id.text,
                        "artifactId": artifact_id.text,
                        "version": dep_version,
                        "file": str(pom_file.relative_to(self.project_root)),
                        "is_owned": self._is_owned_artifact(group_id.text)
                    }
                    
                    # Avoid duplicates
                    dep_key = f"{group_id.text}:{artifact_id.text}"
                    if not any(d.get("groupId") == group_id.text and d.get("artifactId") == artifact_id.text 
                              for d in results["dependencies"]):
                        results["dependencies"].append(dep_info)
            
            # Module information
            modules = root.findall('.//m:module', ns)
            for module in modules:
                if module.text:
                    module_path = pom_file.parent / module.text
                    if module_path.exists():
                        results["modules"].append({
                            "name": module.text,
                            "path": str(module_path.relative_to(self.project_root)),
                            "parent_pom": str(pom_file.relative_to(self.project_root))
                        })
                        
        except ET.ParseError as e:
            results.setdefault("parse_errors", []).append(f"Error parsing {pom_file}: {e}")
    
    def _is_owned_artifact(self, group_id: str) -> bool:
        """Check if artifact belongs to our owned projects"""
        owned_patterns = ["no.lau", "ismailubts", "vdvil", "kompost"]
        return any(pattern in group_id.lower() for pattern in owned_patterns)
    
    def scan_local_m2_versions(self, group_id: str, artifact_id: str) -> List[Artifact]:
        """Scan ~/.m2/repository for local versions of an artifact"""
        group_path = self.local_m2 / group_id.replace('.', '/')
        artifact_path = group_path / artifact_id
        
        artifacts = []
        
        if not artifact_path.exists():
            return artifacts
        
        # Find version directories
        for version_dir in artifact_path.iterdir():
            if version_dir.is_dir() and not version_dir.name.startswith('.'):
                # Look for JAR files in this version
                jar_files = list(version_dir.glob("*.jar"))
                if jar_files:
                    artifacts.append(Artifact(
                        group_id=group_id,
                        artifact_id=artifact_id,
                        version=version_dir.name,
                        source="local",
                        path=str(version_dir)
                    ))
        
        return artifacts
    
    def check_github_packages_versions(self, repo: str, group_id: str, artifact_id: str) -> List[Artifact]:
        """Check GitHub Packages for available versions"""
        artifacts = []
        
        try:
            # Use GitHub CLI to get package versions
            cmd = ['gh', 'api', f'/repos/{repo}/packages/maven/{group_id}.{artifact_id}/versions']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                versions_data = json.loads(result.stdout)
                for version_info in versions_data:
                    artifacts.append(Artifact(
                        group_id=group_id,
                        artifact_id=artifact_id,
                        version=version_info.get('name', 'unknown'),
                        source="github_packages",
                        release_date=version_info.get('created_at')
                    ))
            
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            # Silently fail for now
            pass
        
        return artifacts
    
    def compare_versions(self, artifacts: List[Artifact]) -> Dict[str, Any]:
        """Compare versions and determine latest/recommended versions"""
        if not artifacts:
            return {"status": "no_artifacts"}
        
        # Group by source
        by_source = {}
        for artifact in artifacts:
            by_source.setdefault(artifact.source, []).append(artifact)
        
        # Find latest versions
        latest_versions = {}
        for source, source_artifacts in by_source.items():
            try:
                # Sort by version, handle SNAPSHOT versions specially
                sorted_artifacts = sorted(source_artifacts, 
                                        key=lambda a: self._version_key(a.version), 
                                        reverse=True)
                latest_versions[source] = sorted_artifacts[0] if sorted_artifacts else None
            except Exception:
                # Fallback to simple string comparison
                latest_versions[source] = max(source_artifacts, key=lambda a: a.version)
        
        return {
            "by_source": by_source,
            "latest_by_source": latest_versions,
            "recommendations": self._generate_recommendations(latest_versions)
        }
    
    def _version_key(self, version_str: str) -> Tuple:
        """Create sortable version key, handling SNAPSHOT versions"""
        try:
            # Handle SNAPSHOT versions by treating them as pre-release
            if version_str.endswith('-SNAPSHOT'):
                base_version = version_str[:-9]  # Remove -SNAPSHOT
                return (version.parse(base_version), 1)  # 1 = snapshot (higher than release)
            else:
                return (version.parse(version_str), 0)  # 0 = release
        except:
            # Fallback to string comparison
            return (version_str, 0)
    
    def _generate_recommendations(self, latest_versions: Dict[str, Artifact]) -> List[str]:
        """Generate recommendations based on version analysis"""
        recommendations = []
        
        local = latest_versions.get("local")
        github = latest_versions.get("github_packages")
        
        if local and local.version.endswith("-SNAPSHOT"):
            recommendations.append(f"🔧 Using local SNAPSHOT {local.version} - good for development")
        
        if github and local:
            try:
                github_ver = self._version_key(github.version)
                local_ver = self._version_key(local.version)
                
                if github_ver > local_ver:
                    recommendations.append(f"⬆️ GitHub has newer version: {github.version} > {local.version}")
                elif local_ver > github_ver:
                    recommendations.append(f"🚀 Local version is ahead: {local.version} > {github.version}")
            except:
                recommendations.append("🔍 Version comparison failed - manual check needed")
        
        if not local and github:
            recommendations.append(f"📦 No local build - using GitHub Packages {github.version}")
        
        if not github and local:
            recommendations.append("⚠️ No GitHub Packages found - only local available")
        
        return recommendations


def main():
    """Main entry point for artifact analysis"""
    import sys
    
    if len(sys.argv) > 1:
        project_path = Path(sys.argv[1])
    else:
        project_path = Path.cwd()
    
    print(f"🔍 Build Detective Artifact Analysis - {project_path.name}")
    print("=" * 60)
    
    manager = ArtifactManager(project_path)
    
    # Scan project dependencies
    project_info = manager.scan_project_dependencies()
    
    print(f"📋 Build System: {project_info['build_system']}")
    print(f"📦 Repositories: {len(project_info['repositories'])}")
    print(f"🔗 Dependencies: {len(project_info['dependencies'])}")
    print(f"📁 Modules: {len(project_info['modules'])}")
    print()
    
    # Analyze owned dependencies
    owned_deps = [dep for dep in project_info['dependencies'] if dep['is_owned']]
    
    if owned_deps:
        print("🏠 Owned Dependencies Analysis:")
        print("-" * 40)
        
        for dep in owned_deps:
            group_id = dep['groupId']
            artifact_id = dep['artifactId']
            current_version = dep['version']
            
            print(f"\n📦 {group_id}:{artifact_id}")
            print(f"   Current: {current_version}")
            
            # Check local versions
            local_artifacts = manager.scan_local_m2_versions(group_id, artifact_id)
            
            # Check GitHub versions for owned repos
            github_artifacts = []
            for repo in manager.owned_repos:
                github_artifacts.extend(
                    manager.check_github_packages_versions(repo, group_id, artifact_id)
                )
            
            # Compare versions
            all_artifacts = local_artifacts + github_artifacts
            comparison = manager.compare_versions(all_artifacts)
            
            if comparison.get("status") == "no_artifacts":
                print("   ❌ No versions found")
                continue
            
            # Show findings
            latest_by_source = comparison.get("latest_by_source", {})
            for source, artifact in latest_by_source.items():
                if artifact:
                    print(f"   {source}: {artifact.version}")
            
            # Show recommendations
            for rec in comparison.get("recommendations", []):
                print(f"   {rec}")
    
    else:
        print("ℹ️ No owned dependencies found in this project")


if __name__ == "__main__":
    main()