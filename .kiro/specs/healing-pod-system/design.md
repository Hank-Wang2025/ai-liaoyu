# Design Document: 智能疗愈仓系统

## Overview

智能疗愈仓系统是一个基于 Mac Mini M4 Pro 的本地化心理疗愈解决方案。系统采用模块化架构，由情绪分析引擎、疗愈引擎、设备控制器和用户界面四大核心组件构成。所有 AI 推理均在本地完成，确保用户隐私安全。

### 技术栈选型

| 层级 | 技术选择 | 理由 |
|------|----------|------|
| 主控应用 | Electron + Vue 3 + TypeScript | 跨平台、UI 灵活、开发效率高 |
| 后端服务 | Python + FastAPI | AI 生态完善、异步支持好 |
| AI 推理 | PyTorch MPS / MLX | Mac 原生优化 |
| 语音识别 | SenseVoice-Small | 中文最强、内置情感识别 |
| 情绪识别 | emotion2vec+ large | 9 类情绪、跨语言 SOTA |
| 语音合成 | CosyVoice 3.0 | 情感可控、流式输出 |
| 大语言模型 | Qwen3-8B | 中文理解最强 |
| 面部分析 | MediaPipe + CNN | 轻量、实时 |
| 数据库 | SQLite | 单文件、免维护 |
| 设备通信 | asyncio + bleak (BLE) | 异步、Mac 兼容好 |

### 硬件配置

| 组件 | 规格 | 用途 |
|------|------|------|
| Mac Mini | M4 Pro 48GB | 主控工作站 |
| 显示器 | 4K 曲面屏 / 投影仪 | 视觉内容展示 |
| 音响 | 4 声道环绕音响 | 沉浸式音频 |
| 灯光 | WiFi 智能灯带 (Yeelight) | 氛围灯光 |
| 摄像头 | USB 高清摄像头 | 面部表情捕捉 |
| 麦克风 | USB 指向性麦克风 | 语音采集 |
| 心率手环 | BLE 心率带 | 生理信号采集 |
| 按摩座椅 | 蓝牙智能座椅 | 触觉反馈 |
| 香薰机 | WiFi 智能香薰 | 嗅觉刺激 |

## Architecture

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户界面层                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Electron + Vue 3 应用                               │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │  │
│  │  │  欢迎页面   │ │  疗愈进行   │ │  报告页面   │ │  管理后台   │     │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────┤
│                              API 网关层                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    FastAPI (localhost:8000)                            │  │
│  │  /api/emotion  /api/therapy  /api/device  /api/session  /api/admin    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────┤
│                              服务层                                          │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐               │
│  │  Emotion Engine │ │  Therapy Engine │ │ Device Controller│               │
│  │                 │ │                 │ │                 │               │
│  │ ┌─────────────┐ │ │ ┌─────────────┐ │ │ ┌─────────────┐ │               │
│  │ │ SenseVoice  │ │ │ │ Plan Manager│ │ │ │ Light Ctrl  │ │               │
│  │ │ emotion2vec │ │ │ │ Scheduler   │ │ │ │ Audio Ctrl  │ │               │
│  │ │ MediaPipe   │ │ │ │ Feedback    │ │ │ │ Chair Ctrl  │ │               │
│  │ │ HRV Analyzer│ │ │ │ CosyVoice   │ │ │ │ Scent Ctrl  │ │               │
│  │ │ Fusion      │ │ │ │ Qwen3       │ │ │ │ Display Ctrl│ │               │
│  │ └─────────────┘ │ │ └─────────────┘ │ │ └─────────────┘ │               │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘               │
├─────────────────────────────────────────────────────────────────────────────┤
│                              数据层                                          │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐               │
│  │    SQLite       │ │   Content Store │ │   Config Store  │               │
│  │  (用户数据)     │ │  (音视频资源)   │ │  (YAML 配置)    │               │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘               │
├─────────────────────────────────────────────────────────────────────────────┤
│                              硬件层                                          │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │
│  │ 麦克风 │ │ 摄像头 │ │ 心率带 │ │ 音响   │ │ 灯光   │ │ 座椅   │        │
│  │ (USB)  │ │ (USB)  │ │ (BLE)  │ │ (USB)  │ │ (WiFi) │ │ (BLE)  │        │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 数据流图

