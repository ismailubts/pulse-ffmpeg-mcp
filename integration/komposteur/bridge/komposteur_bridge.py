"""
Komposteur Bridge - Python-Java integration layer
Provides access to Komposteur's production-proven video processing algorithms
"""
import os
import subprocess
import json
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class KomposteurBridge:
    """Bridge to Komposteur Java library using direct Java subprocess calls"""
    
    def __init__(self):
        self.jar_path = None
        self._initialized = False
        self.version = "0.11.0"  # Updated with CI/CD-enabled release
        
    def initialize(self) -> bool:
        """Initialize the Komposteur bridge by locating the JAR"""
        try:
            # Find Komposteur JAR - prefer CI/CD-enabled version
            # Try new CI/CD-enabled versions first
            possible_jars = [
                # Latest CI/CD-enabled release
                "~/.m2/repository/no/lau/kompost/komposteur-core/0.11.0/komposteur-core-0.11.0-jar-with-dependencies.jar",
                # Previous working release
                "~/.m2/repository/no/lau/kompost/uber-kompost/0.10.1/uber-kompost-0.10.1-shaded.jar",
                # Development snapshot
                "~/.m2/repository/no/lau/kompost/komposteur-core/0.9-SNAPSHOT/komposteur-core-0.9-SNAPSHOT-jar-with-dependencies.jar",
                # Fallback to old version
                "~/.m2/repository/no/lau/kompost/komposteur-core/0.8-SNAPSHOT/komposteur-core-0.8-SNAPSHOT-jar-with-dependencies.jar"
            ]
            
            for jar_path in possible_jars:
                expanded_path = os.path.expanduser(jar_path)
                if Path(expanded_path).exists():
                    self.jar_path = expanded_path
                    logger.info(f"🔧 Found Komposteur JAR: {Path(self.jar_path).name}")
                    break
            
            if not self.jar_path:
                logger.error("❌ No Komposteur JAR found in any expected location")
                return False
            
            if not Path(self.jar_path).exists():
                logger.error(f"Komposteur JAR not found at {self.jar_path}")
                return False
                
            # Test if we can run Java with the JAR
            test_cmd = ["java", "-cp", self.jar_path, "no.lau.komposteur.core.KomposteurCore"]
            try:
                result = subprocess.run(test_cmd, capture_output=True, timeout=5)
                logger.info(f"Komposteur JAR accessible: {Path(self.jar_path).stat().st_size / 1024:.1f}KB")
                self._initialized = True
                return True
            except subprocess.TimeoutExpired:
                # This is expected since there's no main method, but it means the JAR loads
                logger.info(f"Komposteur JAR accessible: {Path(self.jar_path).stat().st_size / 1024:.1f}KB")
                self._initialized = True
                return True
            except Exception as e:
                logger.error(f"Failed to test Komposteur JAR: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize Komposteur bridge: {e}")
            return False
    
    def shutdown(self):
        """Clean shutdown - no resources to clean up for subprocess approach"""
        self._initialized = False
    
    def is_available(self) -> bool:
        """Check if Komposteur bridge is initialized and available"""
        return self._initialized and self.jar_path and Path(self.jar_path).exists()
    
    def beat_sync(self, video_path: str, audio_path: str, bpm: float) -> Dict[str, Any]:
        """Beat-synchronize video using Komposteur's 120 BPM = 8s per 16 beats formula"""
        if not self.is_available():
            return {"success": False, "error": "Komposteur bridge not initialized"}
            
        # TODO: Implement actual Java call to Komposteur BeatSynchronizer
        # For now, return mock data showing the expected workflow
        duration = (16 / bpm) * 60  # 120 BPM = 8s per 16 beats formula
        
        return {
            "success": False,  # Mark as false until real implementation
            "error": "MOCK IMPLEMENTATION - Need actual Komposteur API documentation",
            "expected_workflow": {
                "java_class": "no.lau.komposteur.core.timing.BeatSynchronizer",
                "expected_method": "beatSync(String videoPath, String audioPath, double bpm)",
                "expected_output": {
                    "output_path": f"/tmp/music/temp/komposteur_sync_{int(time.time())}.mp4",
                    "duration": duration,
                    "beat_count": 16,
                    "processing_time": 2.3
                }
            }
        }
    
    def extract_segment(self, video_path: str, start_time: float, end_time: float) -> Dict[str, Any]:
        """Extract video segment with microsecond precision"""
        if not self.is_available():
            return {"success": False, "error": "Komposteur bridge not initialized"}
            
        # TODO: Implement actual Java call
        return {
            "success": False,
            "error": "MOCK IMPLEMENTATION - Need actual Komposteur API documentation",
            "expected_workflow": {
                "java_class": "no.lau.komposteur.core.KomposteurCore", 
                "expected_method": "extractSegment(String path, double start, double end)",
                "expected_output": {
                    "output_path": f"/tmp/music/temp/komposteur_segment_{int(start_time)}_{int(end_time)}.mp4",
                    "actual_start": start_time,
                    "actual_end": end_time,
                    "frame_count": int((end_time - start_time) * 30)  # Assuming 30fps
                }
            }
        }
    
    def validate_media(self, file_path: str) -> Dict[str, Any]:
        """Comprehensive media file validation using Komposteur pipeline"""
        if not self.is_available():
            return {"success": False, "error": "Komposteur bridge not initialized"}
            
        # TODO: Implement actual Java call
        return {
            "success": False,
            "error": "MOCK IMPLEMENTATION - Need actual Komposteur API documentation", 
            "expected_workflow": {
                "java_class": "no.lau.komposteur.core.validation.MediaValidator",
                "expected_method": "validateMedia(String filePath)",
                "expected_output": {
                    "valid": True,
                    "format": "mp4",
                    "duration": 30.5,
                    "resolution": {"width": 1920, "height": 1080},
                    "quality_score": 0.85,
                    "issues": []
                }
            }
        }
    
    def process_kompost_json(self, kompost_path: str) -> Dict[str, Any]:
        """Process a kompost.json file using Komposteur's curated FFMPEG workflows"""
        if not self.is_available():
            return {"success": False, "error": "Komposteur bridge not initialized"}
            
        try:
            # Create a simple Java wrapper to call the new API
            java_wrapper = f'''
import no.lau.komposteur.core.KomposteurEntryPoint;
import java.util.Map;

public class KomposteurWrapper {{
    public static void main(String[] args) {{
        try {{
            KomposteurEntryPoint komposteur = new KomposteurEntryPoint();
            komposteur.initialize();
            
            String result = komposteur.processKompost(args[0]);
            System.out.println("RESULT:" + result);
            
            komposteur.shutdown();
        }} catch (Exception e) {{
            System.err.println("ERROR:" + e.getMessage());
            e.printStackTrace();
        }}
    }}
}}
'''
            
            # Write the wrapper to a temporary file
            wrapper_file = "/tmp/KomposteurWrapper.java"
            with open(wrapper_file, 'w') as f:
                f.write(java_wrapper)
            
            # Compile the wrapper
            compile_cmd = [
                "javac", "-cp", self.jar_path,
                wrapper_file
            ]
            compile_result = subprocess.run(compile_cmd, capture_output=True, text=True)
            
            if compile_result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Failed to compile Java wrapper: {compile_result.stderr}"
                }
            
            # Run the wrapper
            run_cmd = [
                "java", "-cp", f"{self.jar_path}:/tmp",
                "KomposteurWrapper", kompost_path
            ]
            
            run_result = subprocess.run(run_cmd, capture_output=True, text=True, timeout=300)
            
            if run_result.returncode == 0:
                # Parse the result
                output_lines = run_result.stdout.strip().split('\n')
                result_line = None
                for line in output_lines:
                    if line.startswith("RESULT:"):
                        result_line = line[7:]  # Remove "RESULT:" prefix
                        break
                
                if result_line:
                    return {
                        "success": True,
                        "output_video_path": "Processing completed - check Komposteur output",
                        "processing_log": [f"Komposteur result: {result_line}"],
                        "curated_effects_used": ["Real Komposteur processing"],
                        "ffmpeg_commands_executed": "Unknown (handled by Komposteur)",
                        "total_processing_time": "Unknown",
                        "raw_result": result_line
                    }
                else:
                    return {
                        "success": False,
                        "error": "No result found in Komposteur output",
                        "stdout": run_result.stdout,
                        "stderr": run_result.stderr
                    }
            else:
                error_lines = run_result.stderr.strip().split('\n')
                error_msg = None
                for line in error_lines:
                    if line.startswith("ERROR:"):
                        error_msg = line[6:]  # Remove "ERROR:" prefix
                        break
                
                return {
                    "success": False,
                    "error": error_msg or "Komposteur processing failed",
                    "stdout": run_result.stdout,
                    "stderr": run_result.stderr,
                    "return_code": run_result.returncode
                }
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Komposteur processing timeout (5 minutes)"}
        except Exception as e:
            return {"success": False, "error": f"Bridge processing failed: {str(e)}"}
    
    def get_version(self) -> str:
        """Get Komposteur version and status"""
        if not self.is_available():
            return "Komposteur bridge not available"
        jar_name = Path(self.jar_path).name if self.jar_path else "unknown"
        return f"Komposteur {self.version} - CI/CD-enabled ({jar_name})"

# Global bridge instance
_bridge_instance: Optional[KomposteurBridge] = None

def get_bridge() -> KomposteurBridge:
    """Get or create the global Komposteur bridge instance"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = KomposteurBridge()
        _bridge_instance.initialize()
    return _bridge_instance

def shutdown_bridge():
    """Shutdown the global bridge instance"""
    global _bridge_instance
    if _bridge_instance:
        _bridge_instance.shutdown()
        _bridge_instance = None