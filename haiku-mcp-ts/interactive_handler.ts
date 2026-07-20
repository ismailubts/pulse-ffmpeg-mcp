import { HaikuMCPClient } from './client.ts';

class InteractiveMCPChat {
  private client: HaikuMCPClient;
  private connected: boolean = false;
  
  constructor() {
    this.client = new HaikuMCPClient();
  }
  
  async connect() {
    if (!this.connected) {
      await this.client.connect();
      this.connected = true;
    }
  }
  
  async disconnect() {
    if (this.connected) {
      await this.client.disconnect();
      this.connected = false;
    }
  }
  
  async processCommand(input: string): Promise<string> {
    await this.connect();
    
    const command = input.toLowerCase().trim();
    
    // Handle built-in commands
    if (command === 'list files' || command.includes('show') && command.includes('files')) {
      return this.handleListFiles();
    }
    
    if (command === 'stats' || command === 'statistics') {
      return this.handleStats();
    }
    
    if (command === 'help') {
      return this.handleHelp();
    }
    
    if (command.includes('download') && command.includes('youtube')) {
      return this.handleYouTubeDownload(input);
    }
    
    if (command.includes('create') || command.includes('make') || command.includes('generate')) {
      return this.handleCreateVideo(input);
    }
    
    if (command.includes('process') || command.includes('convert') || command.includes('transform')) {
      return this.handleProcessVideo(input);
    }
    
    // Generic processing - let the LLM decide
    return this.handleGenericRequest(input);
  }
  
  private async handleListFiles(): Promise<string> {
    try {
      const response = await this.client.callTool('list_files', {});
      const files = JSON.parse(response.content[0].text).files;
      
      if (files.length === 0) {
        return "No media files found in registry. Add some videos/audio files first.";
      }
      
      let result = `📁 Available files (${files.length}):\n\n`;
      
      const videos = files.filter(f => f.mediaType === 'video');
      const audios = files.filter(f => f.mediaType === 'audio');
      
      if (videos.length > 0) {
        result += "📹 Videos:\n";
        videos.forEach(f => {
          const sizeMB = Math.round(f.size / 1024 / 1024);
          result += `  • ${f.id}: ${f.path.split('/').pop()} (${sizeMB}MB)\n`;
        });
        result += "\n";
      }
      
      if (audios.length > 0) {
        result += "🎵 Audio:\n";
        audios.forEach(f => {
          const sizeMB = Math.round(f.size / 1024 / 1024);
          result += `  • ${f.id}: ${f.path.split('/').pop()} (${sizeMB}MB)\n`;
        });
      }
      
      return result;
    } catch (error) {
      return `❌ Error listing files: ${error.message}`;
    }
  }
  
  private async handleStats(): Promise<string> {
    try {
      const response = await this.client.callTool('get_llm_stats', {});
      const stats = JSON.parse(response.content[0].text);
      
      return `📊 LLM Statistics:
      
🤖 Primary Model: ${stats.primary_model.provider}/${stats.primary_model.model}
🔄 Fallback Model: ${stats.fallback_model.provider}/${stats.fallback_model.model}

💰 Estimated Costs:
  • Primary: $${stats.estimated_costs.primary_per_1k_tokens}/1k tokens
  • Fallback: $${stats.estimated_costs.fallback_per_1k_tokens}/1k tokens
  
⚡ Performance: Both models ready for video processing`;
    } catch (error) {
      return `❌ Error getting stats: ${error.message}`;
    }
  }
  
  private handleHelp(): string {
    return `🎬 Interactive MCP Video Processing Help

📋 Available Commands:
  
🗂️  File Management:
  • "list files" / "show me files" - Display all available media
  • "download youtube [URL]" - Download video/audio from YouTube
  
🎥 Video Creation:
  • "create/make [description]" - Generate music videos
    Examples:
    - "Create a 30-second video with smooth crossfades"
    - "Make a beat-synced video at 128 BPM"
    - "Generate a cinematic video with fade effects"
  
🔧 Video Processing:  
  • "process/convert [description]" - Transform existing videos
    Examples:
    - "Convert to 720p with better compression"
    - "Add fade in/out effects to my video"
    - "Reduce file size while keeping quality"
  
📊 System:
  • "stats" - Show LLM usage and cost information
  • "help" - Show this help message
  • "quit" - Exit the chat interface
  
💡 Tips:
  • Be specific about duration, quality, effects you want
  • Mention file IDs from 'list files' if targeting specific media
  • Natural language works - describe what you want to achieve`;
  }
  
