# Build Detective Confidence Validation Patterns

## Automatic BD Quality Checks for Sonnet

### **Red Flag Detection System**

#### **Confidence Score Analysis** 🚨
```python
# Confidence patterns that trigger Sonnet review
CONFIDENCE_RED_FLAGS = {
    "suspiciously_perfect": 10,      # Too confident - verify accuracy
    "uncertain_analysis": lambda x: x < 7,  # Too uncertain - manual needed
    "overconfident_complex": lambda x, complexity: x > 8 and complexity == "high"
}

def check_confidence_validity(bd_result, context):
    confidence = bd_result["confidence"]
    
    # Perfect confidence is suspicious
    if confidence == 10:
        return ValidationFlag(
            level="WARNING",
            message="BD shows perfect confidence - verify against context",
            action="VERIFY_ACCURACY"
        )
    
    # Low confidence needs human
    if confidence < 7:
        return ValidationFlag(
            level="ESCALATE", 
            message="BD uncertainty requires manual analysis",
            action="MANUAL_REVIEW"
        )
    
    # High confidence on complex scenarios  
    complexity_indicators = count_complexity_markers(context)
    if confidence > 8 and complexity_indicators > 3:
        return ValidationFlag(
            level="WARNING",
            message="High confidence on complex scenario - double-check",
            action="DEEP_REVIEW"
        )
```

#### **Technology Stack Misalignment** ⚠️
```python
def validate_tech_stack_alignment(bd_result, project_context):
    """Check if BD's analysis matches project technology"""
    
    mismatches = []
    
    # Java-specific errors in non-Java projects
    if bd_result["error_type"] == "java_version":
        if not project_context.has_files([".java", "pom.xml", "build.gradle"]):
            mismatches.append("Java error claimed in non-Java project")
    
    # Maven errors without Maven files
    if "maven" in bd_result["primary_error"].lower():
        if not project_context.has_files(["pom.xml"]):
            mismatches.append("Maven error claimed in non-Maven project")
    
    # Docker errors without Docker files
    if "docker" in bd_result["primary_error"].lower():
        if not project_context.has_files(["Dockerfile", ".dockerignore"]):
            mismatches.append("Docker error claimed in non-Docker project")
    
    return mismatches
```

#### **Solution Feasibility Check** 🔍
```python
def validate_solution_feasibility(bd_result, project_context):
    """Check if BD's suggested solution makes sense"""
    
    solution = bd_result["suggested_action"].lower()
    issues = []
    
    # Generic solutions are red flags
    generic_patterns = [
        "check configuration",
        "verify setup", 
        "review settings",
        "ensure proper"
    ]
    
    if any(pattern in solution for pattern in generic_patterns):
        issues.append("Generic solution suggests BD didn't find specific pattern")
    
    # Version conflict suggestions
    if "update" in solution and "version" in solution:
        # Check if version constraints exist
        if project_context.has_version_constraints():
            issues.append("Version update suggested but constraints may prevent it")
    
    # File modification suggestions
    if "add" in solution or "create" in solution:
        if project_context.is_readonly_context():
            issues.append("File modification suggested in read-only context")
    
    return issues
```

#### **Build Phase Logic Validation** 🧩
```python
def validate_build_phase_logic(bd_result, raw_log):
    """Check if BD correctly identified build phase"""
    
    claimed_phase = bd_result["build_step"]
    issues = []
    
    # Test phase claimed but build never succeeded
    if claimed_phase == "test":
        if "BUILD FAILURE" in raw_log or "compilation failed" in raw_log:
            issues.append("Test failure claimed but build failed at compilation")
    
    # Package phase claimed but compilation errors present
    if claimed_phase == "package":
        if "cannot find symbol" in raw_log or "package does not exist" in raw_log:
            issues.append("Package failure claimed but compilation errors present")
    
    # Deploy phase claimed but earlier phases failed
    if claimed_phase == "deploy":
        if "Tests run:" in raw_log and "Failures:" in raw_log:
            issues.append("Deploy failure claimed but tests are failing")
    
    return issues
```

### **Context Contradiction Detection** 🚫

#### **Multi-Error Scenarios** 
```python
def detect_complexity_underestimation(bd_result, raw_log):
    """Check if BD oversimplified complex scenarios"""
    
    # Count different error types in log
    error_indicators = [
        "compilation failed",
        "Tests run:",
        "Could not resolve dependencies",
        "Docker build failed", 
        "Plugin execution failed",
        "Connection refused",
        "Permission denied"
    ]
    
    error_count = sum(1 for indicator in error_indicators if indicator in raw_log)
    
    # BD reports simple single error but log shows multiple issues
    if error_count > 2 and bd_result["confidence"] > 8:
        return ValidationFlag(
            level="WARNING",
            message=f"BD reports simple error but log shows {error_count} different issues",
            action="COMPLEXITY_REVIEW"
        )
    
    return None
```

