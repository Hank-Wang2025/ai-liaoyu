"""
Qwen3 对话模块
Qwen3 Dialog Module

使用阿里 Qwen3-8B 模型进行 AI 对话陪伴
支持温暖、共情、非评判的对话风格
"""
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class DialogRole(str, Enum):
    """对话角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class DialogMessage:
    """对话消息"""
    role: DialogRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, str]:
        """转换为字典格式"""
        return {"role": self.role.value, "content": self.content}


@dataclass
class DialogResponse:
    """对话响应"""
    content: str
    is_first_response: bool = False
    contains_ai_disclosure: bool = False
    contains_crisis_warning: bool = False
    crisis_resources: Optional[List[str]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    generation_time_ms: int = 0


class CrisisKeywordDetector:
    """
    危机关键词检测器
    
    检测用户消息中可能表明严重心理问题的关键词
    """
    
    # 危机关键词列表（中文）
    CRISIS_KEYWORDS_ZH = [
        # 自杀相关
        "自杀", "不想活", "想死", "结束生命", "活着没意思", "了结", "轻生",
        "跳楼", "割腕", "服药自杀", "上吊", "寻死",
        # 自伤相关
        "自残", "伤害自己", "割自己", "打自己",
        # 绝望表达
        "活不下去", "没有希望", "绝望", "生无可恋", "人间不值得",
        "没人在乎", "世界没有我会更好", "是个累赘", "拖累",
        # 告别相关
        "最后一次", "永别", "遗书", "后事"
    ]
    
    # 危机关键词列表（英文）
    CRISIS_KEYWORDS_EN = [
        "suicide", "kill myself", "end my life", "want to die",
        "self-harm", "hurt myself", "cutting",
        "hopeless", "no reason to live", "better off dead",
        "goodbye forever", "final goodbye", "last message"
    ]
    
    # 心理援助热线
    CRISIS_RESOURCES = [
        "全国心理援助热线：400-161-9995",
        "北京心理危机研究与干预中心：010-82951332",
        "生命热线：400-821-1215",
        "希望24热线：400-161-9995"
    ]
    
    @classmethod
    def detect_crisis(cls, text: str) -> tuple[bool, List[str]]:
        """
        检测文本中是否包含危机关键词
        
        Args:
            text: 用户输入文本
            
        Returns:
            (是否检测到危机, 匹配到的关键词列表)
        """
        text_lower = text.lower()
        matched_keywords = []
        
        # 检查中文关键词
        for keyword in cls.CRISIS_KEYWORDS_ZH:
            if keyword in text:
                matched_keywords.append(keyword)
        
        # 检查英文关键词
        for keyword in cls.CRISIS_KEYWORDS_EN:
            if keyword in text_lower:
                matched_keywords.append(keyword)
        
        return len(matched_keywords) > 0, matched_keywords
    
    @classmethod
    def get_crisis_resources(cls) -> List[str]:
        """获取心理援助资源列表"""
        return cls.CRISIS_RESOURCES.copy()


class QwenDialogEngine:
    """
    Qwen3 对话引擎
    
    功能:
    - 温暖、共情、非评判的对话
    - AI 身份声明
    - 危机干预检测
    - 对话历史管理
    """
    
    # 系统提示词 - 温暖、共情、非评判
    SYSTEM_PROMPT = """你是一个温暖、有同理心的疗愈助手。你的任务是：

1. 倾听用户的倾诉，给予情感支持
2. 使用温和、非评判的语言回应
3. 适时提供积极的引导和建议
4. 明确说明你是 AI 助手，不能替代专业心理咨询
5. 如果检测到严重心理问题，建议用户寻求专业帮助

重要原则：
- 不要提供具体的心理治疗建议，只提供情感支持
- 不要评判用户的感受或行为
- 使用"我理解"、"我听到了"等共情表达
- 保持温暖但不过度热情
- 尊重用户的感受和节奏

