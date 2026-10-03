from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import cv2
import numpy as np
import pytesseract
from PIL import Image

from ai.contracts import OCRResult


@dataclass
class PreprocessResult:
    image: np.ndarray
    strategy: str
    params: dict[str, Any]


class Preprocessor:
    def __init__(self) -> None:
        self.strategies = {
            "default": self._preprocess_default,
            "high_contrast": self._preprocess_high_contrast,
            "denoise": self._preprocess_denoise,
            "sharpen": self._preprocess_sharpen,
            "adaptive_threshold": self._preprocess_adaptive_threshold,
            "morphology": self._preprocess_morphology,
        }

    def preprocess(self, image: np.ndarray, strategy: str = "default") -> PreprocessResult:
        if strategy not in self.strategies:
            strategy = "default"
        return self.strategies[strategy](image)

    def try_all_strategies(self, image: np.ndarray) -> list[PreprocessResult]:
        results = []
        for _name, func in self.strategies.items():
            try:
                result = func(image)
                results.append(result)
            except Exception:
                continue
        return results

    def _preprocess_default(self, image: np.ndarray) -> PreprocessResult:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        resized = self._resize_if_needed(gray)
        return PreprocessResult(resized, "default", {})

    def _preprocess_high_contrast(self, image: np.ndarray) -> PreprocessResult:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        resized = self._resize_if_needed(enhanced)
        return PreprocessResult(resized, "high_contrast", {"clip_limit": 3.0})

    def _preprocess_denoise(self, image: np.ndarray) -> PreprocessResult:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        denoised = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
        resized = self._resize_if_needed(denoised)
        return PreprocessResult(resized, "denoise", {"h": 10})

    def _preprocess_sharpen(self, image: np.ndarray) -> PreprocessResult:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        sharpened = cv2.filter2D(gray, -1, kernel)
        resized = self._resize_if_needed(sharpened)
        return PreprocessResult(resized, "sharpen", {})

    def _preprocess_adaptive_threshold(self, image: np.ndarray) -> PreprocessResult:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        resized = self._resize_if_needed(binary)
        return PreprocessResult(resized, "adaptive_threshold", {"block_size": 11, "c": 2})

    def _preprocess_morphology(self, image: np.ndarray) -> PreprocessResult:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        morphed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        resized = self._resize_if_needed(morphed)
        return PreprocessResult(resized, "morphology", {"kernel_size": (2, 2)})

    def _resize_if_needed(self, image: np.ndarray, min_height: int = 1000) -> np.ndarray:
        h, w = image.shape[:2]
        if h < min_height:
            scale = min_height / h
            new_w = int(w * scale)
            return cv2.resize(image, (new_w, min_height), interpolation=cv2.INTER_CUBIC)
        return image


class OCREngine(ABC):
    @abstractmethod
    def recognize(self, image: np.ndarray) -> OCRResult:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def get_version(self) -> str:
        pass


class TesseractEngine(OCREngine):
    def __init__(self, lang: str = "vie+eng", config: str = "--oem 3 --psm 6") -> None:
        self.lang = lang
        self.config = config

    def recognize(self, image: np.ndarray) -> OCRResult:
        start_time = time.perf_counter()

        pil_image = Image.fromarray(image)

        data = pytesseract.image_to_data(
            pil_image, lang=self.lang, config=self.config, output_type=pytesseract.Output.DICT
        )

        text = pytesseract.image_to_string(pil_image, lang=self.lang, config=self.config)

        boxes = []
        for i in range(len(data["text"])):
            if data["text"][i].strip():
                boxes.append({
                    "text": data["text"][i],
                    "conf": data["conf"][i],
                    "x": data["left"][i],
                    "y": data["top"][i],
                    "w": data["width"][i],
                    "h": data["height"][i],
                })

        lines = [line for line in text.split("\n") if line.strip()]

        confidences = [c for c in data["conf"] if c > 0]
        avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0

        processing_time = int((time.perf_counter() - start_time) * 1000)

        return OCRResult(
            raw_text=text.strip(),
            confidence=avg_confidence,
            bounding_boxes=boxes,
            lines=lines,
            words=[{"text": w, "conf": c} for w, c in zip(data["text"], data["conf"], strict=False) if w.strip()],
            engine="tesseract",
            engine_version=pytesseract.get_tesseract_version(),
            processing_time_ms=processing_time,
        )

    def get_name(self) -> str:
        return "tesseract"

    def get_version(self) -> str:
        return str(pytesseract.get_tesseract_version())


class OCRService:
    def __init__(self, engines: list[OCREngine] | None = None) -> None:
        self.engines = engines or [TesseractEngine()]
        self.preprocessor = Preprocessor()

    def process(
        self,
        image_bytes: bytes,
        preprocess_strategy: str = "default",
        try_multiple: bool = True,
    ) -> OCRResult:
        image = self._load_image(image_bytes)

        if try_multiple:
            return self._process_with_multiple_strategies(image)
        else:
            preprocessed = self.preprocessor.preprocess(image, preprocess_strategy)
            return self._run_ocr(preprocessed.image)

    def _process_with_multiple_strategies(self, image: np.ndarray) -> OCRResult:
        best_result = None
        best_confidence = -1.0

        for strategy_name in self.preprocessor.strategies:
            preprocessed = self.preprocessor.preprocess(image, strategy_name)
            result = self._run_ocr(preprocessed.image)

            if result.confidence > best_confidence:
                best_confidence = result.confidence
                best_result = result

        if best_result is None:
            preprocessed = self.preprocessor.preprocess(image, "default")
            best_result = self._run_ocr(preprocessed.image)

        return best_result

    def _run_ocr(self, image: np.ndarray) -> OCRResult:
        best_result = None
        best_confidence = -1.0

        for engine in self.engines:
            try:
                result = engine.recognize(image)
                if result.confidence > best_confidence:
                    best_confidence = result.confidence
                    best_result = result
            except Exception:
                continue

        if best_result is None:
            raise RuntimeError("All OCR engines failed")

        return best_result

    def _load_image(self, image_bytes: bytes) -> np.ndarray:
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Failed to decode image")
        return image


def compute_file_hash(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


def compute_perceptual_hash(image_bytes: bytes) -> str:
    image = Image.open(BytesIO(image_bytes))
    image = image.convert("L").resize((32, 32), Image.Resampling.LANCZOS)
    pixels = np.array(image, dtype=np.float64)
    dct = cv2.dct(pixels)
    dct_low = dct[:8, :8]
    median = np.median(dct_low)
    hash_bits = (dct_low > median).flatten()
    hash_int = 0
    for bit in hash_bits:
        hash_int = (hash_int << 1) | int(bit)
    return f"{hash_int:016x}"
