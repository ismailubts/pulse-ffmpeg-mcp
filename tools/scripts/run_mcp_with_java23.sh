#!/bin/bash
# Run MCP server with Java 23

export JAVA_HOME="/usr/local/opt/openjdk/libexec/openjdk.jdk/Contents/Home"
export PATH="/usr/local/opt/openjdk/bin:$PATH"

echo "🔧 Java Environment:"
echo "   JAVA_HOME: $JAVA_HOME" 
echo "   Java binary: $(which java)"
echo "   Java version: $(java -version 2>&1 | head -1)"

echo ""
echo "🚀 Starting MCP server..."
.venv/bin/python -m src.server