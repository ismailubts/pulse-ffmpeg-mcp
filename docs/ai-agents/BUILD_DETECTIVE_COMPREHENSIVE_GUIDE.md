# Build Detective: Comprehensive AI Agent Guide

## What is Build Detective?

**Build Detective (BD)** is a specialized Haiku-powered AI subagent designed for **cost-effective CI/build failure analysis**. It operates under **Sonnet oversight** to provide fast, pattern-based diagnosis of common build failures.

### Core Philosophy
```
Haiku = Fast pattern recognition specialist
Sonnet = Senior consultant providing oversight
User = Receives validated, actionable analysis
```

## The Economic Problem BD Solves

### Before Build Detective
- **Cost**: 3000+ tokens per CI analysis using Sonnet
- **Time**: 2-5 minutes for thorough analysis
- **Accuracy**: High, but expensive for routine failures

### With Build Detective
- **Cost**: 400-800 tokens using Haiku (85% reduction)
- **Time**: 10-30 seconds for pattern recognition
- **Accuracy**: 85%+ for common patterns with Sonnet validation
- **Reliability**: Quality assurance prevents misleading analysis

## Architecture: Two-Tier AI System

### Tier 1: Build Detective (Haiku)
**Role**: Pattern-matching specialist
**Strengths**:
- Lightning-fast error pattern recognition
- Structured JSON output format
- Cost-effective bulk analysis
- Technology stack identification

**Limitations**:
- Can miss complex edge cases
- May overconfident on fuzzy matches
- Limited reasoning about context
- Requires validation for reliability

### Tier 2: Sonnet Oversight
**Role**: Quality validator and senior consultant
**Responsibilities**:
- Validate BD analysis for obvious errors
- Escalate complex scenarios BD can't handle
- Augment BD analysis with additional context
- Learn from BD mistakes to improve patterns

## Quality Assurance System

### Automatic Escalation Triggers

#### 1. Confidence Score Red Flags
```python
if bd_confidence < 7:
    → ESCALATE: BD uncertain, manual review needed
    
if bd_confidence == 10:
    → VERIFY: Perfect confidence suspicious for real CI failures
    
if bd_confidence > 8 and context_complexity == "high":
    → REVIEW: High confidence on complex scenarios needs verification
```

#### 2. Technology Stack Misalignment
```python
if bd_says_java_error and no_java_files_in_project:
    → ESCALATE: BD applied wrong pattern library
    
if bd_says_maven_error and no_pom_xml_exists:
    → ESCALATE: BD misunderstood build system
    
if bd_says_docker_error and no_dockerfile_present:
    → ESCALATE: BD focused on wrong technology
```

#### 3. Context Contradiction Detection
```python
if bd_says_test_failure and build_failed_at_compilation:
    → ESCALATE: BD misidentified build phase
    
if bd_says_simple_error and multiple_different_errors_in_log:
    → ESCALATE: BD oversimplified complex scenario
    
if bd_solution_is_generic_("check configuration"):
    → ESCALATE: BD didn't find specific pattern, guessing
```

### Sonnet Validation Workflow

#### Quick Validation (30 seconds)
```markdown
1. Check BD confidence vs error complexity
2. Verify technology stack alignment
3. Scan for obvious contradictions
4. Assess solution specificity

IF red flags detected → Escalate to deep review
ELSE → Accept with monitoring
```

#### Deep Review (2-3 minutes)
```markdown
1. Read full log context
2. Cross-reference project constraints
3. Verify error classification accuracy
4. Test solution feasibility

IF BD fundamentally wrong → Override with Sonnet analysis
IF BD missed complexity → Augment with additional context  
IF BD mostly correct → Endorse with minor corrections
```

## Setup and Installation

### Template-Based Deployment
```bash
# Copy BD template to any project
./scripts/setup-build-detective.sh /path/to/target/project

# What it creates:
target-project/.claude/agents/build-detective.md
```

