#\!/bin/bash

echo "🎬 Creating music video with 12 YouTube Short segments..."

# Create input list file for segments
cat > segments_list.txt << EOL
file 'segments/seg01_Oa8iS1W3OCM.mp4'
file 'segments/seg02_Oa8iS1W3OCM.mp4'
file 'segments/seg03_Oa8iS1W3OCM.mp4'
file 'segments/seg04_Oa8iS1W3OCM.mp4'
file 'segments/seg05_3xEMCU1fyl8.mp4'
file 'segments/seg06_3xEMCU1fyl8.mp4'
file 'segments/seg07_3xEMCU1fyl8.mp4'
file 'segments/seg08_3xEMCU1fyl8.mp4'
file 'segments/seg09_PLnPZVqiyjA.mp4'
file 'segments/seg10_PLnPZVqiyjA.mp4'
file 'segments/seg11_PLnPZVqiyjA.mp4'
file 'segments/seg12_PLnPZVqiyjA.mp4'
EOL

# Step 1: Concatenate all segments with crossfade transitions
ffmpeg -f concat -safe 0 -i segments_list.txt \
  -filter_complex "
  [0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[v0];
  [1:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[v1];
  [2:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[v2];
  [3:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[v3];
  [4:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[v4];
  [5:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[v5];
  [6:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[v6];
  [7:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[v7];
  [8:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[v8];
  [9:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[v9];
  [10:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[v10];
  [11:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[v11];
  
  [v0][v1]xfade=transition=fade:duration=1:offset=1[x01];
  [x01][v2]xfade=transition=fade:duration=1:offset=3[x02];
  [x02][v3]xfade=transition=fade:duration=1:offset=5[x03];
  [x03][v4]xfade=transition=fade:duration=1:offset=7[x04];
  [x04][v5]xfade=transition=fade:duration=1:offset=9[x05];
  [x05][v6]xfade=transition=fade:duration=1:offset=11[x06];
  [x06][v7]xfade=transition=fade:duration=1:offset=13[x07];
  [x07][v8]xfade=transition=fade:duration=1:offset=15[x08];
  [x08][v9]xfade=transition=fade:duration=1:offset=17[x09];
  [x09][v10]xfade=transition=fade:duration=1:offset=19[x10];
  [x10][v11]xfade=transition=fade:duration=1:offset=21[video_out];
  
  [video_out]colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3:1[bit_compressed]
  " \
  -map "[bit_compressed]" -t 24 -c:v libx264 -preset fast -crf 23 temp_video_segments.mp4 -y

echo "✅ Video segments processed"

# Step 2: Add Subnautic music and final effects
ffmpeg -i temp_video_segments.mp4 -i "Subnautic Measures.flac" \
  -filter_complex "
  [0:v]setsar=1[video];
  [1:a]volume=0.8,atempo=1.0[audio];
  [video]fade=t=in:st=0:d=1:color=black,fade=t=out:st=23:d=1:color=black[final_video]
  " \
  -map "[final_video]" -map "[audio]" \
  -c:v libx264 -c:a aac -shortest -t 24 \
  subnautic_youtube_shorts_music_video.mp4 -y

echo "🎉 COMPLETE\! Created subnautic_youtube_shorts_music_video.mp4"
echo "   📊 24 seconds, 1080x1920 (YouTube Shorts)"
echo "   🎵 Subnautic Measures background music"
echo "   📹 12 segments from YouTube Shorts with transitions"
echo "   🎨 Bit-compression effects applied"

# Cleanup
rm segments_list.txt temp_video_segments.mp4 2>/dev/null || true

