#!/usr/bin/env python3
"""
Test suite for Build Detective Artifact Manager
Validates artifact discovery, version comparison, and GitHub integration
"""

import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))
from bd_artifact_manager import ArtifactManager, Artifact


class TestArtifactManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment with temporary directories"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.manager = ArtifactManager(self.project_root)
    
    def tearDown(self):
        """Clean up temporary directories"""
        self.temp_dir.cleanup()
    
    def create_test_pom(self, content: str, filename: str = "pom.xml") -> Path:
        """Helper to create test POM files"""
        pom_path = self.project_root / filename
        pom_path.parent.mkdir(parents=True, exist_ok=True)
        pom_path.write_text(content)
        return pom_path
    
    def test_maven_pom_parsing(self):
        """Test Maven POM parsing for dependencies and repositories"""
        pom_content = """<?xml version="1.0" encoding="UTF-8"?>
        <project xmlns="http://maven.apache.org/POM/4.0.0">
            <modelVersion>4.0.0</modelVersion>
            <groupId>test.group</groupId>
            <artifactId>test-project</artifactId>
            <version>1.0.0</version>
            
            <repositories>
                <repository>
                    <id>github</id>
                    <url>https://maven.pkg.github.com/ismailubts/VideoRenderer</url>
                </repository>
            </repositories>
            
            <dependencies>
                <dependency>
                    <groupId>no.lau.vdvil</groupId>
                    <artifactId>video-renderer</artifactId>
                    <version>1.3.8</version>
                </dependency>
                <dependency>
                    <groupId>no.lau.kompost</groupId>
                    <artifactId>kompost-core</artifactId>
                    <version>0.10.1-SNAPSHOT</version>
                </dependency>
            </dependencies>
        </project>"""
        
        self.create_test_pom(pom_content)
        
        results = self.manager.scan_project_dependencies()
        
        self.assertEqual(results["build_system"], "maven")
        self.assertEqual(len(results["repositories"]), 1)
        self.assertEqual(len(results["dependencies"]), 2)
        
        # Check repository parsing
        repo = results["repositories"][0]
        self.assertEqual(repo["id"], "github")
        self.assertEqual(repo["url"], "https://maven.pkg.github.com/ismailubts/VideoRenderer")
        
        # Check dependency parsing
        deps = results["dependencies"]
        video_renderer = next(d for d in deps if d["artifactId"] == "video-renderer")
        self.assertEqual(video_renderer["groupId"], "no.lau.vdvil")
        self.assertEqual(video_renderer["version"], "1.3.8")
        self.assertTrue(video_renderer["is_owned"])
        
        kompost_core = next(d for d in deps if d["artifactId"] == "kompost-core")
        self.assertEqual(kompost_core["version"], "0.10.1-SNAPSHOT")
        self.assertTrue(kompost_core["is_owned"])
    
    def test_owned_artifact_detection(self):
        """Test detection of owned vs external artifacts"""
        test_cases = [
            ("no.lau.vdvil", True),
            ("no.lau.kompost", True),
            ("ismailubts.test", True),
            ("org.springframework", False),
            ("com.fasterxml.jackson", False),
        ]
        
        for group_id, expected in test_cases:
            with self.subTest(group_id=group_id):
                result = self.manager._is_owned_artifact(group_id)
                self.assertEqual(result, expected)
    
    def test_version_comparison(self):
        """Test semantic version comparison including SNAPSHOT handling"""
        artifacts = [
            Artifact("test.group", "test-artifact", "1.0.0", "github_packages"),
            Artifact("test.group", "test-artifact", "1.1.0-SNAPSHOT", "local"),
            Artifact("test.group", "test-artifact", "0.9.0", "local"),
            Artifact("test.group", "test-artifact", "1.0.1", "github_packages"),
        ]
        
        comparison = self.manager.compare_versions(artifacts)
        
        # Check that we have proper grouping
        self.assertIn("local", comparison["by_source"])
        self.assertIn("github_packages", comparison["by_source"])
        
        # Check latest versions
        latest = comparison["latest_by_source"]
        self.assertEqual(latest["local"].version, "1.1.0-SNAPSHOT")  # SNAPSHOT should be latest for local
        self.assertEqual(latest["github_packages"].version, "1.0.1")  # Latest release version
    
    def test_version_key_sorting(self):
        """Test version key generation for proper sorting"""
        test_cases = [
            ("1.0.0", "1.1.0", True),  # 1.1.0 > 1.0.0
            ("1.0.0-SNAPSHOT", "1.0.0", False),  # 1.0.0-SNAPSHOT < 1.0.0 (snapshot before release)
            ("1.1.0-SNAPSHOT", "1.0.0", False),  # 1.1.0-SNAPSHOT > 1.0.0
        ]
        
        for ver1, ver2, ver1_should_be_less in test_cases:
            with self.subTest(ver1=ver1, ver2=ver2):
                key1 = self.manager._version_key(ver1)
                key2 = self.manager._version_key(ver2)
                
                if ver1_should_be_less:
                    self.assertLess(key1, key2)
                else:
                    self.assertGreater(key1, key2)
    
    @patch('subprocess.run')
    def test_github_packages_api_call(self, mock_run):
        """Test GitHub Packages API integration"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.returncode = 0
        mock_response.stdout = json.dumps([
            {"name": "1.3.8", "created_at": "2024-01-01T10:00:00Z"},
            {"name": "1.3.7", "created_at": "2024-01-01T09:00:00Z"},
        ])
        mock_run.return_value = mock_response
        
        artifacts = self.manager.check_github_packages_versions(
            "ismailubts/VideoRenderer", "no.lau.vdvil", "video-renderer"
        )
        
        self.assertEqual(len(artifacts), 2)
        self.assertEqual(artifacts[0].version, "1.3.8")
        self.assertEqual(artifacts[0].source, "github_packages")
        self.assertEqual(artifacts[1].version, "1.3.7")
        
        # Verify the correct API call was made
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertIn("gh", call_args)
        self.assertIn("api", call_args)
        self.assertIn("/repos/ismailubts/VideoRenderer/packages/maven/no.lau.vdvil.video-renderer/versions", call_args)
    
    @patch('subprocess.run')
    def test_github_packages_api_failure(self, mock_run):
        """Test handling of GitHub Packages API failures"""
        # Mock failed API response
        mock_response = MagicMock()
        mock_response.returncode = 1
        mock_run.return_value = mock_response
        
        artifacts = self.manager.check_github_packages_versions(
            "ismailubts/VideoRenderer", "no.lau.vdvil", "video-renderer"
        )
        
        # Should return empty list on failure
        self.assertEqual(len(artifacts), 0)
    
    def test_recommendations_generation(self):
        """Test recommendation generation logic"""
        test_cases = [
            # Local SNAPSHOT available
            {
                "local": Artifact("test", "test", "1.0.0-SNAPSHOT", "local"),
                "github_packages": None,
                "expected_contains": ["🔧 Using local SNAPSHOT", "⚠️ No GitHub Packages found"]
            },
            # GitHub has newer version
            {
                "local": Artifact("test", "test", "1.0.0", "local"),
                "github_packages": Artifact("test", "test", "1.1.0", "github_packages"),
                "expected_contains": ["⬆️ GitHub has newer version: 1.1.0 > 1.0.0"]
            },
            # Local version ahead
            {
                "local": Artifact("test", "test", "1.2.0-SNAPSHOT", "local"),
                "github_packages": Artifact("test", "test", "1.1.0", "github_packages"),
                "expected_contains": ["🚀 Local version is ahead: 1.2.0-SNAPSHOT > 1.1.0"]
            }
        ]
        
        for i, case in enumerate(test_cases):
            with self.subTest(case=i):
                latest_versions = {
                    k: v for k, v in case.items() 
                    if k in ["local", "github_packages"] and v is not None
                }
                
                recommendations = self.manager._generate_recommendations(latest_versions)
                
                for expected_text in case["expected_contains"]:
                    found = any(expected_text in rec for rec in recommendations)
                    self.assertTrue(found, f"Expected '{expected_text}' in recommendations: {recommendations}")


class TestBDArtifactManagerIntegration(unittest.TestCase):
    """Integration tests using real project structure"""
    
    def setUp(self):
        """Set up with real project root"""
        # Assume we're running from the project root
        project_root = Path(__file__).parent.parent.parent
        if not (project_root / "pyproject.toml").exists():
            self.skipTest("Not running from project root - integration tests disabled")
        
        self.manager = ArtifactManager(project_root)
    
    def test_real_project_scanning(self):
        """Test scanning the actual PULSE-FFMPEG-MCP project"""
        results = self.manager.scan_project_dependencies()
        
        # Basic sanity checks
        self.assertIn(results["build_system"], ["maven", "unknown"])
        self.assertIsInstance(results["repositories"], list)
        self.assertIsInstance(results["dependencies"], list)
        self.assertIsInstance(results["modules"], list)
        
        # Should find some owned dependencies
        owned_deps = [dep for dep in results["dependencies"] if dep["is_owned"]]
        self.assertGreater(len(owned_deps), 0, "Should find at least some owned dependencies")
        
        # Check that we found VideoRenderer and VDVIL components
        artifact_ids = [dep["artifactId"] for dep in owned_deps]
        expected_components = ["video-renderer", "ffmpeg", "renderer"]
        
        found_expected = [comp for comp in expected_components if comp in artifact_ids]
        self.assertGreater(len(found_expected), 0, 
                          f"Should find some expected components: {expected_components}")


def main():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestArtifactManager))
    suite.addTests(loader.loadTestsFromTestCase(TestBDArtifactManagerIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code based on test results
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit(main())