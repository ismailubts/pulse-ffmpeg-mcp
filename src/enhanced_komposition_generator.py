"""
Enhanced Komposition Generator with Deep Content Analysis Integration
===================================================================

Extends the existing komposition generator to better utilize content analysis:
- Maps scene characteristics to musical structure (intro, verse, refrain, outro)
- Uses visual analysis for intelligent segment selection
- Integrates object detection for content-aware transitions
- Leverages timing analysis for beat-synchronized cuts
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

try:
    from .komposition_generator import KompositionGenerator, CompositionIntent
    from .content_analyzer import VideoContentAnalyzer
    from .file_manager import FileManager
except ImportError:
    from komposition_generator import KompositionGenerator, CompositionIntent
    from content_analyzer import VideoContentAnalyzer
    from file_manager import FileManager


@dataclass
class SceneSelection:
    """Selected scene with musical context"""
    scene_id: int
    source_filename: str
    file_id: str
    start: float
    end: float
    duration: float
    musical_role: str  # intro, verse, refrain, outro
    selection_reasons: List[str]
    visual_characteristics: List[str]
    objects: List[str]
    quality_score: int


class EnhancedKompositionGenerator(KompositionGenerator):
    """Enhanced komposition generator with deep content analysis integration"""
    
    def __init__(self):
        super().__init__()
        self.scene_role_mapping = {
            "intro": {
                "preferred_characteristics": ["normal_lighting", "medium_detail", "establishing_shot"],
                "preferred_objects": ["eyes", "faces"],
                "avoid_characteristics": ["dark", "low_detail", "chaotic"],
                "duration_range": (5.0, 20.0)
            },
            "verse": {
                "preferred_characteristics": ["normal_lighting", "medium_detail", "stable"],
                "preferred_objects": ["faces", "eyes"],
                "avoid_characteristics": ["extreme_close", "motion_blur"],
                "duration_range": (8.0, 30.0)
            },
            "refrain": {
                "preferred_characteristics": ["dynamic", "high_detail", "colorful", "orange_tones"],
                "preferred_objects": ["multiple_eyes", "faces", "movement"],
                "avoid_characteristics": ["static", "monotone"],
                "duration_range": (15.0, 40.0)
            },
            "outro": {
                "preferred_characteristics": ["dark", "fade", "low_detail", "closing"],
                "preferred_objects": [],
                "avoid_characteristics": ["bright", "energetic"],
                "duration_range": (3.0, 15.0)
            }
        }
    
    async def generate_content_aware_komposition(
        self,
        description: str,
        title: str = "Enhanced Content-Aware Composition",
        use_source_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Generate komposition with deep content analysis integration
        
        Args:
            description: Natural language description
            title: Composition title
            use_source_metadata: Whether to use existing source metadata files
            
        Returns:
            Enhanced komposition with content-aware segment selection
        """
        
        # Get available files using parent class method
        available_source_names = self.get_available_sources()
        video_files = [name for name in available_source_names if Path(name).suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']]
        
        # Parse intent using parent class method
        intent = await self._parse_intent(description, title, available_source_names)
        
        if not video_files:
            return {
                "success": False,
                "error": "No video files available for composition"
            }
        
        # Analyze content and load source metadata if available
        content_analysis = await self._get_comprehensive_content_analysis(video_files, use_source_metadata)
        
        # Select scenes based on musical structure and content analysis
        selected_scenes = await self._select_scenes_for_musical_structure(
            content_analysis,
            intent.musical_structure,
            intent.total_beats,
            intent.beats_per_measure
        )
        
        # Generate enhanced komposition
        komposition = await self._create_enhanced_komposition(
            intent,
            selected_scenes,
            content_analysis
        )
        
        # Save komposition
        komposition_file = self._save_komposition(komposition, title)
        
        return {
            "success": True,
            "komposition": komposition,
            "komposition_file": komposition_file,
            "content_analysis_used": len(content_analysis),
            "scenes_selected": len(selected_scenes),
            "selection_details": selected_scenes
        }
    
    async def _get_comprehensive_content_analysis(
        self,
        video_files: List[str],
        use_source_metadata: bool
    ) -> Dict[str, Any]:
        """Get comprehensive content analysis including source metadata"""
        
        analysis = {}
        
        for filename in video_files:
            file_analysis = {
                "file_info": {
                    "name": filename,
                    "size": 0  # We'll get this from file path if needed
                },
                "scenes": [],
                "source_metadata": None,
                "content_insights": None
            }
            
            # Get content analysis - use full path to source file
            source_path = Path("/tmp/music/source") / filename
            if source_path.exists():
                # Generate a file ID for caching consistency
                file_id = self.file_manager.register_file(source_path)
                content_result = await self.content_analyzer.analyze_video_content(source_path, file_id)
                if content_result.get("success"):
                    file_analysis["scenes"] = content_result.get("analysis", {}).get("scenes", [])
                    file_analysis["content_insights"] = content_result.get("analysis", {}).get("summary", {})
                    file_analysis["file_info"]["size"] = source_path.stat().st_size
            
            # Load source metadata if available
            if use_source_metadata:
                metadata_file = Path(f"examples/source-metadata/{filename.split('.')[0]}-metadata.json")
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            file_analysis["source_metadata"] = json.load(f)
                    except Exception as e:
                        print(f"Warning: Could not load source metadata for {filename}: {e}")
            
            analysis[filename] = file_analysis
        
        return analysis
    
    async def _select_scenes_for_musical_structure(
        self,
        content_analysis: Dict[str, Any],
        musical_structure: List[str],
        total_beats: int,
        beats_per_measure: int
    ) -> List[SceneSelection]:
        """Select best scenes for each part of musical structure"""
        
        if not musical_structure:
            musical_structure = ["intro", "verse", "refrain", "outro"]
        
        selected_scenes = []
        beats_per_segment = total_beats // len(musical_structure)
        
        for i, role in enumerate(musical_structure):
            best_scene = await self._find_best_scene_for_role(
                content_analysis,
                role,
                beats_per_segment * i,
                beats_per_segment * (i + 1)
            )
            
            if best_scene:
                selected_scenes.append(best_scene)
        
        return selected_scenes
    
    async def _find_best_scene_for_role(
        self,
        content_analysis: Dict[str, Any],
        role: str,
        start_beat: int,
        end_beat: int
    ) -> Optional[SceneSelection]:
        """Find the best scene for a specific musical role"""
        
        role_criteria = self.scene_role_mapping.get(role, {})
        preferred_chars = role_criteria.get("preferred_characteristics", [])
        preferred_objects = role_criteria.get("preferred_objects", [])
        avoid_chars = role_criteria.get("avoid_characteristics", [])
        duration_range = role_criteria.get("duration_range", (5.0, 30.0))
        
        candidates = []
        
        # Evaluate all available scenes
        for filename, file_analysis in content_analysis.items():
            scenes = file_analysis.get("scenes", [])
            source_metadata = file_analysis.get("source_metadata", {})
            
            for scene in scenes:
                # Check duration suitability
                scene_duration = scene.get("duration", 0)
                if not (duration_range[0] <= scene_duration <= duration_range[1]):
                    continue
                
                # Score the scene for this role
                score = self._score_scene_for_role(
                    scene,
                    preferred_chars,
                    preferred_objects,
                    avoid_chars,
                    source_metadata
                )
                
                if score > 0:  # Only consider scenes with positive scores
                    candidates.append({
                        "scene": scene,
                        "filename": filename,
                        "score": score,
                        "role": role
                    })
        
        # Sort by score and return best candidate
        if candidates:
            best = max(candidates, key=lambda x: x["score"])
            scene = best["scene"]
            
            return SceneSelection(
                scene_id=scene.get("scene_id", 0),
                source_filename=best["filename"],
                file_id="",  # We'll resolve this later if needed
                start=scene.get("start", 0),
                end=scene.get("end", 0),
                duration=scene.get("duration", 0),
                musical_role=role,
                selection_reasons=self._get_selection_reasons(scene, preferred_chars, preferred_objects),
                visual_characteristics=scene.get("characteristics", []),
                objects=scene.get("objects", []),
                quality_score=best["score"]
            )
        
        return None
    
    def _score_scene_for_role(
        self,
        scene: Dict[str, Any],
        preferred_chars: List[str],
        preferred_objects: List[str],
        avoid_chars: List[str],
        source_metadata: Optional[Dict[str, Any]]
    ) -> int:
        """Score a scene's suitability for a musical role"""
        
        score = 0
        scene_chars = scene.get("characteristics", [])
        scene_objects = scene.get("objects", [])
        
        # Positive scoring for preferred characteristics
        for char in preferred_chars:
            if char in scene_chars:
                score += 2
        
        # Positive scoring for preferred objects
        for obj in preferred_objects:
            if any(obj in scene_obj for scene_obj in scene_objects):
                score += 3
        
        # Negative scoring for characteristics to avoid
        for char in avoid_chars:
            if char in scene_chars:
                score -= 3
        
        # Bonus for scenes marked as suitable in source metadata
        if source_metadata:
            usable_segments = source_metadata.get("usableSegments", [])
            scene_start = scene.get("start", 0)
            scene_end = scene.get("end", 0)
            
            for segment in usable_segments:
                seg_start = segment.get("start", 0)
                seg_end = segment.get("end", 0)
                
                # Check if scene overlaps with usable segment
                if (scene_start <= seg_end and scene_end >= seg_start):
                    score += 5  # Significant bonus for metadata-identified segments
        
        return score
    
    def _get_selection_reasons(
        self,
        scene: Dict[str, Any],
        preferred_chars: List[str],
        preferred_objects: List[str]
    ) -> List[str]:
        """Get human-readable reasons for scene selection"""
        
        reasons = []
        scene_chars = scene.get("characteristics", [])
        scene_objects = scene.get("objects", [])
        
        for char in preferred_chars:
            if char in scene_chars:
                reasons.append(f"Has preferred characteristic: {char}")
        
        for obj in preferred_objects:
            if any(obj in scene_obj for scene_obj in scene_objects):
                reasons.append(f"Contains desired object: {obj}")
        
        duration = scene.get("duration", 0)
        if 5 <= duration <= 30:
            reasons.append(f"Good duration: {duration:.1f}s")
        
        return reasons
    
    async def _create_enhanced_komposition(
        self,
        intent: CompositionIntent,
        selected_scenes: List[SceneSelection],
        content_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create enhanced komposition with content-aware segments"""
        
        komposition = {
            "metadata": {
                "title": intent.title,
                "description": intent.description,
                "bpm": intent.bpm,
                "beatsPerMeasure": intent.beats_per_measure,
                "totalBeats": intent.total_beats,
                "estimatedDuration": (intent.total_beats * 60) / intent.bpm,
                "createdAt": datetime.now().isoformat(),
                "generatedFromDescription": True,
                "contentAnalysisUsed": True,
                "enhancedGeneration": True
            },
            "segments": [],
            "effects_tree": [],
            "outputSettings": {
                "resolution": f"{intent.resolution[0]}x{intent.resolution[1]}",
                "aspectRatio": f"{intent.resolution[0]}:{intent.resolution[1]}",
                "fps": 30,
                "videoCodec": "libx264",
                "audioCodec": "aac"
            },
            "contentAnalysisSummary": {
                "filesAnalyzed": len(content_analysis),
                "scenesSelected": len(selected_scenes),
                "selectionCriteria": "content-aware musical structure mapping"
            }
        }
        
        # Create segments from selected scenes
        beats_per_segment = intent.total_beats // len(selected_scenes) if selected_scenes else 16
        
        for i, scene_selection in enumerate(selected_scenes):
            start_beat = i * beats_per_segment
            end_beat = (i + 1) * beats_per_segment
            segment_duration = (beats_per_segment * 60) / intent.bpm
            
            segment = {
                "id": f"content_aware_segment_{i}",
                "sourceRef": scene_selection.source_filename,
                "startBeat": start_beat,
                "endBeat": end_beat,
                "duration": beats_per_segment,
                "operation": "trim",
                "source_timing": {
                    "original_start": scene_selection.start,
                    "original_end": scene_selection.end,
                    "original_duration": scene_selection.duration
                },
                "params": {
                    "start": scene_selection.start,
                    "duration": min(segment_duration, scene_selection.duration)
                },
                "description": f"{scene_selection.musical_role.title()} segment from {scene_selection.source_filename}",
                "musical_role": scene_selection.musical_role,
                "content_analysis": {
                    "scene_id": scene_selection.scene_id,
                    "visual_characteristics": scene_selection.visual_characteristics,
                    "objects": scene_selection.objects,
                    "selection_reasons": scene_selection.selection_reasons,
                    "quality_score": scene_selection.quality_score
                }
            }
            
            komposition["segments"].append(segment)
        
        # Add content-aware effects
        komposition["effects_tree"] = self._generate_content_aware_effects(selected_scenes)
        
        return komposition
    
    def _generate_content_aware_effects(self, selected_scenes: List[SceneSelection]) -> List[Dict[str, Any]]:
        """Generate effects based on content analysis"""
        
        effects = []
        
        # Add crossfade transitions between segments
        effects.append({
            "effect": "crossfade_transition",
            "params": {
                "duration": 0.5,
                "method": "crossfade",
                "beat_aligned": True
            }
        })
        
        # Add color grading based on visual characteristics
        dominant_characteristics = {}
        for scene in selected_scenes:
            for char in scene.visual_characteristics:
                dominant_characteristics[char] = dominant_characteristics.get(char, 0) + 1
        
        if "dark" in dominant_characteristics and dominant_characteristics["dark"] > 1:
            effects.append({
                "effect": "brightness_adjustment",
                "params": {
                    "brightness": 0.2,
                    "contrast": 1.1
                }
            })
        
        if "red_tones" in dominant_characteristics:
            effects.append({
                "effect": "color_enhancement",
                "params": {
                    "enhance_reds": 1.2,
                    "warmth": 0.1
                }
            })
        
        # Add audio normalization
        effects.append({
            "effect": "audio_normalize",
            "params": {
                "target_level": -12
            }
        })
        
        return effects


# Integration function for MCP server
async def generate_enhanced_komposition_from_description(
    description: str,
    title: str = "Enhanced Composition",
    use_source_metadata: bool = True
) -> Dict[str, Any]:
    """
    Generate enhanced komposition with deep content analysis integration
    
    This function provides the MCP server integration point for enhanced
    komposition generation that utilizes content analysis and source metadata.
    """
    
    generator = EnhancedKompositionGenerator()
    return await generator.generate_content_aware_komposition(
        description=description,
        title=title,
        use_source_metadata=use_source_metadata
    )