```
用户语音输入                用户面部图像              心率数据
     │                          │                      │
     ▼                          ▼                      ▼
┌─────────────┐          ┌─────────────┐        ┌─────────────┐
│ SenseVoice  │          │  MediaPipe  │        │ HRV Analyzer│
│ + emotion2vec│          │  + CNN      │        │             │
└──────┬──────┘          └──────┬──────┘        └──────┬──────┘
       │                        │                      │
       │    语音情绪            │   面部情绪           │  压力指数
       │    + 文本              │   + 表情             │
       └────────────────────────┼──────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   多模态融合模块       │
                    │   Emotion Fusion      │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   统一情绪状态         │
                    │   EmotionState        │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   疗愈方案匹配         │
                    │   Therapy Matcher     │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   疗愈方案执行         │
                    │   Therapy Executor    │
                    └───────────┬───────────┘
                                │
        ┌───────────┬───────────┼───────────┬───────────┐
        ▼           ▼           ▼           ▼           ▼
    ┌───────┐   ┌───────┐   ┌───────┐   ┌───────┐   ┌───────┐
    │ 灯光  │   │ 音频  │   │ 视觉  │   │ 座椅  │   │ 香薰  │
    └───────┘   └───────┘   └───────┘   └───────┘   └───────┘
```

## Components and Interfaces

### 1. Emotion Engine (情绪分析引擎)

负责多模态情绪识别和融合。

```python
# 接口定义
class EmotionEngine:
    async def analyze_audio(self, audio_data: bytes) -> AudioAnalysisResult:
        """分析音频，返回语音识别结果和情绪"""
        pass
    
    async def analyze_face(self, frame: np.ndarray) -> FaceAnalysisResult:
        """分析面部图像，返回表情识别结果"""
        pass
    
    async def analyze_bio(self, heart_rate: List[int]) -> BioAnalysisResult:
        """分析生理信号，返回压力指数"""
        pass
    
    async def fuse_emotions(
        self, 
        audio: AudioAnalysisResult,
        face: FaceAnalysisResult,
        bio: BioAnalysisResult
    ) -> EmotionState:
        """融合多模态情绪，返回统一情绪状态"""
        pass
```

#### 1.1 SenseVoice 语音分析模块

```python
class SenseVoiceAnalyzer:
    def __init__(self, model_dir: str = "iic/SenseVoiceSmall"):
        self.model = AutoModel(
            model=model_dir,
            vad_model="fsmn-vad",
            vad_kwargs={"max_single_segment_time": 30000},
            device="mps"  # Mac Metal 加速
        )
    
    async def analyze(self, audio_path: str) -> dict:
        """
        返回:
        - text: 识别文本
        - language: 语言类型
        - emotion: 情感标签 (happy/sad/angry/neutral)
        - event: 音频事件 (laughter/crying/cough/etc)
        """
        result = self.model.generate(
            input=audio_path,
            language="auto",
            use_itn=True
        )
        return self._parse_result(result)
```

#### 1.2 emotion2vec+ 情绪识别模块

```python
class Emotion2VecAnalyzer:
    EMOTION_LABELS = [
        "angry", "happy", "neutral", "sad", 
        "surprised", "fearful", "disgusted", 
        "anxious", "tired"
    ]
    
    def __init__(self, model_dir: str = "iic/emotion2vec_plus_large"):
        self.model = AutoModel(model=model_dir, device="mps")
    
    async def analyze(self, audio_path: str) -> dict:
        """
        返回:
        - emotion: 主要情绪类别
        - scores: 各情绪的置信度分数
        - intensity: 情绪强度 (0-1)
        """
        result = self.model.generate(input=audio_path)
        return self._parse_scores(result)
```

#### 1.3 MediaPipe 面部分析模块

```python
class FaceAnalyzer:
    def __init__(self):
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
        self.emotion_classifier = self._load_emotion_cnn()
    
    async def analyze(self, frame: np.ndarray) -> dict:
        """
        返回:
        - landmarks: 468 个面部关键点
        - emotion: 表情类别
        - confidence: 置信度
        - au_activations: 面部动作单元激活
        """
        results = self.face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0]
            emotion = self._classify_emotion(landmarks)
            return {"landmarks": landmarks, "emotion": emotion}
        return None
```

#### 1.4 多模态融合模块

