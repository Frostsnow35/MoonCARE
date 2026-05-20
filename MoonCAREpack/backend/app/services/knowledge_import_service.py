import hashlib
import json
import logging
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


logger = logging.getLogger(__name__)

SPREADSHEET_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
REL_ATTR = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


@dataclass(frozen=True)
class KnowledgeImportRow:
    """One normalized Q/A row imported from a workbook."""

    question: str
    answer: str
    source_file: str
    sheet_name: str
    row_number: int


class KnowledgeBaseImportService:
    """Import Excel Q/A workbooks into the local JSON knowledge base with de-duplication."""

    header_aliases = {
        "question": {"q", "问题", "question", "问", "用户问题"},
        "answer": {"a", "答案", "answer", "答", "回答"},
    }

    keyword_candidates = [
        "PMS",
        "经前期综合征",
        "经前",
        "经期",
        "月经",
        "痛经",
        "腹痛",
        "盆腔",
        "出血",
        "白带",
        "阴道",
        "分泌物",
        "卵巢囊肿",
        "子宫肌瘤",
        "子宫内膜异位症",
        "多囊卵巢综合征",
        "乳房",
        "乳腺",
        "HPV",
        "宫颈癌",
        "筛查",
        "备孕",
        "怀孕",
        "不孕",
        "更年期",
        "绝经",
        "盆底",
        "漏尿",
        "妇科检查",
        "睡眠",
        "焦虑",
        "烦躁",
        "水肿",
        "咖啡因",
    ]

    def read_xlsx_qa_rows(self, workbook_path: Path) -> list[KnowledgeImportRow]:
        """Read question/answer rows from the first-level worksheets in an XLSX file."""
        workbook_path = Path(workbook_path)
        rows: list[KnowledgeImportRow] = []

        with zipfile.ZipFile(workbook_path) as archive:
            shared_strings = self._read_shared_strings(archive)
            sheets = self._read_sheet_paths(archive)

            for sheet_name, sheet_path in sheets:
                if sheet_path not in archive.namelist():
                    logger.warning("Sheet path %s missing in %s", sheet_path, workbook_path)
                    continue

                matrix = self._read_sheet_matrix(archive, sheet_path, shared_strings)
                if not matrix:
                    continue

                question_index, answer_index = self._detect_qa_columns(matrix[0])
                if question_index is None or answer_index is None:
                    logger.warning("No Q/A header found in %s:%s", workbook_path.name, sheet_name)
                    continue

                for row_number, values in enumerate(matrix[1:], start=2):
                    question = self._value_at(values, question_index)
                    answer = self._value_at(values, answer_index)
                    if not question or not answer:
                        continue
                    rows.append(
                        KnowledgeImportRow(
                            question=question,
                            answer=self._ensure_reference_notice(answer),
                            source_file=workbook_path.name,
                            sheet_name=sheet_name,
                            row_number=row_number,
                        )
                    )

        return rows

    def merge_knowledge(
        self,
        existing_cards: list[dict[str, Any]],
        import_rows: list[KnowledgeImportRow],
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """Merge imported rows into existing cards, de-duplicating by normalized question."""
        stats = {
            "existing": len(existing_cards),
            "source_rows": len(import_rows),
            "added": 0,
            "duplicates": 0,
            "existing_duplicates": 0,
        }
        merged: list[dict[str, Any]] = []
        by_question: dict[str, dict[str, Any]] = {}

        for card in existing_cards:
            normalized = self.normalize_question(str(card.get("question", "")))
            if not normalized:
                continue
            if normalized in by_question:
                self._merge_card_metadata(by_question[normalized], card)
                stats["existing_duplicates"] += 1
                continue
            copied = dict(card)
            copied["keywords"] = self._unique_strings(copied.get("keywords", []))
            by_question[normalized] = copied
            merged.append(copied)

        for row in import_rows:
            normalized = self.normalize_question(row.question)
            source = self._source_label(row)
            keywords = self.extract_keywords(row.question, row.answer)
            if normalized in by_question:
                card = by_question[normalized]
                card["source"] = self._merge_source(card.get("source", ""), source)
                card["keywords"] = self._unique_strings(list(card.get("keywords", [])) + keywords)
                stats["duplicates"] += 1
                continue

            card = {
                "id": self._stable_id(normalized),
                "question": row.question,
                "answer": row.answer,
                "keywords": keywords,
                "source": source,
            }
            by_question[normalized] = card
            merged.append(card)
            stats["added"] += 1

        stats["total"] = len(merged)
        return merged, stats

    def import_files(self, workbook_paths: list[Path], knowledge_path: Path) -> dict[str, int]:
        """Import workbook rows into a JSON knowledge base file."""
        knowledge_path = Path(knowledge_path)
        existing_cards: list[dict[str, Any]] = []
        if knowledge_path.exists():
            existing_cards = json.loads(knowledge_path.read_text(encoding="utf-8"))

        rows: list[KnowledgeImportRow] = []
        for workbook_path in workbook_paths:
            rows.extend(self.read_xlsx_qa_rows(Path(workbook_path)))

        merged, stats = self.merge_knowledge(existing_cards, rows)
        knowledge_path.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        logger.info("Imported knowledge rows into %s: %s", knowledge_path, stats)
        return stats

    def normalize_question(self, question: str) -> str:
        """Normalize a question for stable duplicate detection."""
        text = (question or "").strip().lower()
        text = re.sub(r"\s+", "", text)
        text = re.sub(r"[？?。！!，,、：:；;“”\"'‘’（）()\[\]【】]", "", text)
        return text

    def extract_keywords(self, question: str, answer: str) -> list[str]:
        """Extract compact domain keywords from a Q/A pair."""
        combined = f"{question}\n{answer}"
        keywords = [keyword for keyword in self.keyword_candidates if keyword.lower() in combined.lower()]
        if "经前期综合征" in combined and "PMS" not in keywords:
            keywords.append("PMS")
        return self._unique_strings(keywords or ["女性健康"])

    def _read_shared_strings(self, archive: zipfile.ZipFile) -> list[str]:
        if "xl/sharedStrings.xml" not in archive.namelist():
            return []

        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        strings: list[str] = []
        for item in root.findall("x:si", SPREADSHEET_NS):
            strings.append("".join(node.text or "" for node in item.findall(".//x:t", SPREADSHEET_NS)))
        return strings

    def _read_sheet_paths(self, archive: zipfile.ZipFile) -> list[tuple[str, str]]:
        if "xl/workbook.xml" not in archive.namelist():
            return [("Sheet1", "xl/worksheets/sheet1.xml")]

        workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = self._read_workbook_relationships(archive)
        sheets: list[tuple[str, str]] = []
        for sheet in workbook_root.findall(".//x:sheet", SPREADSHEET_NS):
            name = sheet.attrib.get("name", "Sheet")
            rel_id = sheet.attrib.get(REL_ATTR, "")
            target = rels.get(rel_id, "")
            if not target:
                continue
            if not target.startswith("xl/"):
                target = f"xl/{target.lstrip('/')}"
            sheets.append((name, target))
        return sheets or [("Sheet1", "xl/worksheets/sheet1.xml")]

    def _read_workbook_relationships(self, archive: zipfile.ZipFile) -> dict[str, str]:
        rel_path = "xl/_rels/workbook.xml.rels"
        if rel_path not in archive.namelist():
            return {}
        rel_root = ET.fromstring(archive.read(rel_path))
        rels: dict[str, str] = {}
        for rel in rel_root.findall("r:Relationship", REL_NS):
            rel_id = rel.attrib.get("Id", "")
            target = rel.attrib.get("Target", "")
            if rel_id and target:
                rels[rel_id] = target
        return rels

    def _read_sheet_matrix(
        self,
        archive: zipfile.ZipFile,
        sheet_path: str,
        shared_strings: list[str],
    ) -> list[list[str]]:
        root = ET.fromstring(archive.read(sheet_path))
        matrix: list[list[str]] = []
        for row in root.findall(".//x:row", SPREADSHEET_NS):
            values: list[str] = []
            for cell in row.findall("x:c", SPREADSHEET_NS):
                column_index = self._column_index(cell.attrib.get("r", ""))
                while len(values) <= column_index:
                    values.append("")
                values[column_index] = self._cell_value(cell, shared_strings)
            matrix.append(values)
        return matrix

    def _cell_value(self, cell: ET.Element, shared_strings: list[str]) -> str:
        cell_type = cell.attrib.get("t")
        if cell_type == "inlineStr":
            return "".join(node.text or "" for node in cell.findall(".//x:t", SPREADSHEET_NS)).strip()

        value_node = cell.find("x:v", SPREADSHEET_NS)
        if value_node is None or value_node.text is None:
            return ""

        value = value_node.text.strip()
        if cell_type == "s":
            try:
                return shared_strings[int(value)].strip()
            except (IndexError, ValueError):
                return ""
        return value

    def _detect_qa_columns(self, header: list[str]) -> tuple[int | None, int | None]:
        normalized = [cell.strip().lower() for cell in header]
        question_index = self._find_header_index(normalized, self.header_aliases["question"])
        answer_index = self._find_header_index(normalized, self.header_aliases["answer"])
        return question_index, answer_index

    def _find_header_index(self, header: list[str], aliases: set[str]) -> int | None:
        for index, name in enumerate(header):
            if name in aliases:
                return index
        return None

    def _column_index(self, ref: str) -> int:
        letters = "".join(ch for ch in ref if ch.isalpha()).upper()
        index = 0
        for letter in letters:
            index = index * 26 + (ord(letter) - ord("A") + 1)
        return max(index - 1, 0)

    def _value_at(self, values: list[str], index: int) -> str:
        if index >= len(values):
            return ""
        return (values[index] or "").strip()

    def _ensure_reference_notice(self, answer: str) -> str:
        normalized = (answer or "").strip()
        if "仅供参考" in normalized:
            return normalized
        return f"{normalized.rstrip('。')}。以上仅供参考，不替代专业诊断或治疗。"

    def _stable_id(self, normalized_question: str) -> str:
        digest = hashlib.sha1(normalized_question.encode("utf-8")).hexdigest()[:12]
        return f"excel_{digest}"

    def _source_label(self, row: KnowledgeImportRow) -> str:
        return f"excel:{row.source_file}:{row.sheet_name}:row{row.row_number}"

    def _merge_card_metadata(self, target: dict[str, Any], duplicate: dict[str, Any]) -> None:
        target["source"] = self._merge_source(target.get("source", ""), duplicate.get("source", ""))
        target["keywords"] = self._unique_strings(
            list(target.get("keywords", [])) + list(duplicate.get("keywords", []))
        )

    def _merge_source(self, current: str, incoming: str) -> str:
        sources = [item.strip() for item in str(current or "").split(";") if item.strip()]
        if incoming:
            sources.extend(item.strip() for item in str(incoming).split(";") if item.strip())
        return "; ".join(self._unique_strings(sources))

    def _unique_strings(self, values: list[Any]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = str(value).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result