#### **Historical Context Checks**
```python
def validate_against_project_history(bd_result, project_context):
    """Check BD analysis against known project patterns"""
    
    issues = []
    
    # BD suggests changes to intentionally removed dependencies
    if "add dependency" in bd_result["suggested_action"]:
        recently_removed = project_context.get_recently_removed_dependencies()
        if recently_removed:
            issues.append("Dependency addition suggested but similar deps recently removed")
    
    # BD suggests configuration that was just changed
    if "update configuration" in bd_result["suggested_action"]:
        recent_config_changes = project_context.get_recent_config_changes()
        if recent_config_changes:
            issues.append("Config change suggested but config recently modified")
    
    # Repeated failure pattern
    failure_history = project_context.get_failure_history(days=7)
    similar_failures = count_similar_failures(bd_result["primary_error"], failure_history)
    
    if similar_failures > 3:
        issues.append(f"Same error pattern failed {similar_failures} times - systemic issue")
    
    return issues
```

### **Pattern Quality Scoring** 📊

#### **Pattern Reliability Matrix**
```python
PATTERN_RELIABILITY = {
    # High confidence patterns - rarely wrong
    "docker_missing_file": {
        "accuracy": 0.94,
        "escalation_threshold": 0.95,  # Only escalate if >95% confident
        "complexity_tolerance": "low"
    },
    
    # Medium confidence patterns - occasional misses
    "java_version_mismatch": {
        "accuracy": 0.87,
        "escalation_threshold": 0.80,  # Escalate if >80% confident  
        "complexity_tolerance": "medium"
    },
    
    # Lower confidence patterns - need careful review
    "maven_dependency_conflict": {
        "accuracy": 0.73,
        "escalation_threshold": 0.70,  # Escalate if >70% confident
        "complexity_tolerance": "high"
    }
}

def should_escalate_pattern(pattern_name, bd_confidence, context_complexity):
    """Determine if pattern should be escalated to Sonnet"""
    
    if pattern_name not in PATTERN_RELIABILITY:
        return True  # Unknown pattern - always escalate
    
    pattern = PATTERN_RELIABILITY[pattern_name]
    
    # Pattern historically unreliable
    if pattern["accuracy"] < 0.80:
        return True
        
    # High confidence on pattern that can't handle complexity
    if (bd_confidence > pattern["escalation_threshold"] and 
        context_complexity > pattern["complexity_tolerance"]):
        return True
    
    return False
```

### **Sonnet Integration Patterns** 🤝

#### **Quick Validation Workflow** (30 seconds)
```python
def quick_bd_validation(bd_result, context):
    """Fast validation checks Sonnet performs"""
    
    validation_issues = []
    
    # Confidence sanity check
    confidence_issues = check_confidence_validity(bd_result, context)
    if confidence_issues:
        validation_issues.append(confidence_issues)
    
    # Technology alignment
    tech_mismatches = validate_tech_stack_alignment(bd_result, context)
    if tech_mismatches:
        validation_issues.extend(tech_mismatches)
    
    # Solution feasibility  
    solution_issues = validate_solution_feasibility(bd_result, context)
    if solution_issues:
        validation_issues.extend(solution_issues)
    
    # Build phase logic
    phase_issues = validate_build_phase_logic(bd_result, context.raw_log)
    if phase_issues:
        validation_issues.extend(phase_issues)
    
    return ValidationResult(
        needs_review=len(validation_issues) > 0,
        issues=validation_issues,
        recommendation="ESCALATE" if any("ESCALATE" in str(issue) for issue in validation_issues) else "MONITOR"
    )
```

#### **Deep Review Triggers** (2-3 minutes)
```python
def trigger_deep_review(bd_result, context):
    """Determine if BD analysis needs thorough Sonnet review"""
    
    deep_review_triggers = [
        # Complexity underestimation
        detect_complexity_underestimation(bd_result, context.raw_log),
        
        # Historical context conflicts
        validate_against_project_history(bd_result, context),
        
        # Pattern reliability concerns
        should_escalate_pattern(bd_result.get("pattern_matched"), 
                              bd_result["confidence"], 
                              context.complexity_level)
    ]
    
    return any(trigger for trigger in deep_review_triggers if trigger)
```

### **Implementation in Sonnet Workflow** ⚙️

```python
def process_build_detective_analysis(bd_result, context):
    """Main Sonnet workflow for BD oversight"""
    
    # Step 1: Quick validation (always run)
    validation = quick_bd_validation(bd_result, context)
    
    if validation.recommendation == "ESCALATE":
        return perform_manual_analysis(context)
    
    # Step 2: Deep review if triggered
    if trigger_deep_review(bd_result, context):
        return perform_deep_bd_review(bd_result, context)
    
    # Step 3: Accept with monitoring
    return accept_bd_analysis(bd_result, validation.issues)

def accept_bd_analysis(bd_result, issues):
    """Accept BD analysis with noted concerns"""
    return {
        "analysis": bd_result,
        "validation": "ACCEPTED_WITH_MONITORING",
        "concerns": issues,
        "follow_up": "Monitor user feedback for accuracy"
    }

def perform_deep_bd_review(bd_result, context):
    """Sonnet performs thorough review of BD analysis"""
    return {
        "analysis": augment_bd_analysis(bd_result, context),
        "validation": "REVIEWED_AND_ENHANCED", 
        "concerns": [],
        "follow_up": "BD analysis enhanced with additional context"
    }
```

This validation system ensures **Sonnet catches BD mistakes** before they mislead users, while **preserving BD's speed advantage** for straightforward cases that BD handles well.