```python
class EmotionFusion:
    def __init__(self, weights: dict = None):
        self.weights = weights or {
            "audio": 0.4,
            "face": 0.35,
            "bio": 0.25
        }
    
    def fuse(
        self,
        audio_emotion: dict,
        face_emotion: dict,
        bio_stress: float
    ) -> EmotionState:
        """
        融合策略:
        1. 生理信号作为基准（最客观）
        2. 面部表情验证语音情绪
        3. 冲突时优先采信生理 > 面部 > 语音
        """
        # 计算加权情绪向量
        emotion_vector = self._weighted_average(
            audio_emotion, face_emotion, bio_stress
        )
        
        return EmotionState(
            category=self._get_primary_emotion(emotion_vector),
            intensity=self._calculate_intensity(emotion_vector),
            valence=self._calculate_valence(emotion_vector),
            arousal=self._calculate_arousal(emotion_vector, bio_stress)
        )
```

### 2. Therapy Engine (疗愈引擎)

负责疗愈方案匹配、执行和内容生成。

```python
class TherapyEngine:
    async def match_plan(self, emotion: EmotionState, user_prefs: dict) -> TherapyPlan:
        """根据情绪状态匹配疗愈方案"""
        pass
    
    async def execute_plan(self, plan: TherapyPlan) -> AsyncGenerator[TherapyEvent, None]:
        """执行疗愈方案，生成事件流"""
        pass
    
    async def generate_voice(self, text: str, emotion: str) -> bytes:
        """使用 CosyVoice 生成语音"""
        pass
    
    async def chat(self, message: str, context: List[dict]) -> str:
        """使用 Qwen3 进行对话"""
        pass
```

#### 2.1 疗愈方案管理器

```python
class PlanManager:
    def __init__(self, plans_dir: str = "content/plans"):
        self.plans = self._load_plans(plans_dir)
    
    def match(self, emotion: EmotionState, style: str = "auto") -> TherapyPlan:
        """
        匹配逻辑:
        1. 根据主要情绪类别筛选候选方案
        2. 根据情绪强度选择方案强度
        3. 根据用户偏好选择风格（中式/现代）
        """
        candidates = [p for p in self.plans if emotion.category in p.target_emotions]
        
        # 按情绪强度排序
        if emotion.intensity > 0.7:
            candidates = [p for p in candidates if p.intensity == "high"]
        elif emotion.intensity > 0.4:
            candidates = [p for p in candidates if p.intensity == "medium"]
        else:
            candidates = [p for p in candidates if p.intensity == "low"]
        
        # 按风格筛选
        if style != "auto":
            candidates = [p for p in candidates if p.style == style]
        
        return candidates[0] if candidates else self.default_plan
```

#### 2.2 CosyVoice 语音合成模块

```python
class VoiceSynthesizer:
    def __init__(self, model_dir: str = "CosyVoice-300M-SFT"):
        from cosyvoice import CosyVoice
        self.model = CosyVoice(model_dir)
        self.default_speaker = "中文女"
    
    async def synthesize(
        self, 
        text: str, 
        emotion: str = "gentle",
        speed: float = 1.0
    ) -> bytes:
        """
        生成语音:
        - emotion: gentle/warm/calm/encouraging
        - speed: 0.8-1.2
        """
        # 添加情感控制标签
        prompt = self._add_emotion_prompt(text, emotion)
        
        # 流式生成
        audio_chunks = []
        for chunk in self.model.inference_sft(
            prompt, 
            self.default_speaker,
            stream=True
        ):
            audio_chunks.append(chunk)
        
        return self._concat_audio(audio_chunks)
    
    async def clone_voice(self, reference_audio: str, text: str) -> bytes:
        """零样本语音克隆"""
        return self.model.inference_zero_shot(
            text,
            reference_audio
        )
```

#### 2.3 Qwen3 对话模块

```python
class DialogEngine:
    SYSTEM_PROMPT = """你是一个温暖、有同理心的疗愈助手。你的任务是：
1. 倾听用户的倾诉，给予情感支持
2. 使用温和、非评判的语言回应
3. 适时提供积极的引导和建议
4. 明确说明你是 AI 助手，不能替代专业心理咨询
5. 如果检测到严重心理问题，建议用户寻求专业帮助

注意：不要提供具体的心理治疗建议，只提供情感支持。"""

    def __init__(self, model_path: str = "Qwen/Qwen3-8B"):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16,
            device_map="mps"
        )
    
    async def chat(self, message: str, history: List[dict]) -> str:
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})
        
        inputs = self.tokenizer.apply_chat_template(
            messages, return_tensors="pt"
        ).to("mps")
        
        outputs = self.model.generate(
            inputs,
            max_new_tokens=512,
            temperature=0.7,
            do_sample=True
        )
        
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
```

