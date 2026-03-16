"""
表情分类模块
Expression Classification Module

使用预训练 CNN 模型进行 7 类基础表情识别
支持 FER2013 等标准表情数据集训练的模型
"""
import os
from typing import Optional, Dict, List, Tuple, Any
from loguru import logger
import numpy as np

from models.emotion import FacialExpression


class ExpressionClassifier:
    """
    表情分类器
    
    功能:
    - 7 类基础表情识别 (happy, sad, angry, fearful, surprised, disgusted, neutral)
    - 置信度计算
    - 支持多种预训练模型格式
    
    Requirements: 2.3
    """
    
    # 7 类基础表情标签 (FER2013 标准)
    EXPRESSION_LABELS = [
        "angry",      # 0
        "disgusted",  # 1
        "fearful",    # 2
        "happy",      # 3
        "sad",        # 4
        "surprised",  # 5
        "neutral"     # 6
    ]
    
    # 表情到 FacialExpression 枚举的映射
    EXPRESSION_MAP = {
        "angry": FacialExpression.ANGRY,
        "disgusted": FacialExpression.DISGUSTED,
        "fearful": FacialExpression.FEARFUL,
        "happy": FacialExpression.HAPPY,
        "sad": FacialExpression.SAD,
        "surprised": FacialExpression.SURPRISED,
        "neutral": FacialExpression.NEUTRAL
    }
    
    # 默认输入尺寸 (FER2013 标准)
    DEFAULT_INPUT_SIZE = (48, 48)
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        input_size: Tuple[int, int] = DEFAULT_INPUT_SIZE,
        use_gpu: bool = False
    ):
        """
        初始化表情分类器
        
        Args:
            model_path: 预训练模型路径 (支持 .h5, .onnx, .pt 格式)
            input_size: 输入图像尺寸 (height, width)
            use_gpu: 是否使用 GPU 加速
        """
        self.model_path = model_path
        self.input_size = input_size
        self.use_gpu = use_gpu
        
        self.model = None
        self.model_type = None  # 'keras', 'onnx', 'pytorch', 'rule_based'
        self._initialized = False
        
        logger.info(f"ExpressionClassifier created with input size: {input_size}")
    
    def initialize(self) -> bool:
        """
        初始化分类器
        
        如果提供了模型路径，加载预训练模型
        否则使用基于规则的分类方法
        
        Returns:
            是否初始化成功
        """
        if self._initialized:
            return True
        
        if self.model_path and os.path.exists(self.model_path):
            return self._load_model(self.model_path)
        else:
            # 使用基于规则的分类方法
            self.model_type = 'rule_based'
            self._initialized = True
            logger.info("ExpressionClassifier initialized with rule-based classification")
            return True
    
    def _load_model(self, model_path: str) -> bool:
        """
        加载预训练模型
        
        Args:
            model_path: 模型文件路径
            
        Returns:
            是否加载成功
        """
        ext = os.path.splitext(model_path)[1].lower()
        
        try:
            if ext == '.h5':
                return self._load_keras_model(model_path)
            elif ext == '.onnx':
                return self._load_onnx_model(model_path)
            elif ext in ['.pt', '.pth']:
                return self._load_pytorch_model(model_path)
            else:
                logger.warning(f"Unsupported model format: {ext}, using rule-based classification")
                self.model_type = 'rule_based'
                self._initialized = True
                return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            logger.info("Falling back to rule-based classification")
            self.model_type = 'rule_based'
            self._initialized = True
            return True
    
    def _load_keras_model(self, model_path: str) -> bool:
        """加载 Keras/TensorFlow 模型"""
        try:
            import tensorflow as tf
            self.model = tf.keras.models.load_model(model_path)
            self.model_type = 'keras'
            self._initialized = True
            logger.info(f"Keras model loaded from {model_path}")
            return True
        except ImportError:
            logger.warning("TensorFlow not installed, cannot load Keras model")
            return False
        except Exception as e:
            logger.error(f"Failed to load Keras model: {e}")
            return False
    
    def _load_onnx_model(self, model_path: str) -> bool:
        """加载 ONNX 模型"""
        try:
            import onnxruntime as ort
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if self.use_gpu else ['CPUExecutionProvider']
            self.model = ort.InferenceSession(model_path, providers=providers)
            self.model_type = 'onnx'
            self._initialized = True
            logger.info(f"ONNX model loaded from {model_path}")
            return True
        except ImportError:
            logger.warning("onnxruntime not installed, cannot load ONNX model")
            return False
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
            return False
    
    def _load_pytorch_model(self, model_path: str) -> bool:
        """加载 PyTorch 模型"""
        try:
            import torch
            device = 'cuda' if self.use_gpu and torch.cuda.is_available() else 'cpu'
            self.model = torch.load(model_path, map_location=device)
            self.model.eval()
            self.model_type = 'pytorch'
            self._initialized = True
            logger.info(f"PyTorch model loaded from {model_path}")
            return True
        except ImportError:
            logger.warning("PyTorch not installed, cannot load PyTorch model")
            return False
        except Exception as e:
            logger.error(f"Failed to load PyTorch model: {e}")
            return False
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    def classify(
        self, 
        face_image: np.ndarray,
        landmarks: Optional[List[Tuple[float, float, float]]] = None
    ) -> Tuple[FacialExpression, float, Dict[str, float]]:
        """
        分类面部表情
        
        Args:
            face_image: 面部图像 (BGR 或灰度图)
            landmarks: 可选的面部关键点 (用于规则分类)
            
        Returns:
            (表情类别, 置信度, 各表情分数)
        """
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("ExpressionClassifier not initialized")
        
        if self.model_type == 'rule_based':
            return self._classify_rule_based(face_image, landmarks)
        elif self.model_type == 'keras':
            return self._classify_keras(face_image)
        elif self.model_type == 'onnx':
            return self._classify_onnx(face_image)
        elif self.model_type == 'pytorch':
            return self._classify_pytorch(face_image)
        else:
            return self._classify_rule_based(face_image, landmarks)
    
    def _preprocess_image(self, face_image: np.ndarray) -> np.ndarray:
        """
        预处理图像用于模型输入
        
        Args:
            face_image: 原始面部图像
            
        Returns:
            预处理后的图像
        """
        import cv2
        
        # 转换为灰度图
        if len(face_image.shape) == 3:
            gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_image
        
        # 调整尺寸
        resized = cv2.resize(gray, self.input_size)
        
        # 归一化到 [0, 1]
        normalized = resized.astype(np.float32) / 255.0
        
        return normalized
    
    def _classify_keras(self, face_image: np.ndarray) -> Tuple[FacialExpression, float, Dict[str, float]]:
        """使用 Keras 模型分类"""
        preprocessed = self._preprocess_image(face_image)
        
        # 添加 batch 和 channel 维度
        input_data = preprocessed.reshape(1, *self.input_size, 1)
        
        # 预测
        predictions = self.model.predict(input_data, verbose=0)[0]
        
        return self._parse_predictions(predictions)
    
    def _classify_onnx(self, face_image: np.ndarray) -> Tuple[FacialExpression, float, Dict[str, float]]:
        """使用 ONNX 模型分类"""
        preprocessed = self._preprocess_image(face_image)
        
        # 获取输入名称和形状
        input_name = self.model.get_inputs()[0].name
        input_shape = self.model.get_inputs()[0].shape
        
        # 调整输入形状
        if len(input_shape) == 4:
            input_data = preprocessed.reshape(1, 1, *self.input_size)
        else:
            input_data = preprocessed.reshape(1, *self.input_size)
        
        # 预测
        predictions = self.model.run(None, {input_name: input_data})[0][0]
        
        return self._parse_predictions(predictions)
    
    def _classify_pytorch(self, face_image: np.ndarray) -> Tuple[FacialExpression, float, Dict[str, float]]:
        """使用 PyTorch 模型分类"""
        import torch
        
        preprocessed = self._preprocess_image(face_image)
        
        # 转换为 tensor
        input_tensor = torch.from_numpy(preprocessed).unsqueeze(0).unsqueeze(0)
        
        # 预测
        with torch.no_grad():
            output = self.model(input_tensor)
            predictions = torch.softmax(output, dim=1).numpy()[0]
        
        return self._parse_predictions(predictions)
    
    def _classify_rule_based(
        self, 
        face_image: np.ndarray,
        landmarks: Optional[List[Tuple[float, float, float]]] = None
    ) -> Tuple[FacialExpression, float, Dict[str, float]]:
        """
        基于规则的表情分类
        
        使用图像特征和关键点几何特征进行分类
        
        Args:
            face_image: 面部图像
            landmarks: 面部关键点
            
        Returns:
            (表情类别, 置信度, 各表情分数)
        """
        scores = {label: 0.0 for label in self.EXPRESSION_LABELS}
        
        # 如果有关键点，使用几何特征
        if landmarks and len(landmarks) >= 468:
            scores = self._calculate_geometric_scores(landmarks)
        else:
            # 使用图像特征
            scores = self._calculate_image_scores(face_image)
        
        return self._parse_predictions(list(scores.values()))
    
    def _calculate_geometric_scores(
        self, 
        landmarks: List[Tuple[float, float, float]]
    ) -> Dict[str, float]:
        """
        基于关键点几何特征计算表情分数
        
        Args:
            landmarks: 468 个面部关键点
            
        Returns:
            各表情的分数
        """
        scores = {label: 0.1 for label in self.EXPRESSION_LABELS}
        
        # 提取关键特征点
        # 眼睛
        left_eye_top = landmarks[159][1]
        left_eye_bottom = landmarks[145][1]
        left_eye_width = landmarks[133][0] - landmarks[33][0]
        
        right_eye_top = landmarks[386][1]
        right_eye_bottom = landmarks[374][1]
        right_eye_width = landmarks[263][0] - landmarks[362][0]
        
        # 眼睛开合度
        left_ear = (left_eye_bottom - left_eye_top) / max(left_eye_width, 1)
        right_ear = (right_eye_bottom - right_eye_top) / max(right_eye_width, 1)
        eye_aspect_ratio = (left_ear + right_ear) / 2
        
        # 眉毛
        left_brow = landmarks[105][1]
        right_brow = landmarks[334][1]
        brow_height = ((left_eye_top - left_brow) + (right_eye_top - right_brow)) / 2
        
        # 嘴巴
        mouth_top = landmarks[13][1]
        mouth_bottom = landmarks[14][1]
        mouth_left = landmarks[61][0]
        mouth_right = landmarks[291][0]
        mouth_height = mouth_bottom - mouth_top
        mouth_width = mouth_right - mouth_left
        mouth_aspect_ratio = mouth_height / max(mouth_width, 1)
        
        # 嘴角
        mouth_center_y = (mouth_top + mouth_bottom) / 2
        left_corner_y = landmarks[61][1]
        right_corner_y = landmarks[291][1]
        corner_lift = mouth_center_y - (left_corner_y + right_corner_y) / 2
        
        # 基于特征计算分数
        # Happy: 嘴角上扬，嘴巴张开
        if corner_lift > 3:
            scores['happy'] = min(0.3 + corner_lift * 0.03 + mouth_aspect_ratio * 0.3, 0.95)
        
        # Sad: 嘴角下垂
        if corner_lift < -2:
            scores['sad'] = min(0.3 + abs(corner_lift) * 0.04, 0.9)
        
        # Angry: 眉毛下压
        if brow_height < 12:
            scores['angry'] = min(0.3 + (15 - brow_height) * 0.05, 0.9)
        
        # Surprised: 眼睛睁大，嘴巴张开，眉毛上扬
        if eye_aspect_ratio > 0.35 and mouth_aspect_ratio > 0.25 and brow_height > 20:
            scores['surprised'] = min(0.3 + eye_aspect_ratio * 0.4 + mouth_aspect_ratio * 0.3, 0.95)
        
        # Fearful: 眼睛睁大，眉毛上扬
        if eye_aspect_ratio > 0.32 and brow_height > 18:
            scores['fearful'] = min(0.2 + eye_aspect_ratio * 0.3, 0.85)
        
        # Disgusted: 鼻子皱起区域特征
        if mouth_aspect_ratio < 0.12 and corner_lift < 0:
            scores['disgusted'] = min(0.2 + abs(corner_lift) * 0.02, 0.75)
        
        # Neutral: 默认分数
        scores['neutral'] = 0.25
        
        # 确保所有分数非负（随机关键点可能导致负值）
        scores = {k: max(v, 0.0) for k, v in scores.items()}
        
        # 归一化
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        
        return scores
    
    def _calculate_image_scores(self, face_image: np.ndarray) -> Dict[str, float]:
        """
        基于图像特征计算表情分数（简化版本）
        
        Args:
            face_image: 面部图像
            
        Returns:
            各表情的分数
        """
        import cv2
        
        # 转换为灰度图
        if len(face_image.shape) == 3:
            gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_image
        
        # 计算基本统计特征
        mean_intensity = np.mean(gray)
        std_intensity = np.std(gray)
        
        # 计算梯度特征（边缘强度）
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
        mean_gradient = np.mean(gradient_magnitude)
        
        # 基于简单特征的分数（这是一个简化的启发式方法）
        scores = {label: 0.1 for label in self.EXPRESSION_LABELS}
        
        # 高对比度可能表示更强烈的表情
        if std_intensity > 50:
            scores['surprised'] += 0.1
            scores['happy'] += 0.05
        
        # 高梯度可能表示更多的面部运动
        if mean_gradient > 30:
            scores['angry'] += 0.1
            scores['surprised'] += 0.05
        
        # 默认倾向于 neutral
        scores['neutral'] = 0.3
        
        # 归一化
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        
        return scores
    
    def _parse_predictions(
        self, 
        predictions: Any
    ) -> Tuple[FacialExpression, float, Dict[str, float]]:
        """
        解析模型预测结果
        
        Args:
            predictions: 模型输出的概率分布
            
        Returns:
            (表情类别, 置信度, 各表情分数)
        """
        # 转换为 numpy 数组
        if not isinstance(predictions, np.ndarray):
            predictions = np.array(predictions)
        
        # 确保是一维数组
        predictions = predictions.flatten()
        
        # 应用 softmax（如果还没有）
        if predictions.sum() < 0.99 or predictions.sum() > 1.01:
            exp_preds = np.exp(predictions - np.max(predictions))
            predictions = exp_preds / exp_preds.sum()
        
        # 创建分数字典
        scores = {}
        for i, label in enumerate(self.EXPRESSION_LABELS):
            if i < len(predictions):
                scores[label] = float(predictions[i])
            else:
                scores[label] = 0.0
        
        # 获取主要表情
        primary_idx = np.argmax(predictions)
        primary_label = self.EXPRESSION_LABELS[primary_idx] if primary_idx < len(self.EXPRESSION_LABELS) else 'neutral'
        confidence = float(predictions[primary_idx]) if primary_idx < len(predictions) else 0.0
        # 安全 clamp，防止浮点精度问题导致超出 [0, 1]
        confidence = max(0.0, min(1.0, confidence))
        
        return (
            self.EXPRESSION_MAP.get(primary_label, FacialExpression.NEUTRAL),
            confidence,
            scores
        )
    
    def get_expression_labels(self) -> List[str]:
        """获取支持的表情标签列表"""
        return self.EXPRESSION_LABELS.copy()
    
    def cleanup(self):
        """清理资源"""
        if self.model is not None:
            del self.model
            self.model = None
            self._initialized = False
            logger.info("ExpressionClassifier cleaned up")
