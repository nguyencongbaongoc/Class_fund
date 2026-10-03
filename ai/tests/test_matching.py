from ai.contracts import ExtractionEvidence, SenderExtraction
from ai.matching.service import (
    MatchingService,
    NameNormalizer,
    StudentMatcher,
    StudentRecord,
)


class TestNameNormalizer:
    def test_normalize_vietnamese(self):
        name = "Nguyễn Văn An"
        normalized = NameNormalizer.normalize(name)
        assert normalized == "nguyen van an"

    def test_normalize_uppercase(self):
        name = "NGUYEN VAN A"
        normalized = NameNormalizer.normalize(name)
        assert normalized == "nguyen van a"

    def test_normalize_with_punctuation(self):
        name = "Nguyễn, Văn. An!"
        normalized = NameNormalizer.normalize(name)
        assert normalized == "nguyen van an"

    def test_normalize_extra_spaces(self):
        name = "Nguyễn   Văn   An"
        normalized = NameNormalizer.normalize(name)
        assert normalized == "nguyen van an"

    def test_normalize_empty(self):
        assert NameNormalizer.normalize("") == ""
        assert NameNormalizer.normalize("   ") == ""

    def test_generate_variants(self):
        name = "Nguyễn Văn An"
        variants = NameNormalizer.generate_variants(name)
        assert "nguyen van an" in variants
        assert "an van nguyen" in variants
        assert "nguyenvanan" in variants


class TestStudentMatcher:
    def setup_method(self):
        self.roster = [
            StudentRecord(student_id="1", full_name="Nguyễn Văn An", aliases=["An Nguyen"]),
            StudentRecord(student_id="2", full_name="Nguyễn Văn Anh"),
            StudentRecord(student_id="3", full_name="Nguyễn Văn Ân"),
            StudentRecord(student_id="4", full_name="Trần Thị Bích", student_code="STU001"),
        ]
        self.matcher = StudentMatcher(self.roster)

    def test_exact_match(self):
        sender = SenderExtraction(
            name="NGUYEN VAN AN",
            confidence=0.9,
            evidence=ExtractionEvidence(value="NGUYEN VAN AN", confidence=0.9, source_text="NGUYEN VAN AN"),
        )
        match = self.matcher.match(sender)
        assert match is not None
        assert match.student_id == "1"
        assert match.confidence == 1.0
        assert match.match_method == "exact"

    def test_exact_match_with_diacritics(self):
        sender = SenderExtraction(
            name="NGUYỄN VẢN AN",
            confidence=0.9,
            evidence=ExtractionEvidence(value="NGUYỄN VẢN AN", confidence=0.9, source_text="NGUYỄN VẢN AN"),
        )
        match = self.matcher.match(sender)
        assert match is not None
        assert match.student_id == "1"
        assert match.confidence == 1.0

    def test_fuzzy_match(self):
        sender = SenderExtraction(
            name="NGUYEN VAN AN",
            confidence=0.9,
            evidence=ExtractionEvidence(value="NGUYEN VAN AN", confidence=0.9, source_text="NGUYEN VAN AN"),
        )
        match = self.matcher.match(sender)
        assert match is not None
        assert match.student_id == "1"
        assert match.confidence >= 0.8

    def test_fuzzy_match_close_names(self):
        sender = SenderExtraction(
            name="NGUYEN VAN ANH",
            confidence=0.9,
            evidence=ExtractionEvidence(value="NGUYEN VAN ANH", confidence=0.9, source_text="NGUYEN VAN ANH"),
        )
        match = self.matcher.match(sender)
        assert match is not None
        assert match.student_id == "2"

    def test_alias_match(self):
        sender = SenderExtraction(
            name="AN NGUYEN",
            confidence=0.9,
            evidence=ExtractionEvidence(value="AN NGUYEN", confidence=0.9, source_text="AN NGUYEN"),
        )
        match = self.matcher.match(sender)
        assert match is not None
        assert match.student_id == "1"
        # "AN NGUYEN" is a variant of "Nguyễn Văn An" so it matches via exact/variant
        assert match.match_method in ("exact", "alias")

    def test_student_code_match(self):
        sender = SenderExtraction(
            name="STU001",
            confidence=0.9,
            evidence=ExtractionEvidence(value="STU001", confidence=0.9, source_text="STU001"),
        )
        match = self.matcher.match(sender)
        assert match is not None
        assert match.student_id == "4"

    def test_no_match_low_confidence(self):
        sender = SenderExtraction(
            name="COMPLETELY DIFFERENT NAME",
            confidence=0.9,
            evidence=ExtractionEvidence(value="COMPLETELY DIFFERENT NAME", confidence=0.9, source_text="COMPLETELY DIFFERENT NAME"),
        )
        match = self.matcher.match(sender)
        assert match is None

    def test_candidate_list_populated(self):
        sender = SenderExtraction(
            name="NGUYEN VAN AN",
            confidence=0.9,
            evidence=ExtractionEvidence(value="NGUYEN VAN AN", confidence=0.9, source_text="NGUYEN VAN AN"),
        )
        match = self.matcher.match(sender)
        assert match is not None
        assert len(match.candidate_list) > 0
        for candidate in match.candidate_list:
            assert "student_id" in candidate
            assert "name" in candidate
            assert "score" in candidate


class TestMatchingService:
    def setup_method(self):
        self.roster = [
            StudentRecord(student_id="1", full_name="Nguyễn Văn An"),
        ]
        self.service = MatchingService(self.roster)

    def test_match_sender(self):
        sender = SenderExtraction(
            name="NGUYEN VAN AN",
            confidence=0.9,
            evidence=ExtractionEvidence(value="NGUYEN VAN AN", confidence=0.9, source_text="NGUYEN VAN AN"),
        )
        match = self.service.match_sender(sender)
        assert match is not None
        assert match.student_id == "1"

    def test_update_roster(self):
        new_roster = [
            StudentRecord(student_id="2", full_name="Trần Thị Bích"),
        ]
        self.service.update_roster(new_roster)
        sender = SenderExtraction(
            name="TRAN THI BICH",
            confidence=0.9,
            evidence=ExtractionEvidence(value="TRAN THI BICH", confidence=0.9, source_text="TRAN THI BICH"),
        )
        match = self.service.match_sender(sender)
        assert match is not None
        assert match.student_id == "2"
