# Requirements Document

## Introduction

智能疗愈仓系统是一个基于 Mac Mini 的沉浸式心理疗愈解决方案。系统通过多模态情绪分析（语音、面部表情、生理信号）实时感知用户情绪状态，并通过声光电等多感官刺激提供个性化的疗愈体验。系统采用国内最新开源 AI 模型（SenseVoice、emotion2vec+、Qwen3、CosyVoice 3.0），面向 B 端客户（学校、企业、医疗机构）提供专业的心理健康服务。

## Glossary

- **Healing_Pod**: 智能疗愈仓，包含硬件舱体和软件系统的完整解决方案
- **Emotion_Engine**: 情绪分析引擎，负责多模态情绪识别和融合
- **Therapy_Engine**: 疗愈引擎，负责匹配和执行疗愈方案
- **Device_Controller**: 设备控制器，负责控制灯光、音响、座椅等硬件设备
- **Session**: 一次完整的疗愈会话，从用户进入到离开
- **Therapy_Plan**: 疗愈方案，包含多个阶段的声光电配置
- **Emotion_State**: 情绪状态，包含情绪类别、强度、效价、唤醒度等维度
- **Virtual_Community**: AI 模拟社区，由虚拟角色组成，提供情感共鸣
- **SenseVoice**: 阿里达摩院开源的多语言语音理解模型
- **emotion2vec**: 阿里达摩院开源的语音情感识别基座模型
- **CosyVoice**: 阿里达摩院开源的语音合成模型
- **Qwen3**: 阿里开源的大语言模型

## Requirements

### Requirement 1: 语音情绪分析

**User Story:** As a 疗愈仓用户, I want 通过语音倾诉来表达我的情绪, so that 系统能够理解我的情绪状态并提供针对性的疗愈方案。

#### Acceptance Criteria

1. WHEN 用户开始语音输入 THEN THE Emotion_Engine SHALL 使用 SenseVoice 模型进行语音识别，准确率不低于 95%
2. WHEN 语音识别完成 THEN THE Emotion_Engine SHALL 同时输出文本内容、情感标签和音频事件检测结果
3. WHEN 需要细粒度情绪分析 THEN THE Emotion_Engine SHALL 使用 emotion2vec+ large 模型识别 9 类情绪（生气、开心、中立、难过、惊讶、恐惧、厌恶、焦虑、疲惫）
4. WHEN 检测到音频事件（哭泣、叹气、笑声） THEN THE Emotion_Engine SHALL 将事件类型纳入情绪状态评估
5. WHEN 语音输入结束 THEN THE Emotion_Engine SHALL 在 500ms 内返回完整的情绪分析结果
6. THE Emotion_Engine SHALL 支持中文、英文、粤语、日语、韩语的语音识别

### Requirement 2: 面部表情分析

**User Story:** As a 疗愈仓用户, I want 系统能够通过摄像头捕捉我的面部表情, so that 系统能够更准确地判断我的情绪状态。

#### Acceptance Criteria

1. WHEN 用户同意开启摄像头 THEN THE Emotion_Engine SHALL 使用 MediaPipe 进行实时人脸检测和关键点提取
2. WHEN 检测到人脸 THEN THE Emotion_Engine SHALL 提取 468 个面部关键点并进行表情分类
3. THE Emotion_Engine SHALL 识别至少 7 种基础表情（开心、难过、生气、惊讶、恐惧、厌恶、中立）
4. WHEN 进行面部分析 THEN THE Emotion_Engine SHALL 在本地完成所有处理，不上传任何图像数据
5. WHEN 用户拒绝开启摄像头 THEN THE Healing_Pod SHALL 仅使用语音和生理信号进行情绪分析
6. THE Emotion_Engine SHALL 以 30fps 的帧率进行实时表情分析

### Requirement 3: 生理信号分析

**User Story:** As a 疗愈仓用户, I want 系统能够监测我的心率等生理指标, so that 系统能够客观评估我的压力水平和放松程度。

#### Acceptance Criteria

