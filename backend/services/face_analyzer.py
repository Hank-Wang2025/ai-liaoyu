"""
MediaPipe 面部分析模块
MediaPipe Face Analysis Module

使用 MediaPipe Face Mesh 进行实时人脸检测和关键点提取
支持 468 个面部关键点检测和 7 类基础表情识别
"""
import os
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple, Generator
from loguru import logger
import numpy as np

from models.emotion import FacialExpression, FaceAnalysisResult
from services.expression_classifier import ExpressionClassifier


class FaceAnalyzer:
    """
    MediaPipe 面部分析器
    
    功能:
    - 实时人脸检测
    - 468 个面部关键点提取
    - 7 类基础表情识别
    - 摄像头数据流处理
    
    Requirements: 2.1, 2.2
    """
    
    # 面部关键点数量 (MediaPipe Face Mesh)
    NUM_LANDMARKS = 468
    
    # 默认检测参数
    DEFAULT_MIN_DETECTION_CONFIDENCE = 0.5
    DEFAULT_MIN_TRACKING_CONFIDENCE = 0.5
    DEFAULT_MAX_NUM_FACES = 1
    
    # 表情效价映射 (valence: -1 负面 到 1 正面)
    EXPRESSION_VALENCE = {
        "happy": 0.9,
        "sad": -0.7,
        "angry": -0.8,
        "fearful": -0.6,
        "surprised": 0.2,
        "disgusted": -0.7,
        "neutral": 0.0
    }
    
    # 表情唤醒度映射 (arousal: 0 平静 到 1 激动)
    EXPRESSION_AROUSAL = {
        "happy": 0.7,
        "sad": 0.2,
        "angry": 0.9,
        "fearful": 0.8,
        "surprised": 0.8,
        "disgusted": 0.5,
        "neutral": 0.3
    }
    
    def __init__(
        self,
        min_detection_confidence: float = DEFAULT_MIN_DETECTION_CONFIDENCE,
        min_tracking_confidence: float = DEFAULT_MIN_TRACKING_CONFIDENCE,
        max_num_faces: int = DEFAULT_MAX_NUM_FACES,
        refine_landmarks: bool = True,
        expression_model_path: Optional[str] = None
    ):
        """
        初始化 MediaPipe 面部分析器
        
        Args:
            min_detection_confidence: 最小检测置信度 (0-1)
            min_tracking_confidence: 最小跟踪置信度 (0-1)
            max_num_faces: 最大检测人脸数
            refine_landmarks: 是否精细化关键点（包含虹膜关键点）
            expression_model_path: 表情分类模型路径（可选）
        """
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.max_num_faces = max_num_faces
        self.refine_landmarks = refine_landmarks
        self.expression_model_path = expression_model_path
        
        self.face_mesh = None
        self.mp_face_mesh = None
        self.mp_drawing = None
        self._initialized = False
        
        # 表情分类器
        self._expression_classifier: Optional[ExpressionClassifier] = None
        
        logger.info("FaceAnalyzer created with MediaPipe Face Mesh")
    
    def initialize(self) -> bool:
        """
        初始化 MediaPipe Face Mesh 和表情分类器
        
        Returns:
            是否初始化成功
        """
        if self._initialized:
            return True
        
        try:
            import mediapipe as mp
            
            self.mp_face_mesh = mp.solutions.face_mesh
            self.mp_drawing = mp.solutions.drawing_utils
            
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=self.max_num_faces,
                refine_landmarks=self.refine_landmarks,
                min_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_tracking_confidence
            )
            
            # 初始化表情分类器
            self._expression_classifier = ExpressionClassifier(
                model_path=self.expression_model_path
            )
            self._expression_classifier.initialize()
            
            self._initialized = True
            logger.info("MediaPipe Face Mesh and ExpressionClassifier initialized successfully")
            return True
            
        except ImportError as e:
            logger.error(f"MediaPipe not installed: {e}")
            logger.info("Please install: pip install mediapipe")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize MediaPipe Face Mesh: {e}")
            return False
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    async def analyze(self, frame: np.ndarray) -> FaceAnalysisResult:
        """
        分析单帧图像中的面部表情
        
        Args:
            frame: BGR 格式的图像帧 (numpy array)
            
        Returns:
            FaceAnalysisResult 分析结果
        """
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("MediaPipe Face Mesh not initialized")
        
        return self._analyze_frame(frame)
    
    def analyze_sync(self, frame: np.ndarray) -> FaceAnalysisResult:
        """
        同步分析单帧图像（用于非异步环境）
        
        Args:
            frame: BGR 格式的图像帧
            
        Returns:
            FaceAnalysisResult 分析结果
        """
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("MediaPipe Face Mesh not initialized")
        
        return self._analyze_frame(frame)
    
    def _analyze_frame(self, frame: np.ndarray) -> FaceAnalysisResult:
        """
        内部方法：分析单帧图像
        
        Args:
            frame: BGR 格式的图像帧
            
        Returns:
            FaceAnalysisResult 分析结果
        """
        import cv2
        
        # 转换 BGR 到 RGB（MediaPipe 需要 RGB 格式）
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 处理图像
        results = self.face_mesh.process(rgb_frame)
        
        # 检查是否检测到人脸
        if not results.multi_face_landmarks:
            return FaceAnalysisResult.no_face_detected()
        
        # 获取第一个人脸的关键点
        face_landmarks = results.multi_face_landmarks[0]
        
        # 提取关键点坐标
        landmarks = self._extract_landmarks(face_landmarks, frame.shape)
        
        # 计算人脸边界框
        face_bbox = self._calculate_bbox(landmarks, frame.shape)
        
        # 提取面部区域图像用于表情分类
        x, y, w, h = face_bbox
        if w > 0 and h > 0:
            face_image = frame[y:y+h, x:x+w]
        else:
            face_image = frame
        
        # 分类表情（使用 ExpressionClassifier）
        expression, confidence, scores = self._classify_expression(landmarks, face_image)
        
        return FaceAnalysisResult(
            detected=True,
            expression=expression,
            confidence=confidence,
            expression_scores=scores,
            landmarks=landmarks,
            face_bbox=face_bbox,
            timestamp=datetime.now()
        )
    
    def _extract_landmarks(
        self, 
        face_landmarks: Any, 
        frame_shape: Tuple[int, int, int]
    ) -> List[Tuple[float, float, float]]:
        """
        提取面部关键点坐标
        
        Args:
            face_landmarks: MediaPipe 面部关键点对象
            frame_shape: 图像尺寸 (height, width, channels)
            
        Returns:
            468 个关键点的 (x, y, z) 坐标列表
        """
        height, width = frame_shape[:2]
        landmarks = []
        
        for landmark in face_landmarks.landmark:
            # 转换归一化坐标到像素坐标
            x = landmark.x * width
            y = landmark.y * height
            z = landmark.z * width  # z 使用 width 作为参考
            landmarks.append((x, y, z))
        
        return landmarks
    
    def _calculate_bbox(
        self, 
        landmarks: List[Tuple[float, float, float]],
        frame_shape: Tuple[int, int, int]
    ) -> Tuple[int, int, int, int]:
        """
        计算人脸边界框
        
        Args:
            landmarks: 关键点列表
            frame_shape: 图像尺寸
            
        Returns:
            (x, y, width, height) 边界框
        """
        if not landmarks:
            return (0, 0, 0, 0)
        
        x_coords = [lm[0] for lm in landmarks]
        y_coords = [lm[1] for lm in landmarks]
        
        x_min = max(0, int(min(x_coords)))
        y_min = max(0, int(min(y_coords)))
        x_max = min(frame_shape[1], int(max(x_coords)))
        y_max = min(frame_shape[0], int(max(y_coords)))
        
        return (x_min, y_min, x_max - x_min, y_max - y_min)
    
    def _classify_expression(
        self, 
        landmarks: List[Tuple[float, float, float]],
        face_image: Optional[np.ndarray] = None
    ) -> Tuple[FacialExpression, float, Dict[str, float]]:
        """
        基于关键点和图像分类面部表情
        
        使用 ExpressionClassifier 进行表情分类，支持：
        - 预训练 CNN 模型
        - 基于几何特征的规则分类
        
        Args:
            landmarks: 468 个面部关键点
            face_image: 可选的面部图像（用于 CNN 分类）
            
        Returns:
            (表情类别, 置信度, 各表情分数)
        """
        if self._expression_classifier is None:
            # 回退到简单的几何分类
            return self._classify_expression_geometric(landmarks)
        
        return self._expression_classifier.classify(
            face_image if face_image is not None else np.zeros((48, 48), dtype=np.uint8),
            landmarks
        )
    
    def _classify_expression_geometric(
        self, 
        landmarks: List[Tuple[float, float, float]]
    ) -> Tuple[FacialExpression, float, Dict[str, float]]:
        """
        基于关键点几何特征分类面部表情（回退方法）
        
        Args:
            landmarks: 468 个面部关键点
            
        Returns:
            (表情类别, 置信度, 各表情分数)
        """
        # 计算面部几何特征
        features = self._extract_geometric_features(landmarks)
        
        # 基于规则的表情分类
        scores = self._calculate_expression_scores(features)
        
        # 获取主要表情
        primary_expression = max(scores, key=scores.get)
        confidence = scores[primary_expression]
        
        return (
            FacialExpression(primary_expression),
            confidence,
            scores
        )
    
    def _extract_geometric_features(
        self, 
        landmarks: List[Tuple[float, float, float]]
    ) -> Dict[str, float]:
        """
        提取面部几何特征
        
        MediaPipe Face Mesh 关键点索引参考:
        - 左眼: 33, 133, 160, 159, 158, 144, 145, 153
        - 右眼: 362, 263, 387, 386, 385, 373, 374, 380
        - 左眉: 70, 63, 105, 66, 107
        - 右眉: 336, 296, 334, 293, 300
        - 嘴巴: 61, 291, 0, 17, 13, 14, 78, 308
        - 鼻子: 1, 2, 98, 327
        
        Args:
            landmarks: 468 个面部关键点
            
        Returns:
            几何特征字典
        """
        features = {}
        
        # 眼睛开合度 (Eye Aspect Ratio - EAR)
        # 左眼
        left_eye_top = landmarks[159][1]
        left_eye_bottom = landmarks[145][1]
        left_eye_left = landmarks[33][0]
        left_eye_right = landmarks[133][0]
        left_ear = (left_eye_bottom - left_eye_top) / max(left_eye_right - left_eye_left, 1)
        
        # 右眼
        right_eye_top = landmarks[386][1]
        right_eye_bottom = landmarks[374][1]
        right_eye_left = landmarks[362][0]
        right_eye_right = landmarks[263][0]
        right_ear = (right_eye_bottom - right_eye_top) / max(right_eye_right - right_eye_left, 1)
        
        features['eye_aspect_ratio'] = (left_ear + right_ear) / 2
        
        # 眉毛高度（相对于眼睛）
        left_brow_center = landmarks[105][1]
        right_brow_center = landmarks[334][1]
        left_eye_center = (left_eye_top + left_eye_bottom) / 2
        right_eye_center = (right_eye_top + right_eye_bottom) / 2
        
        features['left_brow_height'] = left_eye_center - left_brow_center
        features['right_brow_height'] = right_eye_center - right_brow_center
        features['brow_height'] = (features['left_brow_height'] + features['right_brow_height']) / 2
        
        # 嘴巴开合度 (Mouth Aspect Ratio - MAR)
        mouth_top = landmarks[13][1]
        mouth_bottom = landmarks[14][1]
        mouth_left = landmarks[61][0]
        mouth_right = landmarks[291][0]
        mouth_height = mouth_bottom - mouth_top
        mouth_width = mouth_right - mouth_left
        features['mouth_aspect_ratio'] = mouth_height / max(mouth_width, 1)
        
        # 嘴角位置（相对于嘴巴中心）
        mouth_center_y = (mouth_top + mouth_bottom) / 2
        left_corner = landmarks[61][1]
        right_corner = landmarks[291][1]
        features['mouth_corner_lift'] = mouth_center_y - (left_corner + right_corner) / 2
        
        # 嘴巴宽度（微笑时会变宽）
        features['mouth_width'] = mouth_width
        
        # 眉毛内侧距离（皱眉时会变近）
        left_brow_inner = landmarks[107][0]
        right_brow_inner = landmarks[336][0]
        features['brow_inner_distance'] = right_brow_inner - left_brow_inner
        
        return features
    
    def _calculate_expression_scores(
        self, 
        features: Dict[str, float]
    ) -> Dict[str, float]:
        """
        基于几何特征计算各表情的分数
        
        Args:
            features: 几何特征字典
            
        Returns:
            各表情的分数 (0-1)
        """
        scores = {expr.value: 0.0 for expr in FacialExpression}
        
        ear = features.get('eye_aspect_ratio', 0.3)
        mar = features.get('mouth_aspect_ratio', 0.1)
        brow_height = features.get('brow_height', 0)
        mouth_corner_lift = features.get('mouth_corner_lift', 0)
        brow_inner_distance = features.get('brow_inner_distance', 50)
        
        # Happy: 嘴角上扬，眼睛微眯
        if mouth_corner_lift > 5 and mar > 0.1:
            scores['happy'] = min(0.3 + mouth_corner_lift * 0.02 + mar * 0.5, 1.0)
        
        # Sad: 嘴角下垂，眉毛内侧上扬
        if mouth_corner_lift < -3:
            scores['sad'] = min(0.3 + abs(mouth_corner_lift) * 0.03, 1.0)
        
        # Angry: 眉毛下压，眉毛内侧靠近
        if brow_height < 15 and brow_inner_distance < 40:
            scores['angry'] = min(0.3 + (40 - brow_inner_distance) * 0.02, 1.0)
        
        # Surprised: 眼睛睁大，嘴巴张开，眉毛上扬
        if ear > 0.35 and mar > 0.3 and brow_height > 25:
            scores['surprised'] = min(0.3 + ear * 0.5 + mar * 0.3, 1.0)
        
        # Fearful: 眼睛睁大，眉毛上扬内收
        if ear > 0.35 and brow_height > 20:
            scores['fearful'] = min(0.2 + ear * 0.4, 1.0)
        
        # Disgusted: 鼻子皱起，上唇上扬
        if mar < 0.15 and mouth_corner_lift < 0:
            scores['disgusted'] = min(0.2 + abs(mouth_corner_lift) * 0.02, 0.8)
        
        # Neutral: 默认分数
        scores['neutral'] = 0.3
        
        # 归一化分数
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        
        return scores

    
    def process_camera_stream(
        self, 
        camera_id: int = 0,
        target_fps: int = 30
    ) -> Generator[FaceAnalysisResult, None, None]:
        """
        处理摄像头数据流
        
        Args:
            camera_id: 摄像头 ID (默认 0 为默认摄像头)
            target_fps: 目标帧率
            
        Yields:
            FaceAnalysisResult 每帧的分析结果
        """
        import cv2
        import time
        
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("MediaPipe Face Mesh not initialized")
        
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open camera {camera_id}")
        
        frame_interval = 1.0 / target_fps
        last_frame_time = 0
        
        try:
            while True:
                current_time = time.time()
                
                # 控制帧率
                if current_time - last_frame_time < frame_interval:
                    continue
                
                ret, frame = cap.read()
                if not ret:
                    logger.warning("Failed to read frame from camera")
                    continue
                
                last_frame_time = current_time
                
                # 分析帧
                result = self._analyze_frame(frame)
                yield result
                
        finally:
            cap.release()
    
    async def analyze_image_file(self, image_path: str) -> FaceAnalysisResult:
        """
        分析图像文件中的面部表情
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            FaceAnalysisResult 分析结果
        """
        import cv2
        
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        frame = cv2.imread(image_path)
        if frame is None:
            raise ValueError(f"Failed to read image: {image_path}")
        
        return await self.analyze(frame)
    
    def analyze_image_file_sync(self, image_path: str) -> FaceAnalysisResult:
        """
        同步分析图像文件（用于非异步环境）
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            FaceAnalysisResult 分析结果
        """
        import cv2
        
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        frame = cv2.imread(image_path)
        if frame is None:
            raise ValueError(f"Failed to read image: {image_path}")
        
        return self.analyze_sync(frame)
    
    def get_valence(self, expression: str) -> float:
        """
        获取表情的效价值
        
        Args:
            expression: 表情标签
            
        Returns:
            效价值 (-1 到 1)
        """
        return self.EXPRESSION_VALENCE.get(expression.lower(), 0.0)
    
    def get_arousal(self, expression: str) -> float:
        """
        获取表情的唤醒度
        
        Args:
            expression: 表情标签
            
        Returns:
            唤醒度 (0 到 1)
        """
        return self.EXPRESSION_AROUSAL.get(expression.lower(), 0.3)
    
    def get_expression_labels(self) -> List[str]:
        """获取支持的表情标签列表"""
        return [e.value for e in FacialExpression]
    
    def draw_landmarks(
        self, 
        frame: np.ndarray, 
        landmarks: List[Tuple[float, float, float]],
        draw_tesselation: bool = True,
        draw_contours: bool = True
    ) -> np.ndarray:
        """
        在图像上绘制面部关键点
        
        Args:
            frame: 原始图像帧
            landmarks: 关键点列表
            draw_tesselation: 是否绘制网格
            draw_contours: 是否绘制轮廓
            
        Returns:
            绘制后的图像帧
        """
        import cv2
        
        annotated_frame = frame.copy()
        
        # 绘制关键点
        for i, (x, y, z) in enumerate(landmarks):
            cv2.circle(annotated_frame, (int(x), int(y)), 1, (0, 255, 0), -1)
        
        return annotated_frame
    
    def cleanup(self):
        """清理资源"""
        if self.face_mesh is not None:
            self.face_mesh.close()
            self.face_mesh = None
            self._initialized = False
            logger.info("MediaPipe Face Mesh cleaned up")
