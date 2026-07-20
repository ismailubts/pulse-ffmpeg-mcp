#!/usr/bin/env python3
"""
Transition Effects Verification Script
Validates transition outputs and generates examples with visual comparison
"""

import asyncio
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from transition_processor import TransitionProcessor
    from file_manager import FileManager
    from ffmpeg_wrapper import FFMPEGWrapper
    from config import SecurityConfig
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

class TransitionVerifier:
    """Verifies transition effects with visual and technical validation"""
    
    def __init__(self):
        self.file_manager = FileManager()
        self.ffmpeg = FFMPEGWrapper(SecurityConfig.FFMPEG_PATH)
        self.transition_processor = TransitionProcessor(self.file_manager, self.ffmpeg)
        
        # Create output directories
        self.output_dir = Path("/tmp/music/transition-verification")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Source files (check availability)
        self.source_dir = Path("/tmp/music/source")
        self.available_sources = self._check_available_sources()
        
    def _check_available_sources(self) -> List[str]:
        """Check which source files are available for testing"""
        test_files = [
            "JJVtt947FfI_136.mp4",
            "PXL_20250306_132546255.mp4", 
            "_wZ5Hof5tXY_136.mp4"
        ]
        
        available = []
        for filename in test_files:
            filepath = self.source_dir / filename
            if filepath.exists():
                available.append(filename)
                
        return available
    
    def create_transition_komposition(self, transition_type: str, 
                                    duration_beats: float = 2.0,
                                    start_offset_beats: float = -1.0,
                                    additional_params: Dict = None) -> Dict[str, Any]:
        """Create komposition JSON for testing specific transition"""
        
        if len(self.available_sources) < 2:
            raise ValueError(f"Need at least 2 source videos, found: {len(self.available_sources)}")
        
        params = {
            "duration_beats": duration_beats,
            "start_offset_beats": start_offset_beats
        }
        
        if additional_params:
            params.update(additional_params)
        
        return {
            "bpm": 120,
            "effects_schema_version": "1.0",
            "sources": [
                {"id": "video1", "url": f"file://{self.available_sources[0]}"},
                {"id": "video2", "url": f"file://{self.available_sources[1]}"}
            ],
            "segments": [
                {
                    "segment_id": "first_clip",
                    "source_ref": "video1",
                    "start_beat": 0,
                    "end_beat": 16,
                    "source_timing": {"original_start": 0, "original_duration": 8}
                },
                {
                    "segment_id": "second_clip", 
                    "source_ref": "video2",
                    "start_beat": 16,
                    "end_beat": 32,
                    "source_timing": {"original_start": 2, "original_duration": 8}
                }
            ],
            "effects_tree": {
                "effect_id": f"{transition_type}_test",
                "type": transition_type,
                "parameters": params,
                "applies_to": [
                    {"type": "segment", "id": "first_clip"},
                    {"type": "segment", "id": "second_clip"}
                ]
            }
        }
    
    async def verify_transition(self, transition_type: str, params: Dict = None) -> Dict[str, Any]:
        """Verify a specific transition type with given parameters"""
        
        print(f"🧪 Testing {transition_type}...")
        
        try:
            # Create komposition
            komposition = self.create_transition_komposition(
                transition_type, 
                additional_params=params or {}
            )
            
            # Save komposition for reference
            komposition_file = self.output_dir / f"{transition_type}_test.json"
            with open(komposition_file, 'w') as f:
                json.dump(komposition, f, indent=2)
            
            # Process transition
            start_time = time.time()
            result = await self.transition_processor.process_effects_tree(komposition)
            processing_time = time.time() - start_time
            
            if not result.get("success"):
                return {
                    "transition_type": transition_type,
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "processing_time": processing_time
                }
            
            # Get output file info
            output_file_id = result["output_file_id"]
            output_path = self.file_manager.get_file_path(output_file_id)
            
            # Verify file exists and get metadata
            if not output_path.exists():
                return {
                    "transition_type": transition_type,
                    "success": False,
                    "error": "Output file not created",
                    "processing_time": processing_time
                }
            
            file_size = output_path.stat().st_size
            
            # Get video metadata using ffprobe
            metadata = await self._get_video_metadata(output_path)
            
            # Copy to verification output directory with descriptive name
            verification_output = self.output_dir / f"{transition_type}_verified.mp4"
            output_path.rename(verification_output)
            
            return {
                "transition_type": transition_type,
                "success": True,
                "output_file": str(verification_output),
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / (1024*1024), 2),
                "processing_time_seconds": round(processing_time, 2),
                "video_metadata": metadata,
                "komposition_file": str(komposition_file),
                "parameters_used": params or {}
            }
            
        except Exception as e:
            return {
                "transition_type": transition_type,
                "success": False,
                "error": str(e),
                "processing_time": processing_time if 'processing_time' in locals() else 0
            }
    
    async def _get_video_metadata(self, video_path: Path) -> Dict[str, Any]:
        """Get video metadata using ffprobe"""
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json", 
                "-show_format", "-show_streams", str(video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                metadata = json.loads(result.stdout)
                
                # Extract key info
                video_stream = next((s for s in metadata["streams"] if s["codec_type"] == "video"), None)
                audio_stream = next((s for s in metadata["streams"] if s["codec_type"] == "audio"), None)
                
                return {
                    "duration": float(metadata["format"]["duration"]),
                    "video": {
                        "width": video_stream["width"] if video_stream else None,
                        "height": video_stream["height"] if video_stream else None,
                        "codec": video_stream["codec_name"] if video_stream else None,
                        "fps": eval(video_stream["r_frame_rate"]) if video_stream else None
                    } if video_stream else None,
                    "audio": {
                        "codec": audio_stream["codec_name"] if audio_stream else None,
                        "sample_rate": audio_stream["sample_rate"] if audio_stream else None
                    } if audio_stream else None
                }
            else:
                return {"error": "ffprobe failed", "stderr": result.stderr}
                
        except Exception as e:
            return {"error": str(e)}
    
    async def run_full_verification(self) -> Dict[str, Any]:
        """Run comprehensive verification of all transition types"""
        
        print("🎬 Starting Transition Effects Verification")
        print("=" * 50)
        print(f"Available source files: {len(self.available_sources)}")
        for i, source in enumerate(self.available_sources):
            print(f"  {i+1}. {source}")
        print()
        
        if len(self.available_sources) < 2:
            print("❌ Need at least 2 source videos for transition testing")
            return {"error": "Insufficient source files"}
        
        # Test configurations
        test_configs = [
            {
                "transition_type": "crossfade_transition",
                "params": {"duration_beats": 2.0, "start_offset_beats": -1.0},
                "description": "Classic crossfade with 2-beat duration"
            },
            {
                "transition_type": "gradient_wipe",
                "params": {"duration_beats": 1.5, "start_offset_beats": -0.5},
                "description": "Quick gradient wipe transition"
            },
            {
                "transition_type": "opacity_transition", 
                "params": {"opacity": 0.7},
                "description": "Semi-transparent overlay"
            },
            {
                "transition_type": "crossfade_transition",
                "params": {"duration_beats": 4.0, "start_offset_beats": -2.0},
                "description": "Long crossfade with extended overlap"
            }
        ]
        
        results = []
        
        for config in test_configs:
            print(f"Testing: {config['description']}")
            result = await self.verify_transition(
                config["transition_type"],
                config["params"]
            )
            results.append(result)
            
            if result["success"]:
                print(f"  ✅ Success - {result['file_size_mb']}MB, {result['processing_time_seconds']}s")
                if result.get("video_metadata", {}).get("duration"):
                    duration = result["video_metadata"]["duration"]
                    print(f"     Duration: {duration:.1f}s")
            else:
                print(f"  ❌ Failed - {result['error']}")
            print()
        
        # Generate summary report
        successful_tests = [r for r in results if r["success"]]
        failed_tests = [r for r in results if not r["success"]]
        
        summary = {
            "verification_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": len(results),
            "successful_tests": len(successful_tests),
            "failed_tests": len(failed_tests),
            "source_files_used": self.available_sources,
            "output_directory": str(self.output_dir),
            "results": results
        }
        
        # Save summary report
        report_file = self.output_dir / "verification_report.json"
        with open(report_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print("📊 VERIFICATION SUMMARY")
        print("=" * 30)
        print(f"✅ Successful: {len(successful_tests)}")
        print(f"❌ Failed: {len(failed_tests)}")
        print(f"📁 Output directory: {self.output_dir}")
        print(f"📄 Full report: {report_file}")
        
        if successful_tests:
            print("\n🎬 Generated Videos:")
            for result in successful_tests:
                if result.get("output_file"):
                    print(f"  • {Path(result['output_file']).name} - {result['file_size_mb']}MB")
        
        return summary

async def main():
    """Main verification runner"""
    verifier = TransitionVerifier()
    
    try:
        summary = await verifier.run_full_verification()
        
        if summary.get("successful_tests", 0) > 0:
            print(f"\n🚀 Verification complete! Check {verifier.output_dir} for generated videos.")
            return 0
        else:
            print("\n❌ All tests failed!")
            return 1
            
    except Exception as e:
        print(f"\n💥 Verification failed with error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)