1. WHEN 用户佩戴心率手环 THEN THE Emotion_Engine SHALL 通过蓝牙 BLE 协议实时接收心率数据
2. WHEN 收集到足够的心率数据（至少 60 秒） THEN THE Emotion_Engine SHALL 计算 HRV（心率变异性）指标
3. THE Emotion_Engine SHALL 基于 RMSSD 和 SDNN 指标计算压力指数（0-100）
4. WHEN 检测到心率异常（过高或过低） THEN THE Healing_Pod SHALL 发出提醒并建议用户休息
5. WHERE 用户选择佩戴脑电头环 THEN THE Emotion_Engine SHALL 采集 α 波和 β 波数据用于放松度评估

### Requirement 4: 多模态情绪融合

**User Story:** As a 系统管理员, I want 系统能够综合多种信号源进行情绪判断, so that 情绪识别结果更加准确可靠。

#### Acceptance Criteria

1. WHEN 多个模态的情绪数据可用 THEN THE Emotion_Engine SHALL 使用加权融合算法综合语音、面部、生理信号
2. THE Emotion_Engine SHALL 输出统一的 Emotion_State，包含情绪类别、强度（0-1）、效价（-1 到 1）、唤醒度（0-1）
3. WHEN 不同模态结果冲突 THEN THE Emotion_Engine SHALL 优先采信生理信号，其次是面部表情，最后是语音
4. THE Emotion_Engine SHALL 支持动态调整各模态的权重配置
5. WHEN 仅有单一模态可用 THEN THE Emotion_Engine SHALL 仍能输出有效的情绪状态评估

### Requirement 5: 疗愈方案匹配

**User Story:** As a 疗愈仓用户, I want 系统根据我的情绪状态自动选择合适的疗愈方案, so that 我能获得个性化的疗愈体验。

#### Acceptance Criteria

1. WHEN 情绪分析完成 THEN THE Therapy_Engine SHALL 根据 Emotion_State 匹配最合适的 Therapy_Plan
2. THE Therapy_Engine SHALL 支持至少 10 种预设疗愈方案，覆盖焦虑、低落、疲惫、压力等常见情绪问题
3. WHEN 匹配疗愈方案 THEN THE Therapy_Engine SHALL 考虑用户的历史偏好和疗愈效果记录
4. THE Therapy_Engine SHALL 支持中式风格（调息养神）和现代风格（正念冥想）两种疗愈风格
5. WHEN 用户主动选择疗愈方案 THEN THE Therapy_Engine SHALL 优先执行用户选择

### Requirement 6: 疗愈内容播放

**User Story:** As a 疗愈仓用户, I want 系统播放舒缓的音乐和引导语, so that 我能够放松身心。

#### Acceptance Criteria

1. WHEN 疗愈方案开始执行 THEN THE Therapy_Engine SHALL 按照方案配置播放背景音乐和语音引导
2. THE Therapy_Engine SHALL 使用 CosyVoice 3.0 模型生成自然流畅的中文引导语
3. WHEN 生成引导语 THEN THE Therapy_Engine SHALL 根据用户情绪状态调整语音的情感和语速
4. THE Therapy_Engine SHALL 支持环绕声音频输出，提供沉浸式听觉体验
5. WHEN 播放音频 THEN THE Device_Controller SHALL 确保音量平滑过渡，避免突兀变化
6. THE Therapy_Engine SHALL 支持至少 50 首背景音乐和 20 套引导语模板

### Requirement 7: 灯光控制

**User Story:** As a 疗愈仓用户, I want 舱内灯光能够配合疗愈过程变化, so that 我能获得更好的视觉放松体验。

#### Acceptance Criteria

1. WHEN 疗愈方案执行 THEN THE Device_Controller SHALL 根据方案配置控制灯光颜色和亮度
2. THE Device_Controller SHALL 支持 RGB 全彩灯光控制，色温范围 2700K-6500K
3. WHEN 切换灯光状态 THEN THE Device_Controller SHALL 使用渐变过渡，过渡时间可配置（默认 3 秒）
4. THE Device_Controller SHALL 支持呼吸灯模式，灯光节奏可与引导语的呼吸节奏同步
5. WHEN 检测到用户焦虑情绪 THEN THE Device_Controller SHALL 优先使用蓝绿色系的冷色调灯光
6. THE Device_Controller SHALL 通过 WiFi 协议控制智能灯带（支持 Yeelight 等主流品牌）