### 3. Device Controller (设备控制器)

负责控制所有硬件设备。

```python
class DeviceController:
    async def set_light(self, color: str, brightness: int, transition: int) -> None:
        """控制灯光"""
        pass
    
    async def play_audio(self, file: str, volume: int, channel: str) -> None:
        """播放音频"""
        pass
    
    async def show_visual(self, file: str, mode: str) -> None:
        """显示视觉内容"""
        pass
    
    async def set_chair(self, mode: str, intensity: int) -> None:
        """控制座椅"""
        pass
    
    async def set_scent(self, type: str, intensity: int) -> None:
        """控制香薰"""
        pass
```

#### 3.1 灯光控制器

```python
class LightController:
    def __init__(self, config: dict):
        self.lights = []
        for light_config in config.get("lights", []):
            if light_config["type"] == "yeelight":
                self.lights.append(YeelightAdapter(light_config))
            elif light_config["type"] == "wifi":
                self.lights.append(WiFiLightAdapter(light_config))
    
    async def set_color(
        self, 
        color: str,  # HEX 颜色值
        brightness: int,  # 0-100
        transition: int = 3000  # 过渡时间 ms
    ):
        """设置灯光颜色和亮度"""
        rgb = self._hex_to_rgb(color)
        tasks = [
            light.set_rgb(rgb, brightness, transition)
            for light in self.lights
        ]
        await asyncio.gather(*tasks)
    
    async def breath_mode(self, color: str, period: int = 4000):
        """呼吸灯模式"""
        while True:
            await self.set_color(color, 80, period // 2)
            await asyncio.sleep(period // 2000)
            await self.set_color(color, 30, period // 2)
            await asyncio.sleep(period // 2000)


class YeelightAdapter:
    def __init__(self, config: dict):
        from yeelight import Bulb
        self.bulb = Bulb(config["ip"])
    
    async def set_rgb(self, rgb: tuple, brightness: int, transition: int):
        self.bulb.set_rgb(*rgb)
        self.bulb.set_brightness(brightness)
```

#### 3.2 音频控制器

```python
class AudioController:
    def __init__(self, config: dict):
        import sounddevice as sd
        self.sample_rate = config.get("sample_rate", 44100)
        self.channels = config.get("channels", 4)
        self.current_stream = None
    
    async def play(
        self, 
        file_path: str, 
        volume: float = 0.8,
        loop: bool = False,
        fade_in: int = 2000
    ):
        """播放音频文件"""
        import soundfile as sf
        data, sr = sf.read(file_path)
        
        # 音量调整
        data = data * volume
        
        # 淡入效果
        if fade_in > 0:
            fade_samples = int(sr * fade_in / 1000)
            fade_curve = np.linspace(0, 1, fade_samples)
            data[:fade_samples] *= fade_curve
        
        # 播放
        self.current_stream = sd.play(data, sr)
    
    async def stop(self, fade_out: int = 2000):
        """停止播放"""
        if self.current_stream:
            # 淡出效果
            sd.stop()
            self.current_stream = None
    
    async def set_volume(self, volume: float):
        """调整音量"""
        pass
```

#### 3.3 座椅控制器

```python
class ChairController:
    MODES = {
        "gentle": {"pattern": [1, 0, 1, 0], "intensity": 30},
        "wave": {"pattern": [1, 2, 3, 2, 1], "intensity": 50},
        "deep": {"pattern": [3, 3, 3, 3], "intensity": 70},
        "pulse": {"pattern": [3, 0, 3, 0], "intensity": 60},
        "relax": {"pattern": [1, 1, 2, 1], "intensity": 40}
    }
    
    def __init__(self, config: dict):
        from bleak import BleakClient
        self.device_address = config["address"]
        self.client = None
    
    async def connect(self):
        self.client = BleakClient(self.device_address)
        await self.client.connect()
    
    async def set_mode(self, mode: str, intensity: int = None):
        """设置按摩模式"""
        if mode not in self.MODES:
            mode = "gentle"
        
        mode_config = self.MODES[mode]
        if intensity is not None:
            mode_config["intensity"] = intensity
        
        # 发送 BLE 命令
        command = self._build_command(mode_config)
        await self.client.write_gatt_char(
            self.CHAR_UUID,
            command
        )
    
    async def stop(self):
        """停止按摩"""
        await self.set_mode("off", 0)
```

