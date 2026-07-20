#!/usr/bin/env python3
"""
Subprocess isolation for OpenCV operations to prevent hanging the main MCP server.
This script performs heavy video analysis operations in isolation with timeout protection.
"""
import sys
import json
import logging
import signal
from pathlib import Path
from typing import Dict, Any, List
import tempfile
import os

# Configure logging for subprocess
logging.basicConfig(level=logging.INFO, format='%(asctime)s - OPENCV_SUBPROCESS - %(message)s')
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    global shutdown_requested
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    shutdown_requested = True
    sys.exit(1)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def detect_scenes_subprocess(video_path: str) -> Dict[str, Any]:
    """Perform scene detection in subprocess with progress logging"""
    global shutdown_requested
    
    try:
        logger.info(f"Starting scene detection for: {Path(video_path).name}")
        
        # Import here to avoid loading OpenCV in main process
        import cv2
        
        # Check for early shutdown
        if shutdown_requested:
            return {"success": False, "error": "Shutdown requested"}
            
        # Try PySceneDetect first (more robust)
        try:
            from scenedetect import detect, ContentDetector
            logger.info("Using PySceneDetect for scene detection")
            
            scene_list = detect(str(video_path), ContentDetector(threshold=30.0))
            
            if shutdown_requested:
                return {"success": False, "error": "Shutdown requested"}
                
            scenes = []
            for i, scene in enumerate(scene_list):
                if shutdown_requested:
                    break
                    
                start_time = scene[0].get_seconds()
                end_time = scene[1].get_seconds()
                
                scenes.append({
                    "scene_id": i + 1,
                    "start": start_time,
                    "end": end_time,
                    "duration": end_time - start_time
                })
                
                # Progress logging every 5 scenes
                if i % 5 == 0:
                    logger.info(f"Processed {i + 1} scenes...")
                    
            logger.info(f"Scene detection completed: {len(scenes)} scenes found")
            return {"success": True, "scenes": scenes}
            
        except ImportError:
            logger.info("PySceneDetect not available, using OpenCV fallback")
            
            # OpenCV-based fallback
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return {"success": False, "error": f"Could not open video: {video_path}"}
                
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            logger.info(f"Video info: {total_frames} frames, {fps:.2f} FPS, {duration:.1f}s duration")
            
            # For now, return single scene (basic fallback)
            # TODO: Implement proper OpenCV scene detection if needed
            scenes = [{
                "scene_id": 1,
                "start": 0.0,
                "end": duration,
                "duration": duration
            }]
            
            cap.release()
            logger.info("OpenCV fallback completed")
            return {"success": True, "scenes": scenes}
            
    except Exception as e:
        logger.error(f"Scene detection failed: {e}")
        return {"success": False, "error": str(e)}

def analyze_scene_objects_subprocess(video_path: str, scenes: List[Dict]) -> Dict[str, Any]:
    """Analyze objects in scenes using OpenCV in subprocess"""
    global shutdown_requested
    
    try:
        logger.info(f"Starting object analysis for {len(scenes)} scenes")
        
        import cv2
        
        # Initialize object detectors
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        if shutdown_requested:
            return {"success": False, "error": "Shutdown requested"}
            
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return {"success": False, "error": f"Could not open video: {video_path}"}
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        enhanced_scenes = []
        
        for i, scene in enumerate(scenes):
            if shutdown_requested:
                break
                
            logger.info(f"Analyzing scene {i + 1}/{len(scenes)}")
            
            # Sample frame from middle of scene
            mid_time = (scene["start"] + scene["end"]) / 2
            frame_number = int(mid_time * fps)
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            
            if not ret:
                enhanced_scenes.append({**scene, "objects": [], "characteristics": []})
                continue
                
            # Detect faces
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            objects = []
            characteristics = []
            
            if len(faces) > 0:
                objects.append(f"faces ({len(faces)})")
                characteristics.append("people")
                
            # Basic image characteristics
            brightness = cv2.mean(gray)[0]
            if brightness > 127:
                characteristics.append("bright")
            else:
                characteristics.append("dark")
                
            enhanced_scenes.append({
                **scene,
                "objects": objects,
                "characteristics": characteristics
            })
            
        cap.release()
        logger.info(f"Object analysis completed for {len(enhanced_scenes)} scenes")
        return {"success": True, "scenes": enhanced_scenes}
        
    except Exception as e:
        logger.error(f"Object analysis failed: {e}")
        return {"success": False, "error": str(e)}

def main():
    """Main subprocess entry point"""
    if len(sys.argv) != 3:
        print(json.dumps({"success": False, "error": "Usage: opencv_subprocess.py <operation> <video_path>"}))
        sys.exit(1)
        
    operation = sys.argv[1]
    video_path = sys.argv[2]
    
    logger.info(f"Starting OpenCV subprocess: {operation} on {Path(video_path).name}")
    
    if operation == "detect_scenes":
        result = detect_scenes_subprocess(video_path)
    elif operation == "analyze_objects":
        # For analyze_objects, we need scenes data from stdin
        scenes_data = json.loads(sys.stdin.read())
        result = analyze_scene_objects_subprocess(video_path, scenes_data.get("scenes", []))
    else:
        result = {"success": False, "error": f"Unknown operation: {operation}"}
    
    # Output result as JSON
    print(json.dumps(result))

if __name__ == "__main__":
    main()