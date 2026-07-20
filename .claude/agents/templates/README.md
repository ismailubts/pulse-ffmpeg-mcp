# Claude Agent Templates

Reusable Claude agent templates for consistent CI analysis across projects.

## Available Templates

### 🕵️ Build Detective Template

**Purpose**: Cost-effective build failure investigation using Haiku model for instant pattern recognition.

**Features**:
- ⚡ **Fast Analysis**: 400-800 tokens vs 3000+ (85% cost reduction)
- 🎯 **Structured Output**: JSON responses with specific error classification
- 🔧 **GitHub CLI Integration**: Bypasses URL expiration issues
- 📊 **Bulk Analysis**: Pattern identification across multiple builds
- 🎨 **Project Customization**: Technology stack and domain-specific patterns

## Quick Setup

### Install to Any Project

```bash
# From pulse-ffmpeg-mcp directory
./scripts/setup-build-detective.sh /path/to/target/project
```

### Example Usage

```bash
# Setup for Komposteur
./scripts/setup-build-detective.sh /path/to/komposteur

# Setup for VDVIL  
./scripts/setup-build-detective.sh /path/to/vdvil
```

## What the Setup Does

1. **Creates directory**: `target-project/.claude/agents/`
2. **Customizes template**: Prompts for project-specific configuration
3. **Installs agent**: `target-project/.claude/agents/build-detective.md`
4. **Preserves autonomy**: Each project owns its copy

## Project Customization

The setup script prompts for:

- **Project name** and primary language
- **Build system** (Maven, Gradle, npm)
- **Key dependencies** and deployment targets  
- **Common issues** and typical solutions
- **Domain expertise** (auto-detected from language)

## Template Variables

Templates use `{{VARIABLE}}` placeholders:

| Variable | Purpose | Example |
|----------|---------|---------|
| `{{PROJECT_NAME}}` | Project identification | "Komposteur" |
| `{{PRIMARY_LANGUAGE}}` | Main programming language | "Java" |
| `{{BUILD_SYSTEM}}` | Build tool | "Maven" |
| `{{PROJECT_SPECIFIC_DOMAIN}}` | Domain expertise | "Video Processing" |
| `{{COMMON_ISSUE_X}}` | Frequent problems | "Maven plugin failures" |

## Integration with CLAUDE.md

Add to your project's `CLAUDE.md` delegation strategy:

```markdown
### Subagent Delegation Strategy
**CRITICAL**: Automatically delegate tasks to specialized subagents:

- **CI/Build Analysis**: Use `build-detective` subagent for GitHub Actions failures, Maven errors
```

## Usage Patterns

### Single Build Analysis
```
Use the build-detective to investigate this build failure: 
https://github.com/ismailubts/pulse-ffmpeg-mcp/actions/runs/123456789
```

### Bulk Pattern Analysis
```
Analyze the last 10 CI failures for recurring patterns using build-detective
```

### GitHub CLI Commands
The agent can run:
```bash
gh run list --status failure --limit 10 --json conclusion,workflowName
gh run view <run-id> --repo <repo> --log
```

## Benefits

### Cost Efficiency
- **Token Usage**: 400-800 vs 3000+ tokens
- **Model**: Haiku vs Claude Sonnet (significantly cheaper)
- **Accuracy**: 85%+ for actionable analysis

### Multi-Project Consistency  
- **Standardized**: Same analysis patterns across projects
- **Customizable**: Project-specific expertise and common issues
- **Maintainable**: Single template source, distributed copies

### Developer Experience
- **Fast Setup**: 2-3 minutes per project
- **Immediate Value**: Works with GitHub CLI out of the box
- **Actionable Results**: Structured JSON with specific fix suggestions

## Template Development

### Adding New Templates

1. Create `new-template.md` in this directory
2. Use `{{VARIABLE}}` placeholders for customization
3. Update setup script with new template option
4. Add documentation here

### Customization Guidelines

- **Keep it simple**: Minimal variables, maximum reuse
- **Domain-specific**: Include project-type expertise
- **Actionable**: Focus on fixable issues, not just detection
- **Cost-conscious**: Optimize for token efficiency

## Cross-Project Usage

### Safe Patterns ✅
- **Template copying**: Each project owns its agent
- **Read-only access**: Templates read from pulse-ffmpeg-mcp
- **Opt-in adoption**: Projects choose to install

### Avoid ❌
- **Shared dependencies**: No cross-project file dependencies
- **Auto-modification**: No automatic changes to other projects
- **Complex tooling**: Keep setup scripts simple

## Troubleshooting

### Setup Issues
- **Permission errors**: Ensure target directory is writable
- **Git warnings**: Non-git directories show warnings but continue
- **Existing files**: Script prompts before overwriting

### Agent Issues
- **GitHub CLI**: Requires `gh` command installed and authenticated
- **Token limits**: Haiku model has rate limits (usually not an issue)
- **Project context**: May need adjustment for non-Java projects

## Future Templates

Potential additions:
- **Performance Analyzer**: System performance and bottleneck analysis
- **Security Scanner**: Dependency vulnerability assessment  
- **Documentation Generator**: Auto-generate project documentation
- **Release Manager**: Automated version bumping and changelog generation