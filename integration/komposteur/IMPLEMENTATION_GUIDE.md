# Komposteur Implementation Guide - Ready-to-Deploy Instructions

## 🎯 Purpose
Step-by-step guide to complete the Komposteur integration once the Java API is implemented. This guide assumes the Komposteur library has added the required `processKompostFile` method.

## 📋 Pre-requisites Checklist
- [ ] Komposteur JAR updated with public API
- [ ] `processKompostFile(String)` method implemented
- [ ] JAR deployed to Maven repository
- [ ] Java 17+ runtime available

## 🚀 Implementation Steps

### Step 1: Update Bridge to Use Real API
Replace mock implementation with actual Java calls:

```python
# In integration/komposteur/bridge/komposteur_bridge.py
def process_kompost_json(self, kompost_path: str) -> Dict[str, Any]:
    """Process kompost.json using real Komposteur API"""
    if not self.is_available():
        return {"success": False, "error": "Komposteur bridge not initialized"}
    
    try:
        # Call actual Java method via subprocess
        java_cmd = [
            "java", "-cp", self.jar_path,
            "no.lau.komposteur.core.KomposteurCore",
            "processKompostFile", kompost_path
        ]
        
        result = subprocess.run(java_cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            # Parse JSON response from Java
            output = json.loads(result.stdout)
            return {
                "success": True,
                "output_video_path": output["outputVideoPath"],
                "processing_log": output["processingLog"],
                "curated_effects_used": output["curatedEffectsUsed"],
                "ffmpeg_commands_executed": output["ffmpegCommandsExecuted"],
                "total_processing_time": output["totalProcessingTime"]
            }
        else:
            return {
                "success": False,
                "error": f"Java process failed: {result.stderr}"
            }
            
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Processing timeout (5 minutes)"}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON response from Komposteur"}
    except Exception as e:
        return {"success": False, "error": f"Processing failed: {str(e)}"}
```

### Step 2: Add komposteur_process_kompost Tool Back
Re-add the missing tool to mcp_tools.py:

```python
@server.tool()
async def komposteur_process_kompost(kompost_json_path: str) -> Dict[str, Any]:
    """Process kompost.json file using Komposteur's curated FFMPEG workflows"""
    try:
        bridge = get_bridge()
        if not bridge.is_available():
            return {"success": False, "error": "Komposteur bridge not available"}
        
        result = bridge.process_kompost_json(kompost_json_path)
        
        if result["success"]:
            return {
                "success": True,
                "output_video_path": result["output_video_path"],
                "processing_log": result["processing_log"],
                "curated_effects_used": result["curated_effects_used"],
                "ffmpeg_commands_executed": result["ffmpeg_commands_executed"],
                "total_processing_time": result["total_processing_time"],
                "algorithm": "Komposteur curated FFMPEG workflow processor"
            }
        else:
            return result
            
    except Exception as e:
        logger.error(f"Komposteur kompost.json processing failed: {e}")
        return {"success": False, "error": f"Kompost processing failed: {str(e)}"}

# Update tool count and return list
logger.info("Registered 6 Komposteur MCP tools")
return [
    "komposteur_beat_sync",
    "komposteur_extract_segment", 
    "komposteur_validate_media",
    "komposteur_calculate_beat_duration",
    "komposteur_process_kompost",  # Re-add this line
    "komposteur_get_status"
]
```

### Step 3: Integrate with FFMPEG MCP File Manager
Update file ID resolution to use the main server's file manager:

```python
# In mcp_tools.py, replace placeholder paths:
# OLD:
video_path = f"/tmp/music/source/{video_file_id}"  # Placeholder

# NEW:
from src.file_manager import FileManager
file_manager = FileManager()
video_path = file_manager.get_file_path(video_file_id)
```

### Step 4: Register Tools in Main MCP Server
Add to src/server.py:

```python
# Import Komposteur tools
from integration.komposteur.tools.mcp_tools import register_komposteur_tools

# Register all tools
def setup_server():
    # ... existing MCP tools ...
    
    # Add Komposteur integration
    komposteur_tools = register_komposteur_tools(server)
    logger.info(f"Registered {len(komposteur_tools)} Komposteur tools")
    
    return server
```

### Step 5: Test End-to-End Workflow
Run comprehensive test:

