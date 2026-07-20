# FFmpeg Runner Container - Lightweight & Fast
# This container ONLY contains FFmpeg and runs isolated from main app
FROM alpine:3.19

# Install FFmpeg and audio tools (ffprobe comes with ffmpeg package)
RUN apk add --no-cache \
    ffmpeg \
    # Audio processing
    libsndfile \
    && rm -rf /var/cache/apk/*

# Create non-root user for security
RUN addgroup -g 1001 ffmpeg && \
    adduser -u 1001 -G ffmpeg -s /bin/sh -D ffmpeg

# Create workspace directories
RUN mkdir -p /input /output /metadata /traces \
    && chown -R ffmpeg:ffmpeg /input /output /metadata /traces

# Working directory for operations
WORKDIR /workspace

# Switch to non-root user
USER ffmpeg

# Verify FFmpeg installation
RUN ffmpeg -version > /dev/null 2>&1 && \
    ffprobe -version > /dev/null 2>&1 && \
    echo "✅ FFmpeg runner container ready"

# Default entrypoint (can be overridden)
ENTRYPOINT ["ffmpeg"]

# Labels
LABEL maintainer="ismailubts" \
      version="1.0.0" \
      description="FFmpeg Runner - Isolated execution container" \
      purpose="Execute FFmpeg commands with volume-mounted files"