## Data Models

### 核心数据模型

```python
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from datetime import datetime

class EmotionCategory(Enum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    ANXIOUS = "anxious"
    TIRED = "tired"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    DISGUSTED = "disgusted"
    NEUTRAL = "neutral"

@dataclass
class EmotionState:
    """统一情绪状态"""
    category: EmotionCategory  # 主要情绪类别
    intensity: float  # 情绪强度 0-1
    valence: float  # 效价 -1 到 1 (负面到正面)
    arousal: float  # 唤醒度 0-1 (平静到激动)
    confidence: float  # 置信度 0-1
    timestamp: datetime
    
    # 各模态原始数据
    audio_emotion: Optional[dict] = None
    face_emotion: Optional[dict] = None
    bio_stress: Optional[float] = None

@dataclass
class TherapyPlan:
    """疗愈方案"""
    id: str
    name: str
    description: str
    target_emotions: List[EmotionCategory]
    intensity: str  # low/medium/high
    style: str  # chinese/modern
    duration: int  # 总时长（秒）
    phases: List['TherapyPhase']

@dataclass
class TherapyPhase:
    """疗愈阶段"""
    name: str
    duration: int  # 秒
    light: 'LightConfig'
    audio: 'AudioConfig'
    visual: Optional['VisualConfig']
    voice_guide: Optional['VoiceGuideConfig']
    chair: Optional['ChairConfig']
    scent: Optional['ScentConfig']

@dataclass
class LightConfig:
    color: str  # HEX 颜色
    brightness: int  # 0-100
    transition: int  # 过渡时间 ms
    pattern: Optional[str]  # breath/static/pulse

@dataclass
class AudioConfig:
    file: str  # 音频文件路径
    volume: int  # 0-100
    loop: bool
    fade_in: int  # 淡入时间 ms
    fade_out: int  # 淡出时间 ms

@dataclass
class VoiceGuideConfig:
    text: str  # 引导语文本
    voice: str  # 语音风格
    emotion: str  # 情感控制
    speed: float  # 语速 0.8-1.2

@dataclass
class Session:
    """疗愈会话"""
    id: str
    start_time: datetime
    end_time: Optional[datetime]
    initial_emotion: EmotionState
    final_emotion: Optional[EmotionState]
    emotion_history: List[EmotionState]
    plan_used: TherapyPlan
    adjustments: List[dict]  # 过程中的调整记录
    user_feedback: Optional[dict]

@dataclass
class VirtualCharacter:
    """虚拟角色"""
    id: str
    name: str
    age: int
    occupation: str
    personality: str
    story: str  # 背景故事
    healing_journey: List[dict]  # 疗愈旅程
    artworks: List[str]  # 作品列表
    current_emotion: EmotionCategory
```

### 数据库 Schema