  private async handleCreateVideo(input: string): Promise<string> {
    try {
      // Check if request contains YouTube URLs
      const youtubeRegex = /https?:\/\/(www\.)?(youtube\.com|youtu\.be)\/[^\s]+/g;
      const youtubeUrls = input.match(youtubeRegex);
      
      if (youtubeUrls && youtubeUrls.length > 0) {
        return `🚧 YouTube download integration needed!
        
📋 Your request analysis:
  • Found ${youtubeUrls.length} YouTube URLs
  • Custom requirements: ${input.replace(youtubeRegex, '[YouTube URL]')}
  
⚠️  Current limitation: The MCP server needs YouTube download capability.
  
💡 Alternative: Download the videos manually first, then ask me to process them with:
  "Combine my videos with 1/3 time each, use first video's audio, add 8-bit filter"`;
      }
      
      // Check if request mentions specific files or complex operations
      if (input.includes('combine') || input.includes('three videos') || input.includes('1/3')) {
        return `🚧 Complex video operations detected!
        
📋 Your request: "${input}"
  
⚠️  This requires advanced video processing beyond basic music video creation.
  
💡 This needs custom FFMPEG commands. The current MCP server is designed for simple music video creation.
  
🔧 Consider using the Python MCP server instead, which has more advanced video processing capabilities.`;
      }
      
      // Fall back to simple music video creation with available files
      const filesResponse = await this.client.callTool('list_files', {});
      const files = JSON.parse(filesResponse.content[0].text).files;
      
      const videoFiles = files.filter(f => f.mediaType === 'video');
      const audioFiles = files.filter(f => f.mediaType === 'audio');
      
      if (videoFiles.length === 0 || audioFiles.length === 0) {
        return "❌ Need both video and audio files for music video creation. Use 'list files' to check available media.";
      }
      
      const videoFile = videoFiles[0];
      const audioFile = audioFiles[0];
      
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const outputFile = `/tmp/pulse/ffmpeg-mcp/generated-videos/interactive_${timestamp}.mp4`;
      
      const response = await this.client.callTool('create_music_video', {
        video_file: videoFile.id,
        audio_file: audioFile.id,
        output_file: outputFile,
        duration: 18,
        user_request: input
      });
      
      const result = JSON.parse(response.content[0].text);
      
      if (result.success) {
        const sizeMB = Math.round(result.file_size / 1024 / 1024) || "unknown";
        return `⚠️  Simple music video created (not your full request):

📁 Output: ${result.output_file}
📹 Using: ${videoFile.path.split('/').pop()}
🎵 Audio: ${audioFile.path.split('/').pop()}

💡 Your original request needs more advanced processing capabilities.`;
      } else {
        return `❌ Video creation failed: ${result.error}`;
      }
    } catch (error) {
      return `❌ Error creating video: ${error.message}`;
    }
  }
  
  private async handleProcessVideo(input: string): Promise<string> {
    return "🚧 Video processing coming soon! For now, use 'create video' commands.";
  }
  
  private async handleYouTubeDownload(input: string): Promise<string> {
    return "🚧 YouTube download coming soon! Add URLs and download directories to your request.";
  }
  
  private async handleGenericRequest(input: string): Promise<string> {
    // For generic requests, try to determine the best approach
    if (input.toLowerCase().includes('video') || input.toLowerCase().includes('music')) {
      return this.handleCreateVideo(input);
    } else {
      return `🤔 I'm not sure how to help with: "${input}"

Try being more specific:
• "create a video..." for music video generation
• "list files" to see available media
• "help" for all available commands`;
    }
  }
}

// Main execution
async function main() {
  const chat = new InteractiveMCPChat();
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.error('Usage: node interactive_handler.js "<command>"');
    process.exit(1);
  }
  
  const command = args.join(' ');
  
  try {
    const response = await chat.processCommand(command);
    console.log(response);
    await chat.disconnect();
  } catch (error) {
    console.error(`❌ Error: ${error.message}`);
    await chat.disconnect();
    process.exit(1);
  }
}

main();