### Template Customization Variables
```markdown
{{PROJECT_NAME}} → "MyProject"
{{PRIMARY_LANGUAGE}} → "Java" | "Python" | "Go"
{{BUILD_SYSTEM}} → "Maven" | "Gradle" | "npm"
{{KEY_DEPENDENCIES}} → "Spring Boot, JUnit"
{{DEPLOYMENT_TARGET}} → "AWS" | "Docker" | "GitHub Pages"
{{COMMON_ISSUE_X}} → Project-specific frequent problems
{{TYPICAL_SOLUTION_X}} → Project-specific solutions
```

### Integration with CLAUDE.md
```markdown
### Subagent Delegation Strategy
**CRITICAL**: Automatically delegate to specialized subagents:

- **CI/Build Analysis**: Use `build-detective` subagent for:
  - GitHub Actions failures
  - Maven/Gradle build errors  
  - Docker build failures
  - Compilation errors
  - Test failures
  - Dependency conflicts
```

## Usage Patterns

### Command Patterns
```bash
# Single failure analysis
"Use build-detective to investigate this build failure: <URL>"

# Bulk pattern analysis  
"BD analyze last 10 CI failures for patterns"

# Shorthand format
"BD mvn test ProjectName"
"BD docker build failure"
"BD github actions timeout"
```

### GitHub CLI Integration
BD can automatically run:
```bash
gh run list --status failure --limit 10
gh run view <run-id> --log
gh workflow list --repo <repo>
```

### Structured Output Format
BD returns JSON with:
```json
{
  "confidence": 8,
  "error_type": "compilation",
  "build_step": "compile", 
  "primary_error": "cannot find symbol: class Example",
  "suggested_action": "Add missing import or dependency",
  "pattern_matched": "missing_import_java"
}
```

## Pattern Recognition Library

### High-Confidence Patterns (90%+ accuracy)
```markdown
• Docker COPY missing file: "COPY failed: file not found"
• Java version mismatch: "release version X not supported"
• Maven plugin missing: "Plugin org.apache.maven.plugins:maven-X-plugin not found"
• Git submodule errors: "No url found for submodule"
```

### Medium-Confidence Patterns (80-90% accuracy)
```markdown
• Dependency conflicts: Version collision indicators
• Port already in use: "Address already in use"
• Permission denied: File system access issues
• Out of memory: JVM heap space errors
```

### Low-Confidence Patterns (70-80% accuracy)
```markdown
• Complex Maven dependency trees
• Multi-module build failures
• Transitive dependency conflicts  
• Environment-specific configuration issues
```

## When NOT to Use Build Detective

### Escalate to Sonnet For
```markdown
❌ First-time project failures (need context understanding)
❌ Complex multi-system integration issues
❌ Custom build system configurations
❌ Security-related build failures
❌ Performance optimization analysis
❌ Architecture-level design decisions
```

### BD Sweet Spot
```markdown
✅ Recurring CI pipeline failures
✅ Standard Maven/Gradle/npm build errors
✅ Common Docker build issues
✅ Typical compilation/test failures
✅ Dependency version conflicts
✅ Standard configuration mistakes
```

## Sonnet Oversight Implementation

### Validation Function Template
```python
def validate_bd_analysis(bd_result, context):
    """Sonnet's quality check for BD analysis"""
    
    issues = []
    
    # Confidence validation
    if bd_result["confidence"] < 7:
        issues.append("LOW_CONFIDENCE: Manual review required")
    
    # Technology alignment
    if bd_result["error_type"] == "java" and not context.has_java_files():
        issues.append("TECH_MISMATCH: Java error in non-Java project")
    
    # Solution specificity
    if "check configuration" in bd_result["suggested_action"]:
        issues.append("GENERIC_SOLUTION: BD didn't find specific pattern")
    
    # Build phase logic
    if bd_result["build_step"] == "test" and "BUILD FAILURE" in context.log:
        issues.append("PHASE_MISMATCH: Test failure claimed but build failed")
    
    return ValidationResult(
        needs_review=len(issues) > 0,
        issues=issues,
        escalation_required=any("MISMATCH" in issue for issue in issues)
    )
```

### Decision Matrix
| BD Confidence | Context Complexity | Sonnet Action | Time Investment |
|---------------|-------------------|---------------|-----------------|
| 8-9 + Simple | Low | Quick validation | 30 seconds |
| 8-9 + Complex | High | Deep review | 2-3 minutes |
| 6-7 | Any | Manual analysis | 5+ minutes |
| <6 | Any | Full override | 10+ minutes |
| 10 | Any | Suspicious - verify | 1-2 minutes |