```bash
# Test the integration
python3 integration/komposteur/test_kompost_json_goal.py

# Expected output:
# 🎯 Goal Progress: 4/4 components working
# ✅ PASS Java Connection
# ✅ PASS API Analysis  
# ✅ PASS Kompost JSON Processing (REAL DATA)
# ✅ PASS MCP Integration
```

### Step 6: Docker Integration
Update Dockerfile to include Java runtime and Komposteur JAR:

```dockerfile
# Add Java runtime
RUN apt-get update && apt-get install -y openjdk-17-jre-headless

# Copy Komposteur JAR (or download from Maven)
COPY integration/komposteur/lib/komposteur-core-*.jar /app/lib/

# Set Java classpath
ENV KOMPOSTEUR_JAR=/app/lib/komposteur-core-*-jar-with-dependencies.jar
```

### Step 7: Add Production Monitoring
Add logging and metrics:

```python
# In komposteur_bridge.py
import time
import logging

def process_kompost_json(self, kompost_path: str) -> Dict[str, Any]:
    start_time = time.time()
    logger.info(f"Starting Komposteur processing: {kompost_path}")
    
    try:
        result = # ... actual processing ...
        
        processing_time = time.time() - start_time
        logger.info(f"Komposteur processing completed in {processing_time:.2f}s")
        
        return result
    except Exception as e:
        logger.error(f"Komposteur processing failed after {time.time() - start_time:.2f}s: {e}")
        raise
```

## 🧪 Testing Workflow

### Manual Testing
```bash
# 1. Start MCP server
uv run python -m src.server

# 2. Test with MCP Inspector
npx @modelcontextprotocol/inspector uv run python -m src.server

# 3. Call komposteur_process_kompost tool with test JSON
# Expected: Real video output in /tmp/music/temp/
```

### Automated Testing
```bash
# Run full test suite
python run_tests.py

# Run specific Komposteur tests
python integration/komposteur/test_kompost_json_goal.py
python integration/komposteur/test_integration.py
```

## 🔧 Troubleshooting Guide

### Common Issues

#### "Java process failed"
- Check Java version: `java -version` (need 17+)
- Verify JAR path: Check ~/.m2/repository/no/lau/kompost/...
- Test JAR directly: `java -cp path/to/jar no.lau.komposteur.core.KomposteurCore`

#### "Invalid JSON response" 
- Komposteur needs to output valid JSON to stdout
- Check stderr for Java exceptions
- Verify processKompostFile method exists

#### "Processing timeout"
- Default 5-minute timeout may be too short for large videos
- Increase timeout in subprocess.run() call
- Add progress monitoring for long operations

#### "File not found" errors
- Verify file ID resolution works correctly
- Check file permissions and paths
- Ensure temp directories exist and are writable

## 📊 Success Verification

### Integration Complete When:
- [ ] `test_kompost_json_goal.py` shows 4/4 PASS with real processing
- [ ] MCP Inspector shows 6 Komposteur tools available
- [ ] Sample kompost.json produces actual video output
- [ ] File ID security model maintained
- [ ] Error handling works for invalid inputs
- [ ] Performance acceptable for production use

### Performance Benchmarks
- **Small video (10s, 720p)**: < 30 seconds processing
- **Medium video (60s, 1080p)**: < 2 minutes processing  
- **Large video (300s, 4K)**: < 10 minutes processing
- **Memory usage**: < 1GB peak
- **Error rate**: < 1% for valid inputs

## 🎯 Next Steps After Implementation

1. **Performance optimization**: Profile and optimize slow operations
2. **Error handling**: Add comprehensive error recovery
3. **Documentation**: Update user guides with real examples
4. **Community feedback**: Gather user feedback on curated effects
5. **Pattern discovery**: Implement usage analytics and recommendations

## 📚 Reference Documents
- `KOMPOSTEUR_API_REQUIREMENTS.md` - Exact API specification
- `LIBRARY_ASSESSMENT.md` - Consumer perspective analysis  
- `FORWARD_OPERATIONS_PLAN.md` - Long-term roadmap
- `DOCUMENTATION_NEEDS.md` - Additional documentation requirements

This guide provides everything needed to complete the integration once the Komposteur API is available.