回应风格：
- 简洁但有温度
- 避免说教或给建议
- 多用开放式问题引导用户表达
- 适当使用停顿和沉默的空间"""

    # AI 身份声明模板
    AI_DISCLOSURE = """我是一个 AI 疗愈助手，很高兴能陪伴你。我会认真倾听你想说的话，但请记住，我不能替代专业的心理咨询师。如果你感到需要专业帮助，我建议你联系专业的心理健康服务。"""
    
    # 危机干预响应模板
    CRISIS_RESPONSE = """我注意到你说的话让我有些担心。你的感受很重要，我想让你知道，有专业的人可以帮助你度过这个困难时期。

请考虑联系以下心理援助热线：
{resources}

如果你现在处于紧急情况，请立即拨打 120 或前往最近的医院急诊。

我会继续在这里陪伴你，但专业的帮助可能会更有效。你愿意告诉我更多关于你现在的感受吗？"""

    # 默认模型路径
    DEFAULT_MODEL = "Qwen/Qwen3-8B"
    
    def __init__(
        self,
        model_path: str = None,
        device: str = "cpu",
        max_history: int = 20
    ):
        """
        初始化 Qwen3 对话引擎
        
        Args:
            model_path: 模型路径
            device: 运行设备 ("cpu", "cuda", "mps")
            max_history: 最大对话历史长度
        """
        self.model_path = model_path or self.DEFAULT_MODEL
        self.device = device
        self.max_history = max_history
        
        self.model = None
        self.tokenizer = None
        self._initialized = False
        
        # 对话历史
        self._history: List[DialogMessage] = []
        self._is_first_response = True
        
        # 危机检测器
        self.crisis_detector = CrisisKeywordDetector()
        
        logger.info(f"QwenDialogEngine created with model: {self.model_path}")
    
    def initialize(self) -> bool:
        """
        初始化模型
        
        Returns:
            是否初始化成功
        """
        if self._initialized:
            return True
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            logger.info(f"Loading Qwen3 model from {self.model_path}...")
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )
            
            # 根据设备选择数据类型
            if self.device == "mps":
                dtype = torch.float16
                device_map = "mps"
            elif self.device == "cuda":
                dtype = torch.float16
                device_map = "auto"
            else:
                dtype = torch.float32
                device_map = "cpu"
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=dtype,
                device_map=device_map,
                trust_remote_code=True
            )
            
            self._initialized = True
            logger.info(f"Qwen3 model initialized successfully on {self.device}")
            return True
            
        except ImportError as e:
            logger.error(f"transformers not installed: {e}")
            logger.info("Please install: pip install transformers torch")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Qwen3 model: {e}")
            return False
    
    def is_initialized(self) -> bool:
        """检查模型是否已初始化"""
        return self._initialized
    
    def _build_messages(self, user_message: str) -> List[Dict[str, str]]:
        """
        构建对话消息列表
        
        Args:
            user_message: 用户消息
            
        Returns:
            消息列表
        """
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        
        # 添加历史消息
        for msg in self._history[-self.max_history:]:
            messages.append(msg.to_dict())
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def _add_ai_disclosure(self, response: str) -> str:
        """
        在首次响应中添加 AI 身份声明
        
        Args:
            response: 原始响应
            
        Returns:
            添加声明后的响应
        """
        if self._is_first_response:
            return f"{self.AI_DISCLOSURE}\n\n{response}"
        return response
    
    def _generate_crisis_response(self, matched_keywords: List[str]) -> str:
        """
        生成危机干预响应
        
        Args:
            matched_keywords: 匹配到的危机关键词
            
        Returns:
            危机干预响应文本
        """
        resources = "\n".join(f"• {r}" for r in self.crisis_detector.get_crisis_resources())
        return self.CRISIS_RESPONSE.format(resources=resources)
    
    async def chat(
        self,
        message: str,
        check_crisis: bool = True
    ) -> DialogResponse:
        """
        进行对话
        
        Args:
            message: 用户消息
            check_crisis: 是否检查危机关键词
            
        Returns:
            DialogResponse 对话响应
        """
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("Qwen3 model not initialized")
        
        start_time = datetime.now()
        
        # 检测危机关键词
        is_crisis = False
        crisis_resources = None
        if check_crisis:
            is_crisis, matched_keywords = self.crisis_detector.detect_crisis(message)
            if is_crisis:
                logger.warning(f"Crisis keywords detected: {matched_keywords}")
                crisis_resources = self.crisis_detector.get_crisis_resources()
        
        try:
            # 构建消息
            messages = self._build_messages(message)
            
            # 生成响应
            inputs = self.tokenizer.apply_chat_template(
                messages,
                return_tensors="pt",
                add_generation_prompt=True
            )
            
            if self.device != "cpu":
                inputs = inputs.to(self.device)
            
            outputs = self.model.generate(
                inputs,
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            # 解码响应
            response_text = self.tokenizer.decode(
                outputs[0][inputs.shape[1]:],
                skip_special_tokens=True
            )
            
            # 如果检测到危机，添加危机干预响应
            if is_crisis:
                crisis_response = self._generate_crisis_response(matched_keywords)
                response_text = f"{crisis_response}\n\n---\n\n{response_text}"
            
            # 添加 AI 身份声明（首次响应）
            is_first = self._is_first_response
            if is_first:
                response_text = self._add_ai_disclosure(response_text)
                self._is_first_response = False
            
            # 更新历史
            self._history.append(DialogMessage(
                role=DialogRole.USER,
                content=message
            ))
            self._history.append(DialogMessage(
                role=DialogRole.ASSISTANT,
                content=response_text
            ))
            
            # 计算生成时间
            generation_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return DialogResponse(
                content=response_text,
                is_first_response=is_first,
                contains_ai_disclosure=is_first,
                contains_crisis_warning=is_crisis,
                crisis_resources=crisis_resources,
                generation_time_ms=int(generation_time)
            )
            
        except Exception as e:
            logger.error(f"Qwen3 chat failed: {e}")
            raise
    
    def clear_history(self):
        """清除对话历史"""
        self._history.clear()
        self._is_first_response = True
        logger.info("Dialog history cleared")
    
    def get_history(self) -> List[DialogMessage]:
        """获取对话历史"""
        return self._history.copy()
    
    def reset_session(self):
        """重置会话（清除历史并重置首次响应标志）"""
        self.clear_history()
        logger.info("Dialog session reset")
    
    def cleanup(self):
        """清理资源"""
        if self.model is not None:
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        self._initialized = False
        self.clear_history()
        logger.info("QwenDialogEngine cleaned up")


class MockQwenDialogEngine:
    """
    Mock Qwen3 对话引擎
    
    用于测试和开发环境，当 Qwen3 模型未安装时使用
    """
    
    # 预设响应模板
    MOCK_RESPONSES = [
        "我听到了你说的话，这些感受一定很不容易。你愿意多告诉我一些吗？",
        "谢谢你愿意和我分享这些。我能感受到这对你来说很重要。",
        "我理解你现在的感受。有时候，能够说出来本身就是一种勇气。",
        "你的感受是完全可以理解的。在这种情况下，很多人都会有类似的感受。",
        "我在这里陪着你。你不需要急着做什么，我们可以慢慢来。"
    ]
    
    def __init__(
        self,
        model_path: str = None,
        device: str = "cpu",
        max_history: int = 20
    ):
        self.model_path = model_path or "mock_model"
        self.device = device
        self.max_history = max_history
        self._initialized = False
        self._history: List[DialogMessage] = []
        self._is_first_response = True
        self._response_index = 0
        self.crisis_detector = CrisisKeywordDetector()
        
        logger.info("MockQwenDialogEngine created (for testing)")
    
    def initialize(self) -> bool:
        """初始化 Mock 模型"""
        self._initialized = True
        logger.info("MockQwenDialogEngine initialized")
        return True
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    async def chat(
        self,
        message: str,
        check_crisis: bool = True
    ) -> DialogResponse:
        """Mock 对话"""
        if not self._initialized:
            self.initialize()
        
        start_time = datetime.now()
        
        # 检测危机关键词
        is_crisis = False
        crisis_resources = None
        if check_crisis:
            is_crisis, matched_keywords = self.crisis_detector.detect_crisis(message)
            if is_crisis:
                crisis_resources = self.crisis_detector.get_crisis_resources()
        
        # 选择响应
        response_text = self.MOCK_RESPONSES[self._response_index % len(self.MOCK_RESPONSES)]
        self._response_index += 1
        
        # 如果检测到危机，添加危机干预响应
        if is_crisis:
            resources = "\n".join(f"• {r}" for r in crisis_resources)
            crisis_response = f"""我注意到你说的话让我有些担心。你的感受很重要，我想让你知道，有专业的人可以帮助你度过这个困难时期。

