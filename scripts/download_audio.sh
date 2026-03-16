#!/bin/bash
# 下载免费疗愈音乐脚本
# 音源来自 Pixabay（免版税，可商用）

AUDIO_DIR="content/audio"
mkdir -p "$AUDIO_DIR"

echo "开始下载疗愈音乐..."

# 放松/冥想音乐
echo "下载: 宁静氛围音乐..."
curl -L -o "$AUDIO_DIR/ambient_calm.mp3" \
  "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3" 2>/dev/null

echo "下载: 轻柔钢琴..."
curl -L -o "$AUDIO_DIR/soft_piano.mp3" \
  "https://cdn.pixabay.com/download/audio/2022/10/25/audio_946bc3eb4c.mp3" 2>/dev/null

echo "下载: 深度放松..."
curl -L -o "$AUDIO_DIR/deep_relaxation.mp3" \
  "https://cdn.pixabay.com/download/audio/2023/09/04/audio_4e5d6e7f0a.mp3" 2>/dev/null

# 自然音效
echo "下载: 雨声..."
curl -L -o "$AUDIO_DIR/nature_rain.mp3" \
  "https://cdn.pixabay.com/download/audio/2022/03/10/audio_c8c8a73467.mp3" 2>/dev/null

echo "下载: 海浪声..."
curl -L -o "$AUDIO_DIR/ocean_waves.mp3" \
  "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0c6ff1bab.mp3" 2>/dev/null

echo "下载: 森林鸟鸣..."
curl -L -o "$AUDIO_DIR/nature_birds.mp3" \
  "https://cdn.pixabay.com/download/audio/2021/09/06/audio_0a8b8c8e8a.mp3" 2>/dev/null

echo "下载: 溪流声..."
curl -L -o "$AUDIO_DIR/nature_stream.mp3" \
  "https://cdn.pixabay.com/download/audio/2022/03/15/audio_942694a41b.mp3" 2>/dev/null

# 统计
echo ""
echo "下载完成！"
echo "音频文件列表："
ls -lh "$AUDIO_DIR"/*.mp3 2>/dev/null | awk '{print $9, $5}'
