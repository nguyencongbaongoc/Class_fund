from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ai.contracts import (
    AmountExtraction,
    BankExtraction,
    DateTimeExtraction,
    ExtractionEvidence,
    OCRResult,
    SenderExtraction,
    TransactionCodeExtraction,
)


@dataclass
class ExtractionResult:
    amount: AmountExtraction | None
    transaction_code: TransactionCodeExtraction | None
    sender: SenderExtraction | None
    bank: BankExtraction | None
    datetime: DateTimeExtraction | None
    raw_extractions: dict[str, Any]


class AmountExtractor:
    AMOUNT_PATTERNS = [
        (r"(\+?\d{1,3}(?:[., ]\d{3})*(?:[.,]\d{2})?)\s*(?:VND|đ|VNĐ|vnđ)", "vnd_suffix"),
        (r"(?:số tiền|amount|sotien|so tien)[\s:]*(\+?\d{1,3}(?:[., ]\d{3})*(?:[.,]\d{2})?)", "amount_label"),
        (r"(?:chuyển|transfer|gui|gửi)[\s:]*(\+?\d{1,3}(?:[., ]\d{3})*(?:[.,]\d{2})?)", "transfer_label"),
        (r"^(\+?\d{1,3}(?:[., ]\d{3})*(?:[.,]\d{2})?)$", "standalone"),
    ]

    EXCLUDE_PATTERNS = [
        r"\b\d{10,}\b",
        r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b",
        r"\b\d{4}[-.\s]\d{4}[-.\s]\d{4}\b",
    ]

    def __init__(self) -> None:
        self.compiled_patterns = [(re.compile(p, re.IGNORECASE), label) for p, label in self.AMOUNT_PATTERNS]
        self.exclude_compiled = [re.compile(p) for p in self.EXCLUDE_PATTERNS]

    def extract(self, ocr_result: OCRResult) -> AmountExtraction | None:
        text = ocr_result.raw_text
        lines = ocr_result.lines

        candidates = []

        for pattern, label in self.compiled_patterns:
            for match in pattern.finditer(text):
                amount_str = match.group(1)
                normalized = self._normalize_amount(amount_str)
                if normalized is None:
                    continue

                if self._is_excluded(normalized, text, match.start(), match.end()):
                    continue

                confidence = self._calculate_confidence(label, match, text, lines)
                candidates.append({
                    "amount": normalized,
                    "confidence": confidence,
                    "source_text": match.group(0),
                    "span": match.span(),
                    "rule": label,
                })

        if not candidates:
            return None

        candidates.sort(key=lambda x: (-x["confidence"], x["amount"]))
        best = candidates[0]

        return AmountExtraction(
            amount=best["amount"],
            confidence=best["confidence"],
            evidence=ExtractionEvidence(
                value=str(best["amount"]),
                confidence=best["confidence"],
                source_text=best["source_text"],
                source_span=best["span"],
                rule=best["rule"],
            ),
            currency="VND",
        )

    def _normalize_amount(self, amount_str: str) -> int | None:
        cleaned = amount_str.replace(" ", "").replace(",", "").replace(".", "")
        if cleaned.startswith("+"):
            cleaned = cleaned[1:]
        try:
            value = int(cleaned)
            if value <= 0 or value > 1_000_000_000:
                return None
            return value
        except ValueError:
            return None

    def _is_excluded(self, amount: int, text: str, start: int, end: int) -> bool:
        # Check if the EXTRACTED amount text itself matches exclusion patterns
        # (e.g., the amount looks like a phone number or account number)
        amount_text = text[start:end]
        return any(pattern.fullmatch(amount_text.strip()) for pattern in self.exclude_compiled)

    def _calculate_confidence(self, label: str, match: re.Match, text: str, lines: list[str]) -> float:
        base_confidence = {
            "vnd_suffix": 0.95,
            "amount_label": 0.9,
            "transfer_label": 0.85,
            "standalone": 0.6,
        }.get(label, 0.5)

        context = text[max(0, match.start() - 30):min(len(text), match.end() + 30)]
        if any(kw in context.lower() for kw in ["số dư", "balance", "available", "trước", "previous"]):
            base_confidence *= 0.3

        return min(base_confidence, 1.0)