### Requirement 8: 视觉内容展示

**User Story:** As a 疗愈仓用户, I want 看到舒缓的视觉画面, so that 我能够更好地沉浸在疗愈环境中。

#### Acceptance Criteria

1. WHEN 疗愈方案执行 THEN THE Device_Controller SHALL 在屏幕或投影上展示配套的视觉内容
2. THE Therapy_Engine SHALL 提供至少 20 种视觉场景（自然风光、抽象动画、水墨山水等）
3. WHEN 展示视觉内容 THEN THE Device_Controller SHALL 支持 4K 分辨率输出
4. THE Device_Controller SHALL 支持视频循环播放和平滑切换
5. WHEN 用户闭眼休息 THEN THE Device_Controller SHALL 可选择降低屏幕亮度或关闭显示

### Requirement 9: 座椅控制

**User Story:** As a 疗愈仓用户, I want 座椅能够提供舒适的按摩和震动, so that 我的身体能够得到放松。

#### Acceptance Criteria

1. WHEN 疗愈方案执行 THEN THE Device_Controller SHALL 根据方案配置控制按摩座椅的模式和强度
2. THE Device_Controller SHALL 支持至少 5 种按摩模式（轻柔、舒缓、深度、波浪、脉冲）
3. THE Device_Controller SHALL 支持按摩强度调节（1-10 级）
4. WHEN 用户手动调节座椅 THEN THE Device_Controller SHALL 立即响应并记录用户偏好
5. THE Device_Controller SHALL 通过蓝牙协议与智能按摩座椅通信

### Requirement 10: 实时反馈调整

**User Story:** As a 疗愈仓用户, I want 系统能够根据我的实时状态调整疗愈方案, so that 疗愈效果能够最大化。

#### Acceptance Criteria

1. WHILE 疗愈方案执行中 THE Emotion_Engine SHALL 持续监测用户的情绪和生理状态
2. WHEN 检测到用户情绪明显改善 THEN THE Therapy_Engine SHALL 可选择进入下一阶段或延长当前阶段
3. WHEN 检测到用户情绪恶化或无变化超过 3 分钟 THEN THE Therapy_Engine SHALL 自动切换到备选方案
4. THE Therapy_Engine SHALL 记录每次调整的原因和效果，用于优化算法
5. WHEN 用户主动请求调整 THEN THE Therapy_Engine SHALL 立即响应用户指令

### Requirement 11: AI 对话陪伴

**User Story:** As a 疗愈仓用户, I want 能够与 AI 进行对话倾诉, so that 我能够表达内心的想法并获得情感支持。

#### Acceptance Criteria

1. WHEN 用户发起对话 THEN THE Healing_Pod SHALL 使用 Qwen3-8B 模型进行自然语言对话
2. THE Healing_Pod SHALL 以温暖、共情、非评判的方式回应用户
3. WHEN 用户表达负面情绪 THEN THE Healing_Pod SHALL 提供情感支持和积极引导，但不提供专业心理治疗建议
4. THE Healing_Pod SHALL 在对话中明确说明自己是 AI 助手，不能替代专业心理咨询
5. WHEN 检测到用户可能存在严重心理问题 THEN THE Healing_Pod SHALL 建议用户寻求专业帮助并提供求助热线
6. THE Healing_Pod SHALL 使用 CosyVoice 3.0 将对话内容转换为语音输出

### Requirement 12: 虚拟社区互动

**User Story:** As a 疗愈仓用户, I want 看到其他人的疗愈故事和作品, so that 我能感受到共鸣和支持，但不需要真实社交。

#### Acceptance Criteria

1. WHEN 用户完成创作任务 THEN THE Virtual_Community SHALL 展示 AI 生成的虚拟角色及其作品
2. THE Virtual_Community SHALL 包含至少 30 个预设虚拟角色，具有不同的人设和故事线
3. WHEN 匹配虚拟角色 THEN THE Virtual_Community SHALL 根据用户情绪状态选择情绪相似或正在恢复中的角色
4. THE Virtual_Community SHALL 展示虚拟角色的"疗愈旅程"，让用户看到改变是可能的
5. THE Virtual_Community SHALL 仅支持点赞/送花等轻互动，不支持评论和私信
6. THE Virtual_Community SHALL 所有内容均为 AI 生成，不涉及真实用户数据

