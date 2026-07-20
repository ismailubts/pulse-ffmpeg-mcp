"""
Uber Kompost Bridge - Updated integration using the uber-kompost JAR
"""
import json
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class UberKompostBridge:
    """Bridge to uber-kompost JAR using JSON API"""
    
    def __init__(self):
        self.jar_path = None
        self._initialized = False
        
    def initialize(self) -> bool:
        """Initialize by finding the uber-kompost JAR"""
        try:
            # Look for uber-kompost JAR in common locations
            possible_paths = [
                Path.home() / ".m2/repository/no/lau/kompost/uber-kompost/0.8-SNAPSHOT/uber-kompost-0.8-SNAPSHOT.jar",
                Path("uber-kompost/target/uber-kompost-0.8-SNAPSHOT.jar"),
                Path("../uber-kompost/target/uber-kompost-0.8-SNAPSHOT.jar")
            ]
            
            for jar_path in possible_paths:
                if jar_path.exists():
                    self.jar_path = str(jar_path)
                    break
            
            if not self.jar_path:
                logger.error("uber-kompost JAR not found. Build it with: mvn clean package -pl uber-kompost -DskipTests")
                return False
                
            # Test JAR with version command
            result = subprocess.run(
                ["java", "-jar", self.jar_path, "version"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                logger.info(f"Uber-kompost JAR found: {Path(self.jar_path).stat().st_size / (1024*1024):.1f}MB")
                self._initialized = True
                return True
            else:
                logger.error(f"uber-kompost JAR test failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize uber-kompost bridge: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if bridge is ready"""
        return self._initialized and self.jar_path and Path(self.jar_path).exists()
    
    def call_kompost(self, operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call uber-kompost with JSON API"""
        if not self.is_available():
            return {"success": False, "error": "Bridge not initialized"}
            
        try:
            result = subprocess.run([
                "java", "-jar", self.jar_path,
                "process", json.dumps(operation_data)
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                try:
                    response = json.loads(result.stdout)
                    return {"success": True, **response}
                except json.JSONDecodeError:
                    return {
                        "success": False, 
                        "error": "Invalid JSON response",
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    }
            else:
                return {
                    "success": False,
                    "error": f"Process failed with code {result.returncode}",
                    "stderr": result.stderr
                }
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Operation timeout (5 minutes)"}
        except Exception as e:
            return {"success": False, "error": f"Call failed: {str(e)}"}
    
    def health_check(self) -> Dict[str, Any]:
        """Check system health"""
        return self.call_kompost({"operation": "health_check"})
    
    def process_kompost_json(self, kompost_path: str) -> Dict[str, Any]:
        """Process kompost.json file using uber-kompost"""
        if not Path(kompost_path).exists():
            return {"success": False, "error": f"Kompost file not found: {kompost_path}"}
            
        try:
            # Read the kompost.json file
            with open(kompost_path, 'r') as f:
                kompost_data = json.load(f)
            
            # Call uber-kompost with video processing operation
            return self.call_kompost({
                "operation": "process_video",
                "input_path": kompost_path,
                "output_path": kompost_path.replace('.json', '_processed.mp4'),
                "composition": json.dumps(kompost_data)
            })
            
        except Exception as e:
            return {"success": False, "error": f"Failed to process kompost: {str(e)}"}
    
    def create_composition(self, build_komposition: str, fetch_kompositions: str) -> Dict[str, Any]:
        """Create video composition"""
        return self.call_kompost({
            "operation": "create_composition",
            "build_komposition": build_komposition,
            "fetch_kompositions": fetch_kompositions
        })
    
    def get_version(self) -> str:
        """Get uber-kompost version"""
        if not self.is_available():
            return "Bridge not available"
            
        try:
            result = subprocess.run(
                ["java", "-jar", self.jar_path, "version"],
                capture_output=True, text=True, timeout=10
            )
            return result.stdout.strip() if result.returncode == 0 else f"Error: {result.stderr}"
        except Exception as e:
            return f"Version check failed: {e}"
    
    def shutdown(self):
        """Clean shutdown"""
        self._initialized = False

# Global bridge instance for uber-kompost
_uber_bridge_instance: Optional[UberKompostBridge] = None

def get_uber_bridge() -> UberKompostBridge:
    """Get or create the global uber-kompost bridge instance"""
    global _uber_bridge_instance
    if _uber_bridge_instance is None:
        _uber_bridge_instance = UberKompostBridge()
        _uber_bridge_instance.initialize()
    return _uber_bridge_instance