```sql
-- 用户会话表
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    initial_emotion_category TEXT,
    initial_emotion_intensity REAL,
    final_emotion_category TEXT,
    final_emotion_intensity REAL,
    plan_id TEXT,
    duration_seconds INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 情绪历史表
CREATE TABLE emotion_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    category TEXT,
    intensity REAL,
    valence REAL,
    arousal REAL,
    audio_data TEXT,  -- JSON
    face_data TEXT,   -- JSON
    bio_data TEXT,    -- JSON
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- 疗愈方案表
CREATE TABLE therapy_plans (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    target_emotions TEXT,  -- JSON array
    intensity TEXT,
    style TEXT,
    duration INTEGER,
    phases TEXT,  -- JSON
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

-- 使用统计表
CREATE TABLE usage_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    total_sessions INTEGER DEFAULT 0,
    total_duration INTEGER DEFAULT 0,
    avg_improvement REAL,
    most_common_emotion TEXT,
    most_used_plan TEXT
);

-- 系统日志表
CREATE TABLE system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    level TEXT,
    module TEXT,
    message TEXT,
    details TEXT  -- JSON
);
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

基于需求分析，以下是系统需要满足的正确性属性：

### Property 1: 语音识别输出完整性

*For any* 有效的音频输入，SenseVoice 模型的输出 SHALL 包含文本内容、情感标签和音频事件检测结果三个字段，且所有字段不为空。

**Validates: Requirements 1.2**

### Property 2: 情绪分类范围约束

*For any* 音频输入，emotion2vec+ 模型输出的情绪类别 SHALL 属于预定义的 9 类情绪之一（angry, happy, neutral, sad, surprised, fearful, disgusted, anxious, tired）。

**Validates: Requirements 1.3**

### Property 3: 语音分析延迟约束

*For any* 长度不超过 60 秒的音频输入，情绪分析引擎 SHALL 在 500ms 内返回完整的分析结果。

**Validates: Requirements 1.5**

### Property 4: 面部关键点数量约束

*For any* 检测到人脸的图像帧，MediaPipe 输出的面部关键点数量 SHALL 等于 468。

**Validates: Requirements 2.2**

### Property 5: 表情分类范围约束

*For any* 检测到人脸的图像帧，表情分类器输出的表情类别 SHALL 属于预定义的 7 类基础表情之一。

**Validates: Requirements 2.3**

### Property 6: 面部分析帧率约束

*For any* 连续的视频流输入，面部分析模块 SHALL 以不低于 30fps 的帧率处理图像。

**Validates: Requirements 2.6**

### Property 7: HRV 计算有效性

*For any* 长度至少 60 秒的心率数据序列，HRV 分析模块 SHALL 输出有效的 RMSSD 和 SDNN 指标。

**Validates: Requirements 3.2**

### Property 8: 压力指数范围约束

*For any* 有效的心率数据输入，压力指数计算结果 SHALL 在 0-100 范围内。

**Validates: Requirements 3.3**

### Property 9: 多模态融合输出完整性

*For any* 多模态情绪数据输入，融合模块输出的 EmotionState SHALL 包含情绪类别、强度（0-1）、效价（-1 到 1）、唤醒度（0-1）四个字段。

**Validates: Requirements 4.2**

### Property 10: 模态冲突解决优先级

*For any* 存在模态冲突的情绪数据，融合模块 SHALL 按照生理信号 > 面部表情 > 语音的优先级采信结果。

**Validates: Requirements 4.3**

### Property 11: 单模态降级能力

*For any* 仅有单一模态可用的情况，情绪分析引擎 SHALL 仍能输出有效的 EmotionState。

**Validates: Requirements 4.5**

### Property 12: 疗愈方案匹配一致性

*For any* 相同的 EmotionState 输入，疗愈方案匹配器 SHALL 返回相同的 TherapyPlan（在配置不变的情况下）。

**Validates: Requirements 5.1**

### Property 13: 用户选择优先级

*For any* 用户主动选择的疗愈方案，系统 SHALL 执行用户选择的方案而非自动匹配的方案。

**Validates: Requirements 5.5**

### Property 14: 语音合成有效性

*For any* 有效的中文文本输入，CosyVoice 模型 SHALL 生成非空的音频数据。

**Validates: Requirements 6.2**

### Property 15: 情感控制语音差异性

*For any* 相同的文本输入，使用不同情感参数生成的语音 SHALL 在音频特征上存在可测量的差异。

**Validates: Requirements 6.3**

### Property 16: 灯光颜色转换正确性

*For any* 有效的 HEX 颜色值，灯光控制器 SHALL 正确转换为 RGB 值并发送到设备。

**Validates: Requirements 7.2**

### Property 17: 灯光过渡平滑性

*For any* 灯光状态切换，控制器 SHALL 使用配置的过渡时间进行渐变，而非瞬间切换。

**Validates: Requirements 7.3**

### Property 18: 焦虑情绪灯光映射

*For any* 检测到焦虑情绪的情况，灯光控制器 SHALL 选择蓝绿色系（色相在 150-210 度范围内）的灯光颜色。

**Validates: Requirements 7.5**

### Property 19: 实时监测持续性

*For any* 正在执行的疗愈方案，情绪监测 SHALL 以不低于每 10 秒一次的频率持续进行。

**Validates: Requirements 10.1**

### Property 20: 情绪无变化自动切换

*For any* 情绪状态在 3 分钟内无明显变化（变化幅度小于 0.1）的情况，系统 SHALL 自动切换到备选方案。

**Validates: Requirements 10.3**

### Property 21: 调整记录完整性

*For any* 疗愈过程中的方案调整，系统 SHALL 记录调整时间、原因和调整内容。

**Validates: Requirements 10.4**

### Property 22: 对话响应有效性

*For any* 用户发起的对话消息，Qwen3 模型 SHALL 在 5 秒内返回非空的响应文本。

**Validates: Requirements 11.1**

### Property 23: AI 身份声明

*For any* 对话会话的首次响应，系统 SHALL 在响应中包含 AI 助手身份声明。

**Validates: Requirements 11.4**

### Property 24: 虚拟角色匹配逻辑

*For any* 用户情绪状态，虚拟社区 SHALL 匹配情绪相似度最高或处于恢复阶段的虚拟角色。

**Validates: Requirements 12.3**

### Property 25: 轻互动限制

*For any* 虚拟社区互动，系统 SHALL 仅支持点赞和送花操作，不支持评论和私信。

**Validates: Requirements 12.5**

### Property 26: 疗愈报告生成完整性

*For any* 结束的疗愈会话，生成的报告 SHALL 包含初始情绪状态、情绪变化曲线、最终情绪状态和疗愈时长。

**Validates: Requirements 13.2**

### Property 27: 报告隐私保护

*For any* 生成的疗愈报告，报告内容 SHALL 不包含用户姓名、身份证号、手机号等可识别身份的信息。

**Validates: Requirements 13.6**

### Property 28: 本地数据存储

*For any* 用户数据写入操作，数据 SHALL 存储在本地 SQLite 数据库中，而非远程服务器。

**Validates: Requirements 14.1**

### Property 29: 数据加密有效性

*For any* 存储的敏感数据，系统 SHALL 使用 AES-256 算法进行加密，加密后的数据 SHALL 无法直接读取原文。

**Validates: Requirements 14.3**

### Property 30: 过期数据清理

*For any* 超过配置保留期限的数据，系统 SHALL 在下次清理任务执行时删除该数据。

**Validates: Requirements 14.5**

### Property 31: 管理后台权限控制

*For any* 未经授权的访问请求，管理后台 SHALL 拒绝访问并返回认证错误。

**Validates: Requirements 15.6**

### Property 32: 系统启动时间约束

*For any* 系统启动过程，所有 AI 模型 SHALL 在 60 秒内完成加载。

**Validates: Requirements 16.1**

### Property 33: 设备连接容错

*For any* 硬件设备连接失败的情况，系统 SHALL 记录错误日志并继续启动，不影响其他功能。

**Validates: Requirements 16.3**

### Property 34: 多语言支持

*For any* 用户界面文本，系统 SHALL 提供中文和英文两种语言版本。

**Validates: Requirements 17.6**

## Error Handling

### 错误分类与处理策略

| 错误类型 | 严重程度 | 处理策略 |
|----------|----------|----------|
| AI 模型加载失败 | Critical | 记录日志，显示错误界面，阻止启动 |
| 硬件设备连接失败 | Warning | 记录日志，降级运行，提示用户 |
| 语音识别失败 | Warning | 重试 3 次，失败后提示用户重新录音 |
| 情绪分析超时 | Warning | 使用默认情绪状态，继续执行 |
| 数据库写入失败 | Error | 重试，失败后缓存到内存，稍后重试 |
| 网络设备通信失败 | Warning | 重试，失败后跳过该设备 |

### 错误处理代码示例

```python
class ErrorHandler:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.retry_config = {
            "max_retries": 3,
            "retry_delay": 1.0,
            "exponential_backoff": True
        }
    
    async def with_retry(
        self, 
        func: Callable, 
        error_type: str,
        fallback: Any = None
    ) -> Any:
        """带重试的函数执行"""
        for attempt in range(self.retry_config["max_retries"]):
            try:
                return await func()
            except Exception as e:
                self.logger.warning(
                    f"{error_type} failed (attempt {attempt + 1}): {e}"
                )
                if attempt < self.retry_config["max_retries"] - 1:
                    delay = self.retry_config["retry_delay"]
                    if self.retry_config["exponential_backoff"]:
                        delay *= (2 ** attempt)
                    await asyncio.sleep(delay)
        
        self.logger.error(f"{error_type} failed after all retries")
        return fallback
    
    def handle_device_failure(self, device_name: str, error: Exception):
        """处理设备故障"""
        self.logger.error(f"Device {device_name} failed: {error}")
        # 发送告警通知
        # 切换到降级模式
        return DegradedMode(excluded_devices=[device_name])
