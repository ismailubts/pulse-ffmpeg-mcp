#!/bin/bash
set -e

# Build Detective Setup Script
# Copies and customizes the build-detective template for a target project

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
TEMPLATE_DIR="$SCRIPT_DIR/../.claude/agents/templates"
TEMPLATE_FILE="$TEMPLATE_DIR/build-detective-template.md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_usage() {
    echo "Usage: $0 <target-project-path>"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/komposteur"
    echo "  $0 /path/to/vdvil"
    echo ""
    echo "This script will:"
    echo "  1. Create .claude/agents/ directory in target project"
    echo "  2. Copy and customize build-detective template"
    echo "  3. Prompt for project-specific configuration"
}

validate_target() {
    local target_path="$1"
    
    if [[ ! -d "$target_path" ]]; then
        echo -e "${RED}Error: Target directory '$target_path' does not exist${NC}"
        return 1
    fi
    
    if [[ ! -d "$target_path/.git" ]]; then
        echo -e "${YELLOW}Warning: '$target_path' is not a git repository${NC}"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 1
        fi
    fi
    
    return 0
}

prompt_project_config() {
    echo -e "${BLUE}Configure Build Detective for your project:${NC}"
    echo ""
    
    read -p "Project name: " PROJECT_NAME
    read -p "Primary language (e.g., Java, Python, Go): " PRIMARY_LANGUAGE
    read -p "Build system (e.g., Maven, Gradle, npm): " BUILD_SYSTEM
    read -p "Key dependencies (comma-separated): " KEY_DEPENDENCIES
    read -p "Deployment target (e.g., AWS, Docker, GitHub Pages): " DEPLOYMENT_TARGET
    
    echo ""
    echo -e "${BLUE}Common project issues (press Enter to skip):${NC}"
    read -p "Common issue 1: " COMMON_ISSUE_1
    read -p "Typical solution 1: " TYPICAL_SOLUTION_1
    read -p "Common issue 2: " COMMON_ISSUE_2
    read -p "Typical solution 2: " TYPICAL_SOLUTION_2
    read -p "Common issue 3: " COMMON_ISSUE_3
    read -p "Typical solution 3: " TYPICAL_SOLUTION_3
    
    # Set project-specific domain expertise
    case "$PRIMARY_LANGUAGE" in
        "Java"|"java")
            PROJECT_SPECIFIC_DOMAIN="Video Processing"
            PROJECT_SPECIFIC_EXPERTISE="FFmpeg, crossfade operations, multimedia pipeline tasks"
            ;;
        "Python"|"python")
            PROJECT_SPECIFIC_DOMAIN="MCP Integration"
            PROJECT_SPECIFIC_EXPERTISE="Model Context Protocol, async operations, API integration"
            ;;
        *)
            PROJECT_SPECIFIC_DOMAIN="Software Development"
            PROJECT_SPECIFIC_EXPERTISE="Build systems, dependency management, deployment pipelines"
            ;;
    esac
}

customize_template() {
    local template_content="$1"
    
    # Replace placeholders with actual values
    template_content="${template_content//\{\{PROJECT_NAME\}\}/$PROJECT_NAME}"
    template_content="${template_content//\{\{PRIMARY_LANGUAGE\}\}/$PRIMARY_LANGUAGE}"
    template_content="${template_content//\{\{BUILD_SYSTEM\}\}/$BUILD_SYSTEM}"
    template_content="${template_content//\{\{KEY_DEPENDENCIES\}\}/$KEY_DEPENDENCIES}"
    template_content="${template_content//\{\{DEPLOYMENT_TARGET\}\}/$DEPLOYMENT_TARGET}"
    template_content="${template_content//\{\{PROJECT_SPECIFIC_DOMAIN\}\}/$PROJECT_SPECIFIC_DOMAIN}"
    template_content="${template_content//\{\{PROJECT_SPECIFIC_EXPERTISE\}\}/$PROJECT_SPECIFIC_EXPERTISE}"
    template_content="${template_content//\{\{COMMON_ISSUE_1\}\}/$COMMON_ISSUE_1}"
    template_content="${template_content//\{\{TYPICAL_SOLUTION_1\}\}/$TYPICAL_SOLUTION_1}"
    template_content="${template_content//\{\{COMMON_ISSUE_2\}\}/$COMMON_ISSUE_2}"
    template_content="${template_content//\{\{TYPICAL_SOLUTION_2\}\}/$TYPICAL_SOLUTION_2}"
    template_content="${template_content//\{\{COMMON_ISSUE_3\}\}/$COMMON_ISSUE_3}"
    template_content="${template_content//\{\{TYPICAL_SOLUTION_3\}\}/$TYPICAL_SOLUTION_3}"
    
    echo "$template_content"
}

main() {
    if [[ $# -ne 1 ]]; then
        print_usage
        exit 1
    fi
    
    local target_path="$1"
    
    # Validate inputs
    if [[ ! -f "$TEMPLATE_FILE" ]]; then
        echo -e "${RED}Error: Template file not found at '$TEMPLATE_FILE'${NC}"
        exit 1
    fi
    
    if ! validate_target "$target_path"; then
        exit 1
    fi
    
    # Show what we're about to do
    echo -e "${GREEN}Setting up Build Detective for: $target_path${NC}"
    echo ""
    
    # Check if already exists
    local target_agents_dir="$target_path/.claude/agents"
    local target_file="$target_agents_dir/build-detective.md"
    
    if [[ -f "$target_file" ]]; then
        echo -e "${YELLOW}Warning: build-detective.md already exists${NC}"
        read -p "Overwrite? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Aborted."
            exit 0
        fi
    fi
    
    # Get project configuration
    prompt_project_config
    
    # Create target directory
    echo -e "${BLUE}Creating directory structure...${NC}"
    mkdir -p "$target_agents_dir"
    
    # Read template and customize
    echo -e "${BLUE}Customizing template...${NC}"
    local template_content
    template_content=$(cat "$TEMPLATE_FILE")
    local customized_content
    customized_content=$(customize_template "$template_content")
    
    # Write customized file
    echo "$customized_content" > "$target_file"
    
    echo -e "${GREEN}✅ Build Detective successfully set up!${NC}"
    echo ""
    echo "Created: $target_file"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Review and adjust $target_file if needed"
    echo "2. Test with: Use the build-detective to investigate this build failure: [URL]"
    echo "3. Add to your project's CLAUDE.md delegation triggers"
    echo ""
    echo -e "${BLUE}Integration example:${NC}"
    echo "Add to CLAUDE.md subagent delegation:"
    echo "- **CI/Build Analysis**: Use \`build-detective\` subagent for GitHub Actions failures"
}

main "$@"