请考虑联系以下心理援助热线：
{resources}

如果你现在处于紧急情况，请立即拨打 120 或前往最近的医院急诊。"""
            response_text = f"{crisis_response}\n\n---\n\n{response_text}"
        
        # 添加 AI 身份声明（首次响应）
        is_first = self._is_first_response
        if is_first:
            ai_disclosure = """我是一个 AI 疗愈助手，很高兴能陪伴你。我会认真倾听你想说的话，但请记住，我不能替代专业的心理咨询师。如果你感到需要专业帮助，我建议你联系专业的心理健康服务。"""
            response_text = f"{ai_disclosure}\n\n{response_text}"
            self._is_first_response = False
        
        # 更新历史
        self._history.append(DialogMessage(
            role=DialogRole.USER,
            content=message
        ))
        self._history.append(DialogMessage(
            role=DialogRole.ASSISTANT,
            content=response_text
        ))
        
        # 模拟生成时间
        generation_time = (datetime.now() - start_time).total_seconds() * 1000 + 100
        
        return DialogResponse(
            content=response_text,
            is_first_response=is_first,
            contains_ai_disclosure=is_first,
            contains_crisis_warning=is_crisis,
            crisis_resources=crisis_resources,
            generation_time_ms=int(generation_time)
        )
    
    def clear_history(self):
        """清除对话历史"""
        self._history.clear()
        self._is_first_response = True
    
    def get_history(self) -> List[DialogMessage]:
        """获取对话历史"""
        return self._history.copy()
    
    def reset_session(self):
        """重置会话"""
        self.clear_history()
    
    def cleanup(self):
        """清理资源"""
        self._initialized = False
        self.clear_history()
        logger.info("MockQwenDialogEngine cleaned up")


def create_dialog_engine(
    model_path: str = None,
    device: str = "cpu",
    max_history: int = 20,
    use_mock: bool = False
) -> QwenDialogEngine | MockQwenDialogEngine:
    """
    创建对话引擎实例
    
    Args:
        model_path: 模型路径
        device: 运行设备
        max_history: 最大对话历史长度
        use_mock: 是否使用 Mock 实现
        
    Returns:
        对话引擎实例
    """
    if use_mock:
        return MockQwenDialogEngine(model_path, device, max_history)
    
    # 尝试创建真实的引擎
    try:
        engine = QwenDialogEngine(model_path, device, max_history)
        if engine.initialize():
            return engine
        else:
            logger.warning("Qwen3 initialization failed, using mock engine")
            return MockQwenDialogEngine(model_path, device, max_history)
    except Exception as e:
        logger.warning(f"Failed to create Qwen3 engine: {e}, using mock")
        return MockQwenDialogEngine(model_path, device, max_history)