## Benefits and ROI

### Cost Efficiency
- **85% token reduction** for routine CI failures
- **10x faster** initial analysis than full Sonnet review
- **Bulk analysis** capability for pattern identification
- **Scalable** across unlimited projects with template system

### Quality Assurance
- **Validation system** prevents BD from misleading users
- **Pattern learning** improves accuracy over time
- **Escalation triggers** ensure complex cases get proper attention
- **User feedback loops** for continuous improvement

### Developer Experience  
- **Instant analysis** for common build failures
- **Actionable solutions** not just error identification
- **Cross-project consistency** in CI analysis approach
- **Reduced cognitive load** for routine debugging

## Troubleshooting

### BD Not Available
```bash
# Check if BD template exists
ls -la .claude/agents/build-detective.md

# If missing, run setup
./scripts/setup-build-detective.sh .
```

### Poor BD Analysis Quality
```markdown
Signs BD needs escalation:
• Generic solutions ("check configuration")
• Technology stack mismatches
• Overconfident on complex scenarios
• Solutions contradict project constraints

Action: Use Sonnet validation patterns to escalate
```

### GitHub CLI Issues
```bash
# Ensure GitHub CLI installed and authenticated
gh auth status
gh auth login

# Test access to repository
gh repo view <repo-name>
```

## Pattern Evolution and Learning

### Feedback Integration
```markdown
User reports BD was wrong:
1. Sonnet analyzes what BD missed
2. Determine if pattern improvement needed
3. Update BD template with lessons learned
4. Add escalation triggers for similar scenarios
5. Test improved patterns against historical failures
```

### Pattern Quality Tracking
```json
{
  "pattern_id": "docker_missing_file",
  "accuracy_rate": 0.94,
  "false_positive_count": 2,
  "escalation_threshold": 0.95,
  "complexity_tolerance": "low",
  "last_improvement": "2024-01-15"
}
```

## Multi-Project Deployment

### Template Distribution Strategy
```bash
# Deploy to Java projects
./setup-build-detective.sh /projects/java-app-1
./setup-build-detective.sh /projects/java-app-2

# Deploy to Python projects  
./setup-build-detective.sh /projects/python-api-1
./setup-build-detective.sh /projects/python-api-2
```

### Cross-Project Benefits
- **Consistent analysis patterns** across all projects
- **Shared pattern library** improvements benefit everyone
- **Standardized error classification** and response
- **Knowledge transfer** between project teams

## Advanced Usage

### Bulk Pattern Analysis
```markdown
"Use build-detective to analyze the last 20 CI failures across all repositories for recurring pattern identification"
```

### Historical Trend Analysis  
```markdown
"BD analyze CI failure trends over past month to identify systemic issues"
```

### Multi-Technology Support
BD templates can be customized for:
- **Java**: Maven, Gradle, Spring Boot, JUnit
- **Python**: pip, pytest, Django, FastAPI  
- **JavaScript**: npm, Jest, React, Node.js
- **Go**: go mod, go test, Docker builds
- **Rust**: Cargo, rustc, cross-compilation

## Success Metrics

### Quality Indicators
- **BD Accuracy Rate**: Target >90% for confidence >8
- **False Positive Rate**: <5% on high-confidence analyses
- **Escalation Precision**: Sonnet correctly identifies BD errors >95%
- **Time to Resolution**: BD + validation <2 minutes average

### Adoption Indicators
- **User Trust**: Developers accept BD recommendations >90%
- **Analysis Acceptance**: BD used without manual review >80%
- **Pattern Learning**: Monthly improvement in BD accuracy
- **Cost Savings**: Token usage reduction vs pure Sonnet analysis

## Conclusion

Build Detective represents a **cost-effective specialization** approach to AI-assisted development. By combining **Haiku's pattern recognition speed** with **Sonnet's oversight wisdom**, it delivers fast, reliable CI analysis while maintaining the quality standards developers need.

The key to BD success is **knowing when to trust it** and **when to escalate** - this guide provides the framework for making those decisions systematically and reliably.