class TransactionCodeExtractor:
    BANK_PATTERNS = {
        "MB": [r"(MBVCB\d{10,})", r"(MB\d{12,})"],
        "VCB": [r"(VCB\d{10,})"],
        "TCB": [r"(TCB\d{10,})"],
        "BIDV": [r"(BIDV\d{10,})"],
        "VPB": [r"(VPB\d{10,})"],
        "ACB": [r"(ACB\d{10,})"],
        "SHB": [r"(SHB\d{10,})"],
        "NAPAS": [r"(NAPAS\d{10,})", r"(NAPAS\s*\d{10,})"],
        "GENERIC": [
            r"(?:MÃ GD[\s:]*|MÃ GIAO DỊCH[\s:]*|Mã GD[\s:]*|Transaction code[\s:]*|TXN[\s:]*|Ref[\s:]*)?([A-Z]{2,4}\d{10,})",
            r"(?:FT|REF|TRX|TXN|GD|MAGD)\d{10,}",
            r"([A-Z]{2,4}\d{10,})",
        ],
    }

    def __init__(self) -> None:
        self.compiled = {}
        for bank, patterns in self.BANK_PATTERNS.items():
            self.compiled[bank] = [(re.compile(p, re.IGNORECASE), p) for p in patterns]

    def extract(self, ocr_result: OCRResult) -> TransactionCodeExtraction | None:
        text = ocr_result.raw_text
        lines = ocr_result.lines

        candidates = []

        for bank, patterns in self.compiled.items():
            for pattern, pattern_str in patterns:
                for match in pattern.finditer(text):
                    # Get the first capturing group that has content, or the full match
                    code = ""
                    if match.lastindex:
                        for i in range(1, match.lastindex + 1):
                            group = match.group(i)
                            if group and group.strip():
                                code = group.strip().upper()
                                break
                    if not code:
                        code = match.group(0).strip().upper()

                    if self._is_valid_code(code):
                        confidence = self._calculate_confidence(bank, pattern_str, match, text, lines)
                        candidates.append({
                            "code": code,
                            "confidence": confidence,
                            "source_text": match.group(0),
                            "span": match.span(),
                            "bank_pattern": bank,
                            "rule": pattern_str,
                        })

        if not candidates:
            return None

        candidates.sort(key=lambda x: (-x["confidence"], -len(x["code"])))
        best = candidates[0]

        return TransactionCodeExtraction(
            code=best["code"],
            confidence=best["confidence"],
            evidence=ExtractionEvidence(
                value=best["code"],
                confidence=best["confidence"],
                source_text=best["source_text"],
                source_span=best["span"],
                rule=best["rule"],
            ),
            bank_pattern=best["bank_pattern"],
        )

    def _is_valid_code(self, code: str) -> bool:
        if len(code) < 8 or len(code) > 30:
            return False
        return bool(re.search(r"\d", code))

    def _calculate_confidence(self, bank: str, pattern: str, match: re.Match, text: str, lines: list[str]) -> float:
        base = 0.85 if bank != "GENERIC" else 0.7
        context = text[max(0, match.start() - 20):min(len(text), match.end() + 20)].lower()
        if any(kw in context for kw in ["mã gd", "mã giao dịch", "transaction", "ref", "mã"]):
            base += 0.1
        return min(base, 1.0)


