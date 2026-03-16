# 疗愈音乐资源获取指南

## 快速开始

系统需要的音频文件放在 `content/audio/` 目录下，文件名需与 `audio_manifest.yaml` 中定义的一致。

---

## 推荐免费音乐平台

### 1. Pixabay Music（强烈推荐）
- 网址：https://pixabay.com/music/
- 特点：完全免费，无需署名，可商用
- 搜索关键词：
  - `meditation` - 冥想音乐
  - `relaxation` - 放松音乐
  - `ambient` - 氛围音乐
  - `piano calm` - 轻柔钢琴
  - `nature` - 自然音效

### 2. Mixkit
- 网址：https://mixkit.co/free-stock-music/
- 特点：高质量，免费商用
- 分类：Calm / Ambient / Nature

### 3. Uppbeat
- 网址：https://uppbeat.io/
- 特点：免费版每月3首，质量高
- 分类：Meditation / Relaxing / Ambient

### 4. Free Music Archive
- 网址：https://freemusicarchive.org/
- 特点：大量独立音乐人作品
- 搜索：Ambient / Electronic / Instrumental

### 5. YouTube Audio Library
- 网址：https://studio.youtube.com/channel/UC/music
- 特点：免费用于视频，需要 YouTube 账号

---

## 必需音频文件清单

### 优先级 1：核心音乐（建议先准备）

| 文件名 | 用途 | 建议时长 | 搜索关键词 |
|-------|------|---------|-----------|
| `ambient_calm.mp3` | 正念冥想 | 5-10分钟 | meditation ambient calm |
| `soft_piano.mp3` | 呼吸觉察 | 5-10分钟 | soft piano relaxing |
| `deep_relaxation.mp3` | 深度放松 | 10分钟 | deep relaxation sleep |
| `nature_rain.mp3` | 雨声背景 | 10-15分钟 | rain sounds relaxing |
| `ocean_waves.mp3` | 海浪声 | 10-15分钟 | ocean waves calm |

### 优先级 2：自然音效

| 文件名 | 用途 | 搜索关键词 |
|-------|------|-----------|
| `nature_stream.mp3` | 溪流声 | stream water nature |
| `nature_birds.mp3` | 鸟鸣声 | birds morning nature |
| `forest_ambience.mp3` | 森林氛围 | forest ambience nature |

### 优先级 3：中式音乐

| 文件名 | 用途 | 搜索关键词 |
|-------|------|-----------|
| `chinese_guqin_calm.mp3` | 古琴静心 | guqin chinese traditional |
| `chinese_flute.mp3` | 竹笛 | chinese flute bamboo |
| `tibetan_bowl.mp3` | 颂钵 | tibetan singing bowl |

---

## 音频规格要求

```
格式：MP3
采样率：44100 Hz
比特率：128-320 kbps
声道：立体声（Stereo）
响度：-14 LUFS（建议）
```

---

## 批量下载脚本

如果您有 Pixabay 账号，可以使用以下脚本批量下载：

```bash
# 运行下载脚本
bash scripts/download_audio.sh
```

---

## 付费音乐推荐（高品质）

如果预算允许，以下平台提供专业疗愈音乐：

| 平台 | 价格 | 特点 |
|-----|------|------|
| Epidemic Sound | $15/月 | 专业级，大量冥想音乐 |
| Artlist | $199/年 | 高质量，无限下载 |
| Musicbed | 按曲付费 | 电影级品质 |
| Calm App 授权 | 联系商务 | 专业冥想音乐 |

---

## 自制音乐建议

如果您有音乐制作能力，可以使用：

- **GarageBand**（Mac 免费）- 制作简单氛围音乐
- **Audacity**（免费）- 编辑和混音
- **LMMS**（免费）- 电子音乐制作

### 推荐音色/乐器
- 钢琴（Piano）
- 合成器垫音（Synth Pad）
- 环境音效（Ambient Textures）
- 颂钵/钟声（Singing Bowl / Bells）

---

## 版权注意事项

⚠️ **重要提醒**：

1. 商业使用必须确认音乐授权
2. 保留音乐来源和授权证明
3. 避免使用有版权的流行音乐
4. 自然音效通常无版权问题

---

## 快速测试

下载几首音乐后，可以通过 API 测试播放：

```bash
# 测试音频文件是否可用
curl http://localhost:8000/api/device/audio/test
```

或在前端界面点击「开始疗愈」进入疗愈会话。
