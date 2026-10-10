from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from rapidfuzz import fuzz, process

from ai.contracts import SenderExtraction, StudentMatch


@dataclass
class StudentRecord:
    student_id: str
    full_name: str
    aliases: list[str] = None
    student_code: str | None = None

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


class NameNormalizer:
    @staticmethod
    def normalize(name: str) -> str:
        if not name:
            return ""

        normalized = unicodedata.normalize("NFD", name)
        normalized = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
        normalized = normalized.lower()
        normalized = "".join(c for c in normalized if c.isalnum() or c.isspace())
        normalized = " ".join(normalized.split())
        return normalized

    @staticmethod
    def generate_variants(name: str) -> list[str]:
        normalized = NameNormalizer.normalize(name)
        variants = {normalized}

        parts = normalized.split()
        if len(parts) >= 2:
            variants.add(" ".join(parts[::-1]))
            variants.add("".join(parts))
            for i in range(len(parts)):
                for j in range(i + 1, len(parts) + 1):
                    variants.add(" ".join(parts[i:j]))

        return list(variants)


class StudentMatcher:
    def __init__(self, roster: list[StudentRecord], exact_threshold: float = 0.95, fuzzy_threshold: float = 0.8) -> None:
        self.roster = roster
        self.exact_threshold = exact_threshold
        self.fuzzy_threshold = fuzzy_threshold
        self._build_index()

    def _build_index(self) -> None:
        self.name_to_student = {}
        self.normalized_names = []

        for student in self.roster:
            normalized = NameNormalizer.normalize(student.full_name)
            self.normalized_names.append((normalized, student.student_id, student.full_name))
            self.name_to_student[normalized] = student

            for alias in student.aliases:
                alias_norm = NameNormalizer.normalize(alias)
                self.normalized_names.append((alias_norm, student.student_id, alias))
                self.name_to_student[alias_norm] = student

            if student.student_code:
                code_norm = NameNormalizer.normalize(student.student_code)
                self.normalized_names.append((code_norm, student.student_id, student.student_code))
                self.name_to_student[code_norm] = student

    def match(self, sender_extraction: SenderExtraction) -> StudentMatch | None:
        sender_name = sender_extraction.name
        normalized_sender = NameNormalizer.normalize(sender_name)

        exact_match = self._try_exact_match(normalized_sender)
        if exact_match:
            return exact_match

        fuzzy_match = self._try_fuzzy_match(normalized_sender, sender_name)
        if fuzzy_match:
            return fuzzy_match

        alias_match = self._try_alias_match(sender_name)
        if alias_match:
            return alias_match

        return None

    def _try_exact_match(self, normalized_sender: str) -> StudentMatch | None:
        for norm_name, student_id, original_name in self.normalized_names:
            if norm_name == normalized_sender:
                student = self._get_student_by_id(student_id)
                if student:
                    return StudentMatch(
                        student_id=student.student_id,
                        confidence=1.0,
                        matched_name=original_name,
                        candidate_list=[{"student_id": student.student_id, "name": original_name, "score": 1.0}],
                        match_method="exact",
                    )
        return None

    def _try_fuzzy_match(self, normalized_sender: str, original_sender: str) -> StudentMatch | None:
        names_only = [item[0] for item in self.normalized_names]

        results = process.extract(
            normalized_sender,
            names_only,
            scorer=fuzz.ratio,
            limit=5,
            score_cutoff=int(self.fuzzy_threshold * 100),
        )

        if not results:
            return None

        best_match, best_score, _ = results[0]
        confidence = best_score / 100.0

        matched_student_id = None
        matched_name = ""
        for norm_name, student_id, original_name in self.normalized_names:
            if norm_name == best_match:
                matched_student_id = student_id
                matched_name = original_name
                break

        if not matched_student_id:
            return None

        candidate_list = []
        for match_name, score, _ in results:
            for norm_name, student_id, original_name in self.normalized_names:
                if norm_name == match_name:
                    candidate_list.append({
                        "student_id": student_id,
                        "name": original_name,
                        "score": score / 100.0,
                    })
                    break

        match_method = "fuzzy_high" if confidence >= self.exact_threshold else "fuzzy"

        return StudentMatch(
            student_id=matched_student_id,
            confidence=confidence,
            matched_name=matched_name,
            candidate_list=candidate_list,
            match_method=match_method,
        )

    def _try_alias_match(self, sender_name: str) -> StudentMatch | None:
        sender_variants = NameNormalizer.generate_variants(sender_name)

        for student in self.roster:
            student_variants = NameNormalizer.generate_variants(student.full_name)

            common = set(sender_variants) & set(student_variants)
            if common:
                best_similarity = max(
                    SequenceMatcher(None, s1, s2).ratio()
                    for s1 in sender_variants
                    for s2 in student_variants
                )
                if best_similarity >= self.fuzzy_threshold:
                    return StudentMatch(
                        student_id=student.student_id,
                        confidence=best_similarity * 0.9,
                        matched_name=student.full_name,
                        candidate_list=[{
                            "student_id": student.student_id,
                            "name": student.full_name,
                            "score": best_similarity,
                        }],
                        match_method="alias",
                    )

        return None

    def _get_student_by_id(self, student_id: str) -> StudentRecord | None:
        for student in self.roster:
            if student.student_id == student_id:
                return student
        return None


class MatchingService:
    def __init__(self, roster: list[StudentRecord]) -> None:
        self.matcher = StudentMatcher(roster)

    def match_sender(self, sender_extraction: SenderExtraction) -> StudentMatch | None:
        return self.matcher.match(sender_extraction)

    def update_roster(self, roster: list[StudentRecord]) -> None:
        self.matcher = StudentMatcher(roster)