class SenderExtractor:
    SENDER_LABELS = [
        # Stop at common field keywords or newlines
        r"(?:người gửi|sender|nguoi gui|from)[\s:]*([A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ\s]+?)(?:\s+(?:số|amount|mã|code|ngân|bank|ngày|date|chuyển|transfer|người nhận|recipient)|\n|$)",
        r"(?:chủ tài khoản|account holder|chu tai khoan)[\s:]*([A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ\s]+?)(?:\s+(?:số|amount|mã|code|ngân|bank|ngày|date|chuyển|transfer)|\n|$)",
    ]

    def __init__(self) -> None:
        self.compiled = [(re.compile(p, re.IGNORECASE), p) for p in self.SENDER_LABELS]
        # Allow single character parts for middle initials
        self.name_pattern = re.compile(r"[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]{1,}(?:\s+[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]{1,}){1,5}")

    def extract(self, ocr_result: OCRResult) -> SenderExtraction | None:
        text = ocr_result.raw_text
        lines = ocr_result.lines

        candidates = []

        for pattern, pattern_str in self.compiled:
            for match in pattern.finditer(text):
                name = match.group(1).strip()
                name = self._clean_name(name)
                if self._is_valid_name(name):
                    confidence = 0.9
                    candidates.append({
                        "name": name,
                        "confidence": confidence,
                        "source_text": match.group(0),
                        "span": match.span(),
                        "rule": pattern_str,
                    })

        for line in lines:
            names = self.name_pattern.findall(line)
            for name in names:
                name = self._clean_name(name)
                if self._is_valid_name(name) and not any(c["name"] == name for c in candidates):
                    confidence = 0.5
                    candidates.append({
                        "name": name,
                        "confidence": confidence,
                        "source_text": line,
                        "span": (text.find(line), text.find(line) + len(line)),
                        "rule": "name_pattern",
                    })

        if not candidates:
            return None

        candidates.sort(key=lambda x: -x["confidence"])
        best = candidates[0]
        other_names = [c["name"] for c in candidates[1:]]

        return SenderExtraction(
            name=best["name"],
            confidence=best["confidence"],
            evidence=ExtractionEvidence(
                value=best["name"],
                confidence=best["confidence"],
                source_text=best["source_text"],
                source_span=best["span"],
                rule=best["rule"],
            ),
            candidates=other_names,
        )

    def _clean_name(self, name: str) -> str:
        name = re.sub(r"[^\w\sÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]", "", name)
        name = re.sub(r"\s+", " ", name).strip()
        return name.upper()

    def _is_valid_name(self, name: str) -> bool:
        parts = name.split()
        if len(parts) < 2 or len(parts) > 6:
            return False
        # Allow single-character parts (middle initials)
        if any(len(p) < 1 for p in parts):
            return False
        # At least one part should be >= 2 chars
        return any(len(p) >= 2 for p in parts)


class BankExtractor:
    BANK_KEYWORDS = {
        "MB Bank": ["MB BANK", "MBBANK", "NGÂN HÀNG MB", "MB VC B"],
        "Vietcombank": ["VIETCOMBANK", "VCB", "NGÂN HÀNG VIETCOMBANK", "VIETCOM BANK"],
        "Techcombank": ["TECHCOMBANK", "TCB", "NGÂN HÀNG TECHCOMBANK", "TECHCOM BANK"],
        "BIDV": ["BIDV", "NGÂN HÀNG BIDV", "BANK FOR INVESTMENT AND DEVELOPMENT"],
        "VPBank": ["VPBANK", "VP BANK", "NGÂN HÀNG VPBANK", "VIETNAM PROSPERITY"],
        "ACB": ["ACB", "NGÂN HÀNG Á CHÂU", "ASIA COMMERCIAL BANK"],
        "SHB": ["SHB", "NGÂN HÀNG SHB", "SAIGON HANOI BANK"],
        "Sacombank": ["SACOMBANK", "SACOM BANK", "NGÂN HÀNG SÀI GÒN THƯƠNG TÍN"],
        "VietinBank": ["VIETINBANK", "VIETIN BANK", "NGÂN HÀNG VIETINBANK"],
        "Agribank": ["AGRIBANK", "AGRI BANK", "NGÂN HÀNG NÔNG NGHIỆP"],
        "SeABank": ["SEABANK", "SEA BANK", "NGÂN HÀNG ĐÔNG NAM Á"],
        "NAPAS": ["NAPAS", "NATIONAL PAYMENT"],
    }

    BANK_CODES = {
        "MB Bank": "MB",
        "Vietcombank": "VCB",
        "Techcombank": "TCB",
        "BIDV": "BIDV",
        "VPBank": "VPB",
        "ACB": "ACB",
        "SHB": "SHB",
        "Sacombank": "STB",
        "VietinBank": "ICB",
        "Agribank": "VBA",
        "SeABank": "SEA",
        "NAPAS": "NAPAS",
    }

    def __init__(self) -> None:
        self.compiled_keywords = {}
        for bank, keywords in self.BANK_KEYWORDS.items():
            self.compiled_keywords[bank] = [re.compile(kw, re.IGNORECASE) for kw in keywords]

    def extract(self, ocr_result: OCRResult) -> BankExtraction | None:
        text = ocr_result.raw_text.upper()

        candidates = []

        for bank, patterns in self.compiled_keywords.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    confidence = 0.85
                    if any(kw in text[max(0, match.start() - 20):match.end() + 20] for kw in ["NGÂN HÀNG", "BANK", "NH "]):
                        confidence = 0.95
                    candidates.append({
                        "name": bank,
                        "confidence": confidence,
                        "source_text": match.group(0),
                        "span": match.span(),
                        "code": self.BANK_CODES.get(bank),
                    })

        if not candidates:
            return None

        candidates.sort(key=lambda x: -x["confidence"])
        best = candidates[0]

        return BankExtraction(
            name=best["name"],
            confidence=best["confidence"],
            evidence=ExtractionEvidence(
                value=best["name"],
                confidence=best["confidence"],
                source_text=best["source_text"],
                source_span=best["span"],
                rule="bank_keyword",
            ),
            code=best["code"],
        )