```

### 降级模式

```python
class DegradedMode:
    """降级模式配置"""
    
    MODES = {
        "no_camera": {
            "description": "摄像头不可用，仅使用语音和生理信号",
            "emotion_weights": {"audio": 0.6, "face": 0, "bio": 0.4}
        },
        "no_bio": {
            "description": "心率设备不可用，仅使用语音和面部",
            "emotion_weights": {"audio": 0.5, "face": 0.5, "bio": 0}
        },
        "audio_only": {
            "description": "仅语音可用",
            "emotion_weights": {"audio": 1.0, "face": 0, "bio": 0}
        },
        "no_chair": {
            "description": "座椅不可用，跳过触觉反馈",
            "skip_devices": ["chair"]
        },
        "no_light": {
            "description": "灯光不可用，跳过灯光控制",
            "skip_devices": ["light"]
        }
    }
```

## Testing Strategy

### 测试框架选择

| 测试类型 | 框架 | 说明 |
|----------|------|------|
| 单元测试 | pytest | Python 标准测试框架 |
| 属性测试 | hypothesis | 基于属性的测试 |
| 集成测试 | pytest-asyncio | 异步测试支持 |
| E2E 测试 | playwright | UI 自动化测试 |
| 性能测试 | locust | 负载测试 |

### 单元测试策略

- 每个模块独立测试
- 使用 mock 隔离外部依赖（AI 模型、硬件设备）
- 覆盖正常路径和异常路径
- 测试边界条件

### 属性测试策略

- 使用 hypothesis 库进行属性测试
- 每个属性测试运行至少 100 次迭代
- 测试标签格式：`**Feature: healing-pod-system, Property {number}: {property_text}**`

```python
from hypothesis import given, strategies as st, settings