### Requirement 13: 疗愈报告生成

**User Story:** As a 疗愈仓用户, I want 在疗愈结束后获得一份报告, so that 我能了解自己的情绪变化和疗愈效果。

#### Acceptance Criteria

1. WHEN 疗愈会话结束 THEN THE Healing_Pod SHALL 生成一份疗愈报告
2. THE 疗愈报告 SHALL 包含：初始情绪状态、疗愈过程中的情绪变化曲线、最终情绪状态、疗愈时长
3. THE 疗愈报告 SHALL 提供简短的文字总结和建议
4. WHEN 用户同意 THEN THE Healing_Pod SHALL 将报告保存到本地数据库
5. THE Healing_Pod SHALL 支持将报告导出为 PDF 格式
6. THE 疗愈报告 SHALL 不包含任何可识别用户身份的敏感信息

### Requirement 14: 本地数据管理

**User Story:** As a 系统管理员, I want 所有用户数据都存储在本地, so that 用户隐私得到保护且系统可离线运行。

#### Acceptance Criteria

1. THE Healing_Pod SHALL 将所有用户数据存储在本地 SQLite 数据库中
2. THE Healing_Pod SHALL 不向任何外部服务器传输用户的语音、图像或生理数据
3. THE Healing_Pod SHALL 支持数据加密存储，使用 AES-256 加密算法
4. WHEN 管理员请求 THEN THE Healing_Pod SHALL 支持数据导出和备份功能
5. THE Healing_Pod SHALL 支持配置数据保留期限，自动清理过期数据
6. THE Healing_Pod SHALL 在完全离线环境下正常运行所有核心功能

### Requirement 15: 管理后台

**User Story:** As a 系统管理员, I want 通过管理界面配置和监控系统, so that 我能够维护系统正常运行。

#### Acceptance Criteria

1. THE Healing_Pod SHALL 提供本地 Web 管理界面，可通过浏览器访问
2. THE 管理后台 SHALL 支持查看设备状态、使用统计、疗愈效果分析
3. THE 管理后台 SHALL 支持配置疗愈方案、调整设备参数、管理内容库
4. THE 管理后台 SHALL 支持用户管理（如果启用用户账号功能）
5. THE 管理后台 SHALL 支持系统日志查看和故障诊断
6. THE 管理后台 SHALL 需要管理员密码登录，支持权限分级

### Requirement 16: 系统启动与初始化

**User Story:** As a 系统管理员, I want 系统能够快速启动并自动检测硬件, so that 疗愈仓能够随时投入使用。

#### Acceptance Criteria

1. WHEN 系统启动 THEN THE Healing_Pod SHALL 在 60 秒内完成所有 AI 模型加载
2. WHEN 系统启动 THEN THE Device_Controller SHALL 自动检测并连接所有配置的硬件设备
3. IF 某个硬件设备连接失败 THEN THE Healing_Pod SHALL 记录错误日志并继续启动，使用降级模式运行
4. WHEN 所有组件就绪 THEN THE Healing_Pod SHALL 显示欢迎界面，等待用户开始疗愈
5. THE Healing_Pod SHALL 支持开机自启动，无需人工干预

### Requirement 17: 用户界面

**User Story:** As a 疗愈仓用户, I want 操作界面简洁直观, so that 我能够轻松开始和控制疗愈过程。

#### Acceptance Criteria

1. THE Healing_Pod SHALL 提供触摸屏友好的用户界面
2. THE 用户界面 SHALL 包含：欢迎页、情绪评估页、疗愈进行页、报告页
3. WHEN 用户进入疗愈仓 THEN THE Healing_Pod SHALL 显示简洁的欢迎界面和开始按钮
4. WHILE 疗愈进行中 THE 用户界面 SHALL 显示当前阶段、剩余时间和简单的控制按钮（暂停/跳过/结束）
5. THE 用户界面 SHALL 使用舒缓的配色方案，避免刺眼的颜色和复杂的动画
6. THE 用户界面 SHALL 支持中文和英文两种语言
