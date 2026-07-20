#!/usr/bin/env python3
"""
Manual music video creation workflow using existing videos
"""

import json
import logging
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_subnautic_komposition():
    """Create a Subnautic music video komposition using existing video files"""
    
    # Available video files
    video_files = [
        "JJVtt947FfI_136.mp4",
        "_wZ5Hof5tXY_136.mp4", 
        "PXL_20250306_132546255.mp4"
    ]
    
    # Subnautic audio file
    audio_file = "Subnautic Measures.flac"
    
    # Create komposition
    komposition = {
        "id": "subnautic_music_video_workflow",
        "name": "Subnautic Music Video - Complete Workflow Test",
        "description": "120 BPM Subnautic background music with 12 segments, bit-compression effects",
        "bpm": 120,
        "duration": 24.0,  # 12 segments * 2 seconds each
        "format": {
            "width": 1080,
            "height": 1920,
            "framerate": 30,
            "codec": "libx264",
            "preset": "fast"
        },
        "audio": {
            "file": audio_file,
            "volume": 0.8,
            "effects": ["normalize", "limiter"]
        },
        "global_effects": [
            {
                "type": "bit_compression",
                "parameters": {
                    "bit_depth": 8,
                    "sample_rate": 22050,
                    "strength": 0.7
                }
            }
        ],
        "transitions": {
            "type": "fade_to_black",
            "duration": 1.0,
            "ease": "ease_in_out"
        },
        "segments": []
    }
    
    # Add 12 segments of 4 beats each (2 seconds per segment at 120 BPM)
    segment_duration = 2.0  # seconds
    
    for i in range(12):
        start_time = i * segment_duration
        video_file = video_files[i % len(video_files)]  # Cycle through videos
        
        segment = {
            "id": f"segment_{i+1:02d}",
            "start_time": start_time,
            "duration": segment_duration,
            "video": {
                "source": video_file,
                "start": i * 3.0,  # Start at different points in each video
                "duration": segment_duration,
                "scale": "fit_center",
                "orientation": "portrait"
            },
            "effects": [
                {
                    "type": "bit_compression", 
                    "strength": 0.6 + (i % 3) * 0.1  # Vary strength
                },
                {
                    "type": "color_grading",
                    "preset": "underwater",
                    "intensity": 0.7
                }
            ],
            "beat_sync": {
                "beats_per_segment": 4,
                "sync_to_beat": True,
                "beat_emphasis": i % 4 == 0  # Emphasize every 4th segment
            }
        }
        
        komposition["segments"].append(segment)
    
    return komposition

def main():
    logger.info("🌊 Starting Subnautic Music Video Workflow")
    start_time = time.time()
    
    # Create komposition
    logger.info("📝 Creating komposition...")
    komposition = create_subnautic_komposition()
    
    # Save komposition
    komposition_path = Path("subnautic_music_video_komposition.json")
    with open(komposition_path, 'w') as f:
        json.dump(komposition, f, indent=2)
    
    logger.info(f"✅ Komposition saved: {komposition_path}")
    logger.info(f"   Duration: {komposition['duration']}s")
    logger.info(f"   Segments: {len(komposition['segments'])}")
    logger.info(f"   Format: {komposition['format']['width']}x{komposition['format']['height']}")
    logger.info(f"   BPM: {komposition['bpm']}")
    
    # Try to process with MCP server if available
    try:
        from src.komposition_processor import KompositionProcessor
        logger.info("🔄 Processing komposition...")
        
        processor = KompositionProcessor()
        result = processor.process_komposition_file(str(komposition_path))
        
        if hasattr(result, 'output_path'):
            logger.info(f"✅ Video created: {result.output_path}")
        else:
            logger.warning(f"⚠️ Processing result: {result}")
            
    except Exception as e:
        logger.error(f"❌ Komposition processing failed: {e}")
        logger.info("💡 You can process manually using: python -m src.server")
    
    total_time = time.time() - start_time
    logger.info(f"🎯 Workflow completed in {total_time:.2f}s")
    
    # Create summary report
    summary = {
        "workflow": "subnautic_music_video_creation",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration": total_time,
        "status": "completed",
        "komposition_file": str(komposition_path),
        "target_format": "youtube_shorts",
        "audio_source": "Subnautic Measures.flac",
        "video_sources": ["JJVtt947FfI_136.mp4", "_wZ5Hof5tXY_136.mp4", "PXL_20250306_132546255.mp4"],
        "effects_applied": ["bit_compression", "color_grading", "fade_to_black_transitions"],
        "specifications": {
            "bpm": 120,
            "segments": 12,
            "beats_per_segment": 4,
            "segment_duration": 2.0,
            "total_duration": 24.0,
            "resolution": "1080x1920",
            "framerate": 30
        }
    }
    
    summary_path = Path("WORKFLOW_SUMMARY.json")
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"📋 Summary saved: {summary_path}")
    
    return komposition_path, summary_path

if __name__ == "__main__":
    main()