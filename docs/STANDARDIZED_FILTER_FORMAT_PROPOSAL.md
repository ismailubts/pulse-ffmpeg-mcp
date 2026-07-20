# Standardized Filter Format Proposal for Komposteur

## 🎯 **OBJECTIVE**

Define a standardized JSON format for video processing requests that Komposteur can consume directly, eliminating natural language processing overhead and creating a clean production interface.

## 📋 **CURRENT SITUATION ANALYSIS**

### **What Komposteur Has Built**
- ✅ Natural language processing capabilities
- ✅ Style presets (cinematic, vintage, modern, etc.)
- ✅ Performance tiers (fast/balanced/quality)
- ✅ MCP integration working

### **Production Reality**
- **Development**: Natural language exploration useful for testing
- **Production**: Standardized format files more reliable and performant
- **Integration**: JSON format allows programmatic generation from various sources

## 🏗️ **PROPOSED STANDARDIZED FORMAT**

### **Base Structure Extension**
Extend existing kompost.json with standardized filter specifications:

```json
{
  "metadata": {
    "title": "Video Project",
    "bpm": 120,
    "totalBeats": 64,
    "style": {
      "preset": "cinematic",
      "intensity": "normal",
      "performance_tier": "balanced"
    }
  },
  "segments": [
    {
      "id": "segment_1",
      "sourceRef": "video.mp4",
      "startBeat": 0,
      "endBeat": 16,
      "operation": "trim",
      "params": {"start": 0, "duration": 8},
      "filters": {
        "style_preset": "cinematic_dark",
        "custom_filters": [
          {
            "type": "brightness_contrast",
            "brightness": 0.05,
            "contrast": 1.3
          },
          {
            "type": "blur",
            "radius": 0.5
          }
        ],
        "performance_hint": "balanced"
      }
    }
  ],
  "global_processing": {
    "style_consistency": true,
    "fade_transitions": {
      "fade_in": 1.0,
      "fade_out": 2.0
    },
    "color_grading": {
      "preset": "cinematic",
      "custom_lut": null
    }
  }
}
```

## 🎨 **STYLE PRESET STANDARDIZATION**

### **Style Categories**
```json
{
  "visual_styles": {
    "cinematic": {
      "brightness": 0.05,
      "contrast": 1.3,
      "saturation": 0.9,
      "description": "Film-like dark contrast"
    },
    "vintage": {
      "brightness": 0.1,
      "contrast": 1.1,
      "saturation": 0.7,
      "description": "Retro desaturated look"
    },
    "modern": {
      "brightness": 0.1,
      "contrast": 1.2,
      "saturation": 1.2,
      "description": "Clean contemporary style"
    },
    "documentary": {
      "brightness": 0.08,
      "contrast": 1.1,
      "saturation": 1.0,
      "description": "Natural realistic look"
    }
  }
}
```

### **Performance Tiers**
```json
{
  "performance_tiers": {
    "fast": {
      "max_filters_per_segment": 1,
      "allowed_filters": ["brightness_contrast", "blur"],
      "processing_time_estimate": "< 10s"
    },
    "balanced": {
      "max_filters_per_segment": 2,
      "allowed_filters": ["brightness_contrast", "blur", "saturation"],
      "processing_time_estimate": "10-30s"
    },
    "quality": {
      "max_filters_per_segment": 4,
      "allowed_filters": ["all"],
      "processing_time_estimate": "30s+"
    }
  }
}
```

## 🔧 **KOMPOSTEUR IMPLEMENTATION REQUEST**

### **What Komposteur Should Build**

#### **1. Standardized Format Parser**
```java
public class StandardizedFilterProcessor {
    public KompostResult processStandardizedRequest(JsonObject request) {
        // Parse standardized JSON format
        // Apply style presets
        // Generate MCP-compatible output
        // Return processed video
    }
}
```

#### **2. Style Preset Library** 
```java
public class VideoStyleLibrary {
    public FilterChain getStylePreset(String styleName, String intensity) {
        // Return predefined filter chains for each style
        // Handle intensity scaling (subtle/normal/strong)
        // Ensure MCP compatibility
    }
}
```

#### **3. Format Validation**
```java
public class FormatValidator {
    public ValidationResult validateRequest(JsonObject request) {
        // Validate required fields
        // Check parameter ranges
        // Verify filter compatibility
        // Return validation status
    }
}
```

## 📊 **PRODUCTION WORKFLOW**

### **Intended Usage Pattern**
```
1. External System → Generates standardized JSON
2. Komposteur → Processes JSON (no NL parsing needed)
3. MCP → Applies filters and creates video
4. Output → Professional video file
```

### **Example Integrations**
- **Web UI**: Form inputs → Standardized JSON → Komposteur
- **API**: HTTP requests → JSON validation → Komposteur processing
- **Batch Processing**: JSON files → Automated video generation

## 🎯 **SPECIFIC REQUESTS FOR KOMPOSTEUR**

### **High Priority**
1. **Standardized JSON Parser**: Accept format above without NL processing
2. **Style Preset Integration**: Use existing presets with new JSON structure
3. **MCP Output Format**: Generate JSON that MCP processor expects
4. **Error Handling**: Graceful handling of invalid format/parameters

### **Medium Priority**
1. **Performance Optimization**: Respect performance tier hints
2. **Validation Layer**: Input validation before processing
3. **Backwards Compatibility**: Support existing kompost.json format

### **Low Priority**
1. **Format Documentation**: Auto-generate format specs
2. **Migration Tools**: Convert existing files to new format

## 📈 **BENEFITS OF STANDARDIZED FORMAT**

### **For Production**
- **Predictable**: No NL parsing ambiguity
- **Fast**: Direct JSON processing
- **Reliable**: Validated parameters
- **Scalable**: Programmatic generation

### **For Development**
- **Testable**: Standard test cases
- **Debuggable**: Clear parameter visibility
- **Maintainable**: Version-controlled format specs
- **Extensible**: Easy to add new filter types

## 🤝 **COLLABORATION APPROACH**

### **MCP Side Commitments**
- ✅ Support current filter JSON structure
- ✅ Maintain backwards compatibility
- ✅ Provide format validation feedback
- ✅ Performance optimization for common patterns

### **Komposteur Side Requests**
- 🎯 Implement standardized JSON parser
- 🎯 Integrate with existing style presets
- 🎯 Maintain current NL capabilities for development
- 🎯 Generate MCP-compatible output format

## 📋 **SUCCESS CRITERIA**

**When implementation complete:**
1. Standardized JSON files processed without NL parsing
2. Style presets applied consistently
3. MCP integration maintains current quality
4. Performance tiers respected
5. Error handling graceful and informative

**This approach preserves Komposteur's existing capabilities while adding production-ready standardized format support.**