class DateTimeExtractor:
    DATETIME_PATTERNS = [
        (r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})[\sT](\d{1,2}):(\d{2})(?::(\d{2}))?", "ddmmyyyy_hms"),
        (r"(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})[\sT](\d{1,2}):(\d{2})(?::(\d{2}))?", "yyyymmdd_hms"),
        (r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})", "ddmmyyyy"),
        (r"(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})", "yyyymmdd"),
        (r"(\d{1,2}):(\d{2})(?::(\d{2}))?", "time_only"),
    ]

    def __init__(self) -> None:
        self.compiled = [(re.compile(p), fmt) for p, fmt in self.DATETIME_PATTERNS]

    def extract(self, ocr_result: OCRResult) -> DateTimeExtraction | None:
        text = ocr_result.raw_text

        candidates = []

        for pattern, fmt in self.compiled:
            for match in pattern.finditer(text):
                dt = self._parse_match(match, fmt)
                if dt is None:
                    continue

                context = text[max(0, match.start() - 30):min(len(text), match.end() + 30)].lower()
                confidence = 0.7
                if any(kw in context for kw in ["ngày", "giờ", "thời gian", "time", "date", "ngày giờ"]):
                    confidence = 0.9

                candidates.append({
                    "datetime": dt,
                    "confidence": confidence,
                    "source_text": match.group(0),
                    "span": match.span(),
                    "rule": fmt,
                })

        if not candidates:
            return None

        candidates.sort(key=lambda x: -x["confidence"])
        best = candidates[0]

        return DateTimeExtraction(
            timestamp=best["datetime"],
            confidence=best["confidence"],
            evidence=ExtractionEvidence(
                value=best["datetime"].isoformat(),
                confidence=best["confidence"],
                source_text=best["source_text"],
                source_span=best["span"],
                rule=best["rule"],
            ),
            timezone="UTC",
        )

    def _parse_match(self, match: re.Match, fmt: str) -> datetime | None:
        try:
            groups = match.groups()
            if fmt in ("ddmmyyyy_hms", "yyyymmdd_hms"):
                if fmt == "ddmmyyyy_hms":
                    day, month, year, hour, minute, *second = groups
                else:
                    year, month, day, hour, minute, *second = groups
                second = second[0] if second else "0"
                return datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
            elif fmt in ("ddmmyyyy", "yyyymmdd"):
                if fmt == "ddmmyyyy":
                    day, month, year = groups
                else:
                    year, month, day = groups
                return datetime(int(year), int(month), int(day), 0, 0, 0)
            elif fmt == "time_only":
                hour, minute, *second = groups
                second = second[0] if second else "0"
                now = datetime.now()
                return datetime(now.year, now.month, now.day, int(hour), int(minute), int(second))
        except (ValueError, IndexError):
            return None
        return None


class ExtractionService:
    def __init__(self) -> None:
        self.amount_extractor = AmountExtractor()
        self.transaction_code_extractor = TransactionCodeExtractor()
        self.sender_extractor = SenderExtractor()
        self.bank_extractor = BankExtractor()
        self.datetime_extractor = DateTimeExtractor()

    def extract_all(self, ocr_result: OCRResult) -> ExtractionResult:
        amount = self.amount_extractor.extract(ocr_result)
        transaction_code = self.transaction_code_extractor.extract(ocr_result)
        sender = self.sender_extractor.extract(ocr_result)
        bank = self.bank_extractor.extract(ocr_result)
        datetime_ext = self.datetime_extractor.extract(ocr_result)

        return ExtractionResult(
            amount=amount,
            transaction_code=transaction_code,
            sender=sender,
            bank=bank,
            datetime=datetime_ext,
            raw_extractions={
                "amount": amount.model_dump() if amount else None,
                "transaction_code": transaction_code.model_dump() if transaction_code else None,
                "sender": sender.model_dump() if sender else None,
                "bank": bank.model_dump() if bank else None,
                "datetime": datetime_ext.model_dump() if datetime_ext else None,
            },
        )