class TestEmotionEngine:
    
    @given(st.floats(min_value=0, max_value=1))
    @settings(max_examples=100)
    def test_emotion_intensity_range(self, intensity):
        """
        **Feature: healing-pod-system, Property 9: 多模态融合输出完整性**
        **Validates: Requirements 4.2**
        """
        emotion_state = EmotionState(
            category=EmotionCategory.NEUTRAL,
            intensity=intensity,
            valence=0,
            arousal=0.5,
            confidence=0.9,
            timestamp=datetime.now()
        )
        assert 0 <= emotion_state.intensity <= 1
    
    @given(st.integers(min_value=0, max_value=100))
    @settings(max_examples=100)
    def test_stress_index_range(self, stress):
        """
        **Feature: healing-pod-system, Property 8: 压力指数范围约束**
        **Validates: Requirements 3.3**
        """
        # 压力指数应在 0-100 范围内
        assert 0 <= stress <= 100
```

### 集成测试策略

- 测试模块间的交互
- 测试完整的疗愈流程
- 使用测试数据库和模拟设备

### 测试覆盖率目标

| 模块 | 目标覆盖率 |
|------|-----------|
| Emotion Engine | 90% |
| Therapy Engine | 85% |
| Device Controller | 80% |
| Data Layer | 90% |
| API Layer | 85% |

## API Reference

### REST API 端点

```yaml
# API 端点定义

/api/emotion:
  POST /analyze:
    description: 分析音频情绪
    request:
      audio: binary (wav/mp3)
      include_face: boolean
    response:
      emotion_state: EmotionState
      
  GET /history/{session_id}:
    description: 获取会话情绪历史
    response:
      emotions: List[EmotionState]

/api/therapy:
  POST /start:
    description: 开始疗愈会话
    request:
      plan_id: string (optional)
      user_prefs: object
    response:
      session_id: string
      plan: TherapyPlan
      
  POST /stop/{session_id}:
    description: 结束疗愈会话
    response:
      report: TherapyReport
      
  POST /adjust/{session_id}:
    description: 调整当前方案
    request:
      action: skip_phase | change_plan | pause | resume
    response:
      success: boolean

/api/device:
  GET /status:
    description: 获取所有设备状态
    response:
      devices: List[DeviceStatus]
      
  POST /control:
    description: 控制设备
    request:
      device: light | audio | chair | scent
      action: object
    response:
      success: boolean

/api/chat:
  POST /message:
    description: 发送对话消息
    request:
      message: string
      session_id: string
    response:
      reply: string
      audio: binary (optional)

/api/admin:
  GET /stats:
    description: 获取使用统计
    response:
      stats: UsageStats
      
  GET /logs:
    description: 获取系统日志
    query:
      level: info | warning | error
      limit: integer
    response:
      logs: List[LogEntry]
```
