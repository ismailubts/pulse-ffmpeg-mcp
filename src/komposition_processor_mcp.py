"""
Komposition Processor - Bridge between beat-based komposition format and MCP video processing
"""
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class BeatTiming:
    """Convert between beats and seconds"""
    bpm: int
    
    def beats_to_seconds(self, beats: float) -> float:
        """Convert beats to seconds: beats / (BPM / 60)"""
        return beats / (self.bpm / 60.0)
    
    def seconds_to_beats(self, seconds: float) -> float:
        """Convert seconds to beats: seconds * (BPM / 60)"""
        return seconds * (self.bpm / 60.0)

class KompositionProcessor:
    """Process komposition JSON files into MCP video operations"""
    
    def __init__(self, file_manager, ffmpeg_wrapper):
        self.file_manager = file_manager
        self.ffmpeg_wrapper = ffmpeg_wrapper
        
    async def load_komposition(self, komposition_path: str) -> Dict[str, Any]:
        """Load komposition JSON file"""
        with open(komposition_path, 'r') as f:
            return json.load(f)
    
    async def process_komposition(self, komposition_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing function: convert komposition to video"""
        
        # Initialize beat timing (handle both old and new format)
        bpm = komposition_data.get("bpm") or komposition_data.get("metadata", {}).get("bpm", 120)
        timing = BeatTiming(bpm)
        
        # Extract total beats from komposition data (handle different formats)
        total_beats = (komposition_data.get("total_beats") or 
                      komposition_data.get("beatpattern", {}).get("tobeat") or 
                      128)  # Default fallback
        
        # Step 1: Extract and process all segments according to beat timing
        segment_clips = []
        sources_list = komposition_data.get("sources", [])
        for segment in komposition_data["segments"]:
            clip_id = await self.process_segment(segment, timing, sources_list)
            segment_clips.append({
                "clip_id": clip_id,
                "segment_info": segment
            })
        
        # Step 2: Concatenate all segments
        final_video_id = await self.concatenate_segments(segment_clips)
        
        # Step 3: Add audio track (handle both old and new format)
        audio_track = komposition_data.get("audio_track")
        global_audio = komposition_data.get("globalAudio")
        
        if audio_track or global_audio:
            # For new format, get background music filename from globalAudio
            if global_audio:
                audio_filename = global_audio.get("backgroundMusic")
            else:
                audio_filename = audio_track
            
            if audio_filename:
                # Try to find audio file by name in source files
                audio_file_id = await self.resolve_audio_track_to_file_id(audio_filename)
                if audio_file_id:
                    final_with_audio = await self.add_audio_track(final_video_id, audio_file_id, timing, global_audio)
                    
                    # Apply global filters if specified
                    final_result = await self.apply_global_filters(final_with_audio, komposition_data)
                    
                    # Get the actual output file path for return
                    output_path = self.file_manager.resolve_id(final_result)
                    
                    return {
                        "success": True,
                        "output_file": str(output_path) if output_path else None,
                        "output_file_id": final_result,
                        "composition_info": {
                            "total_duration_beats": total_beats,
                            "total_duration_seconds": timing.beats_to_seconds(total_beats),
                            "bpm": bpm,
                            "segments_processed": len(segment_clips)
                        }
                    }
        
        # Apply global filters if specified
        final_result = await self.apply_global_filters(final_video_id, komposition_data)
        
        # Get the actual output file path for return
        output_path = self.file_manager.resolve_id(final_result)
        
        return {
            "success": True,
            "output_file": str(output_path) if output_path else None,
            "output_file_id": final_result,
            "composition_info": {
                "total_duration_beats": total_beats,
                "total_duration_seconds": timing.beats_to_seconds(total_beats),
                "bpm": bpm,
                "segments_processed": len(segment_clips)
            }
        }
    
    async def process_segment(self, segment: Dict[str, Any], timing: BeatTiming, sources: List[Dict[str, Any]]) -> str:
        """Process individual segment: extract, stretch to beat duration, handle media type"""
        
        # Calculate target duration in seconds (new format uses start_beat/end_beat)
        start_beat = segment.get("startBeat", segment.get("start_beat", 0))
        end_beat = segment.get("endBeat", segment.get("end_beat", 16))
        target_duration_seconds = timing.beats_to_seconds(end_beat - start_beat)
        
        # Find source file name for this segment (new format uses source_ref)
        source_ref = segment.get("sourceRef", segment.get("source_ref", segment.get("segment_id")))
        
        # For new format, sourceRef contains the filename directly
        source_filename = source_ref
        
        if not source_filename:
            raise ValueError(f"No source found for segment: {source_ref}")
        
        # Get file ID for source by finding it in the file registry
        source_file_id = await self.resolve_filename_to_file_id(source_filename)
        
        # For new format, assume video and process accordingly
        # Extract video segment with trim parameters from params object
        params = segment.get("params", {})
        trim_start = params.get("start", 0)
        trim_duration = params.get("duration", target_duration_seconds)
        
        # Extract and stretch video segment
        return await self.extract_and_stretch_video(
            source_file_id, 
            segment, 
            target_duration_seconds,
            trim_start,
            trim_duration
        )
    
    async def extract_and_stretch_video(self, source_file_id: str, segment: Dict[str, Any], target_duration: float, trim_start: float = 0, trim_duration: float = None) -> str:
        """Extract video segment and stretch/compress to target duration"""
        
        # Use provided trim parameters or fallback to original logic
        original_start = trim_start
        original_duration = trim_duration if trim_duration is not None else target_duration
        
        # Step 1: Extract the segment from source video
        try:
            from .video_operations import process_file_internal
        except ImportError:
            from video_operations import process_file_internal
            
        extracted_clip = await process_file_internal(
            input_file_id=source_file_id,
            operation="trim",
            output_extension="mp4",
            params_str=f"start={original_start} duration={original_duration}",
            file_manager=self.file_manager,
            ffmpeg=self.ffmpeg_wrapper
        )
        
        # Step 2: Calculate speed factor to fit target duration
        speed_factor = original_duration / target_duration
        
        # Step 3: Apply speed adjustment if needed
        current_clip = extracted_clip
        if abs(speed_factor - 1.0) > 0.01:  # Only adjust if significant difference
            # Use setpts filter for video speed adjustment
            current_clip = await process_file_internal(
                input_file_id=current_clip,
                operation="convert",
                output_extension="mp4",
                params_str=f"-vf 'setpts={speed_factor}*PTS' -af 'atempo={1/speed_factor}'",
                file_manager=self.file_manager,
                ffmpeg=self.ffmpeg_wrapper
            )
        
        # Step 4: Apply effects and filters if any are specified
        effects = segment.get("effects", [])
        filters = segment.get("filters", [])  # Support both "effects" and "filters" keys
        
        # Combine effects and filters into one list
        all_effects = effects + filters
        
        for effect in all_effects:
            if isinstance(effect, dict) and "type" in effect:
                effect_type = effect["type"]
                effect_params = effect.get("params", {})
                current_clip = await self.apply_effect(current_clip, effect_type, effect_params)
                print(f"Applied effect {effect_type} to segment {segment.get('id', 'unknown')}")
            elif isinstance(effect, dict) and "ffmpeg_filter" in effect:
                # Support custom FFmpeg filter commands
                ffmpeg_filter = effect["ffmpeg_filter"]
                current_clip = await self.apply_custom_filter(current_clip, ffmpeg_filter)
                print(f"Applied custom filter to segment {segment.get('id', 'unknown')}: {ffmpeg_filter}")
        
        if not all_effects:
            print(f"No effects or filters specified for segment {segment.get('id', 'unknown')}")
        
        return current_clip
    
    async def apply_effect(self, file_id: str, effect_type: str, params: Dict[str, Any]) -> str:
        """Apply visual effect to video clip"""
        try:
            from .effect_processor import EffectProcessor
        except (ImportError, ValueError):
            from effect_processor import EffectProcessor
        
        # Initialize effect processor
        effect_processor = EffectProcessor(self.ffmpeg_wrapper, self.file_manager)
        
        # Apply the effect
        result = await effect_processor.apply_effect(file_id, effect_type, params)
        
        if result.get("success"):
            return result["output_file_id"]
        else:
            # If effect fails, log the error but return original file
            print(f"Warning: Effect {effect_type} failed: {result.get('error')}")
            return file_id
    
    async def apply_custom_filter(self, file_id: str, ffmpeg_filter: str) -> str:
        """Apply custom FFmpeg filter to video clip"""
        try:
            from .video_operations import process_file_internal
        except ImportError:
            from video_operations import process_file_internal
        
        try:
            # Apply custom filter using convert operation with the filter parameters
            result = await process_file_internal(
                input_file_id=file_id,
                operation="convert",
                output_extension="mp4",
                params_str=ffmpeg_filter,  # Pass the filter string directly
                file_manager=self.file_manager,
                ffmpeg=self.ffmpeg_wrapper
            )
            return result
        except Exception as e:
            # If custom filter fails, log the error but return original file
            print(f"Warning: Custom filter failed: {e}")
            return file_id
    
    async def create_image_video(self, image_file_id: str, duration: float) -> str:
        """Convert image to video clip of specified duration"""
        try:
            from .video_operations import process_file_internal
        except ImportError:
            from video_operations import process_file_internal
        
        return await process_file_internal(
            input_file_id=image_file_id,
            operation="image_to_video",
            output_extension="mp4", 
            params_str=f"duration={duration}",
            file_manager=self.file_manager,
            ffmpeg=self.ffmpeg_wrapper
        )
    
    async def concatenate_segments(self, segment_clips: List[Dict[str, Any]]) -> str:
        """Concatenate all processed segments into final video"""
        try:
            from .video_operations import process_file_internal, process_file_as_finished
        except ImportError:
            from video_operations import process_file_internal, process_file_as_finished
        
        if len(segment_clips) < 2:
            return segment_clips[0]["clip_id"] if segment_clips else None
        
        # Start with first two clips (temp processing)
        current_result = await process_file_internal(
            input_file_id=segment_clips[0]["clip_id"],
            operation="concatenate_simple",
            output_extension="mp4",
            params_str=f"second_video={segment_clips[1]['clip_id']}",
            file_manager=self.file_manager,
            ffmpeg=self.ffmpeg_wrapper
        )
        
        # Add remaining clips one by one (temp processing)
        for i in range(2, len(segment_clips) - 1): # Iterate up to the second to last
            current_result = await process_file_internal(
                input_file_id=current_result,
                operation="concatenate_simple", 
                output_extension="mp4",
                params_str=f"second_video={segment_clips[i]['clip_id']}",
                file_manager=self.file_manager,
                ffmpeg=self.ffmpeg_wrapper
            )
        
        # Final concatenation goes to finished directory
        # If there are more than 2 segments, current_result holds the concatenation of first N-1 segments
        # The last segment is segment_clips[-1]['clip_id']
        # If there are exactly 2 segments, current_result is already the concatenation of these two.
        # The logic needs to handle the case where len(segment_clips) == 2 separately for the final step.

        if len(segment_clips) > 1: # Ensure there's at least one concatenation to make final
            # If len is 2, current_result is already the combination of the two.
            # If len > 2, current_result is combo of first N-1, and we add the last one.
            input_for_final = current_result
            second_video_for_final = segment_clips[-1]['clip_id']
            
            if len(segment_clips) == 2: # current_result is already the result of concatenating the two.
                                        # We need to re-process them into the finished directory.
                input_for_final = segment_clips[0]['clip_id']
                second_video_for_final = segment_clips[1]['clip_id']


            final_result = await process_file_as_finished(
                input_file_id=input_for_final,
                operation="concatenate_simple",
                output_extension="mp4",
                params_str=f"second_video={second_video_for_final}",
                file_manager=self.file_manager,
                ffmpeg=self.ffmpeg_wrapper,
                title="music_video"
            )
        else: # Only one segment, no concatenation needed, but should be "finished"
             # This case should ideally be handled by the caller, but for robustness:
             # We can't just use process_file_as_finished without an operation.
             # A "copy" or "convert" operation would be needed.
             # For now, assume len(segment_clips) >= 1 and if 1, it's returned by the initial check.
             # If the goal is to ensure the single clip is in "finished", it needs a different path.
             # The current logic implies concatenation, so a single clip means no concat.
             # Let's stick to the original logic: if len < 2, returns the clip_id (which is temp).
             # The caller (process_komposition) then handles audio addition which uses process_file_as_finished.
             # So, this function should primarily return a temp file if intermediate,
             # or the final file if it's the last step of concatenation.
             # The current logic for process_komposition seems to expect the *final concatenated video* (silent)
             # to be returned from here, which then has audio added.
             # The original code's final concatenation step was always to `process_file_as_finished`.
             # Let's simplify: if only one segment, it's not concatenated. If multiple, the final step is _as_finished.

            # Re-evaluating: The loop for i in range(2, len(segment_clips) -1) is for intermediate.
            # The final step should always use process_file_as_finished.
            if len(segment_clips) == 2: # Concatenate first two directly to finished
                 final_result = await process_file_as_finished(
                    input_file_id=segment_clips[0]["clip_id"],
                    operation="concatenate_simple",
                    output_extension="mp4",
                    params_str=f"second_video={segment_clips[1]['clip_id']}",
                    file_manager=self.file_manager,
                    ffmpeg=self.ffmpeg_wrapper,
                    title="music_video"
                )
            elif len(segment_clips) > 2: # More than 2, current_result is temp, concat with last one to finished
                final_result = await process_file_as_finished(
                    input_file_id=current_result, # This is temp from previous concats
                    operation="concatenate_simple",
                    output_extension="mp4",
                    params_str=f"second_video={segment_clips[-1]['clip_id']}",
                    file_manager=self.file_manager,
                    ffmpeg=self.ffmpeg_wrapper,
                    title="music_video"
                )
            else: # len(segment_clips) must be 1 or 0, handled by initial check
                final_result = segment_clips[0]["clip_id"] if segment_clips else None


        return final_result
    
    async def add_audio_track(self, video_file_id: str, audio_file_id: str, timing: BeatTiming, global_audio: Dict[str, Any] = None) -> str:
        """Add audio track to video, trimming audio to video length"""
        try:
            from .video_operations import process_file_as_finished
        except ImportError:
            from video_operations import process_file_as_finished
        
        # Build parameters string with global audio settings if available
        params_parts = [f"audio_file={audio_file_id}"]
        
        if global_audio:
            volume = global_audio.get("musicVolume", 0.8)
            fade_in = global_audio.get("fadeIn", 2.0)
            fade_out = global_audio.get("fadeOut", 3.0)
            params_parts.append(f"volume={volume}")
            params_parts.append(f"fade_in={fade_in}")
            params_parts.append(f"fade_out={fade_out}")
        
        params_str = " ".join(params_parts)
        
        return await process_file_as_finished(
            input_file_id=video_file_id,
            operation="replace_audio",
            output_extension="mp4",
            params_str=params_str,
            file_manager=self.file_manager,
            ffmpeg=self.ffmpeg_wrapper,
            title="music_video_with_audio"
        )
    
    async def smart_match_segment_to_source(self, segment: Dict[str, Any], sources: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Intelligently match segment description to available sources"""
        segment_id = segment["id"].lower()
        
        # Simple keyword matching
        if "dagny" in segment_id or "baybay" in segment_id:
            return self.find_source_by_keyword(sources, ["dagny", "baybay"])
        elif "boat" in segment_id or "image" in segment_id:
            return self.find_source_by_mediatype(sources, "image")
        elif "scene" in segment_id or "video" in segment_id:
            # Return first available video source
            return self.find_source_by_mediatype(sources, "video")
        
        return None
    
    def find_source_by_keyword(self, sources: List[Dict[str, Any]], keywords: List[str]) -> Optional[Dict[str, Any]]:
        """Find source containing any of the keywords"""
        for source in sources:
            source_id = source["id"].lower()
            if any(keyword in source_id for keyword in keywords):
                return source
        return None
    
    def find_source_by_mediatype(self, sources: List[Dict[str, Any]], mediatype: str) -> Optional[Dict[str, Any]]:
        """Find first source of specified media type"""
        for source in sources:
            if source.get("mediatype") == mediatype:
                return source
        return None
    
    async def ensure_compatibility_encoding(self, video_file_id: str) -> str:
        """Ensure video output is compatible with all players (YUV420P, proper encoding)"""
        try:
            # Get input file path
            input_path = self.file_manager.resolve_id(video_file_id)
            if not input_path:
                return video_file_id
                
            # Create temp output path  
            output_file_id, output_path = self.file_manager.create_temp_file("mp4")
            
            # Build YouTube recommended encoding command for YUV420P compatibility
            command = self.ffmpeg_wrapper.build_command(
                "youtube_recommended_encode",
                input_path,
                output_path
            )
            
            # Execute the encoding
            result = await self.ffmpeg_wrapper.execute_command(command, timeout=300)
            
            if result and result.get("success"):
                # Return the new compatible file ID
                return output_file_id
            else:
                # If encoding failed, clean up and return original
                if output_path.exists():
                    output_path.unlink(missing_ok=True)
                self.file_manager.invalidate_file_id(output_file_id)
                return video_file_id
            
        except Exception as e:
            # If compatibility encoding fails, return original
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Compatibility encoding failed, using original: {e}")
            return video_file_id
    
    def find_source_by_id(self, source_id: str, sources: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find source by exact ID match"""
        for source in sources:
            if source["id"] == source_id:
                return source
        return None
    
    def find_audio_source(self, sources: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find audio source for background track"""
        return self.find_source_by_mediatype(sources, "audio")
    
    async def resolve_source_to_file_id(self, source: Dict[str, Any]) -> str:
        """Convert source URL/path to MCP file ID"""
        # Handle file:// URLs
        url = source["url"]
        if url.startswith("file://"):
            filename = url[7:]  # Remove "file://" prefix
            
            # Find matching file in source directory
            try:
                from .config import SecurityConfig
            except ImportError:
                from config import SecurityConfig
            source_dir = SecurityConfig.SOURCE_DIR
            
            for file_path in source_dir.glob("*"):
                if file_path.name == filename and file_path.is_file():
                    # Register the file and return its ID
                    return self.file_manager.register_file(file_path)
            
            raise FileNotFoundError(f"Source file not found: {filename}")
        
        # Handle other URL types (would need downloading)
        raise NotImplementedError(f"URL type not supported yet: {url}")
    
    async def resolve_filename_to_file_id(self, filename: str) -> str:
        """Find file ID for a filename by registering it from source directory"""
        from pathlib import Path
        
        # Look for file in source directory
        source_dir = Path("/tmp/music/source")
        for file_path in source_dir.glob("*"):
            if file_path.name == filename and file_path.is_file():
                # Register the file and return its ID
                return self.file_manager.register_file(file_path)
        
        raise FileNotFoundError(f"File not found in source directory: {filename}")
    
    async def resolve_audio_track_to_file_id(self, audio_filename: str) -> str:
        """Find file ID for audio track filename"""
        return await self.resolve_filename_to_file_id(audio_filename)
    
    async def apply_global_filters(self, video_file_id: str, komposition_data: Dict[str, Any]) -> str:
        """Apply global filters to the final video"""
        # Support both global_filters and effects_tree formats
        global_filters = komposition_data.get("global_filters", [])
        effects_tree = komposition_data.get("effects_tree", [])
        
        # Combine both filter sources
        all_filters = global_filters + effects_tree
        
        if not all_filters:
            # No filters specified, return original video
            return video_file_id
        
        current_video = video_file_id
        
        for filter_spec in global_filters:
            if isinstance(filter_spec, dict):
                if "type" in filter_spec:
                    # Standard effect/filter
                    filter_type = filter_spec["type"]
                    filter_params = filter_spec.get("params", {})
                    current_video = await self.apply_effect(current_video, filter_type, filter_params)
                    print(f"Applied global filter {filter_type} to final video")
                elif "ffmpeg_filter" in filter_spec:
                    # Custom FFmpeg filter
                    ffmpeg_filter = filter_spec["ffmpeg_filter"]
                    current_video = await self.apply_custom_filter(current_video, ffmpeg_filter)
                    print(f"Applied global custom filter to final video: {ffmpeg_filter}")
        
        return current_video
