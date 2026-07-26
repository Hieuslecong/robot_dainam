"""Per-turn grounding + child-safety guard (design 2026-07-26).

Sits between the user aggregator and the LLM. On every LLMContextFrame:

- Knowledge grounding: search ``knowledge/school`` for the last user message.
  Hits are injected as a ``[DỮ LIỆU NHÀ TRƯỜNG]`` system note (evidence WITH
  source metadata). A school-topic question with no hits injects an explicit
  "no data" note so the model must refuse instead of inventing facts.
- Safety: risk keywords (self-harm, bullying, abuse …) inject an ``[AN TOÀN]``
  response guideline and append an alert line to ``artifacts/safety_alerts.jsonl``
  for school staff review. Nothing is ever sent anywhere automatically.

Notes from previous turns are removed before new ones are added, so the
context carries at most one grounding note and one safety note.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from pipecat.frames.frames import Frame
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from app.core.knowledge import KnowledgeStore
from app.logging_utils import get_logger

logger = get_logger(__name__)

GROUNDING_PREFIX = "[DỮ LIỆU NHÀ TRƯỜNG]"
SAFETY_PREFIX = "[AN TOÀN]"

# Queries about these topics MUST be answered from documents or refused.
_SCHOOL_TOPIC = re.compile(
    r"học phí|lịch học|thời khóa biểu|lịch thi|hạn (nộp|đăng ký|chót)|deadline"
    r"|thủ tục|biểu mẫu|đơn (xin|từ)|bảng điểm|bảo lưu|phòng đào tạo|ctsv"
    r"|công tác sinh viên|thư viện|ký túc xá|liên hệ|số điện thoại|email"
    r"|phòng \d|tòa nhà|giờ mở cửa|khai giảng|học kỳ|học phần|tuyển sinh",
    re.IGNORECASE,
)

# Child-safety risk signals. Deliberately broad — a false positive costs one
# gentle system note; a false negative costs a child in need.
_SAFETY_PATTERNS = [
    ("tu_hai", re.compile(
        r"tự tử|tự sát|tự hại|tự làm đau|không muốn sống|muốn chết"
        r"|muốn biến mất|kết thúc cuộc đời|rạch tay", re.IGNORECASE)),
    ("bao_luc", re.compile(
        r"bắt nạt|bị đánh|đánh em|đánh mình|bạo lực|đe dọa|dọa giết|hành hung",
        re.IGNORECASE)),
    ("xam_hai", re.compile(
        r"xâm hại|sàm sỡ|đụng chạm|quấy rối|lạm dụng", re.IGNORECASE)),
]

_SAFETY_NOTE = (
    f"{SAFETY_PREFIX} Người dùng có thể đang gặp nguy hiểm hoặc tổn thương tâm lý. "
    "Ưu tiên tuyệt đối: phản hồi chậm rãi, đồng cảm, KHÔNG phán xét, không giảng "
    "đạo lý, không hứa giữ bí mật. Khuyên bạn ấy tìm NGAY một người lớn tin cậy: "
    "thầy cô chủ nhiệm, phòng tư vấn học đường, hoặc người thân. Nói rõ mình là "
    "trợ lý AI, không thay được chuyên gia. Không hỏi chi tiết gây thêm tổn thương."
)

ALERTS_PATH = Path(__file__).resolve().parents[2] / "artifacts" / "safety_alerts.jsonl"


class TurnGroundingProcessor(FrameProcessor):
    def __init__(
        self,
        context: LLMContext,
        store: KnowledgeStore | None = None,
        alerts_path: Path | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._context = context
        self._store = store or KnowledgeStore()
        self._alerts_path = alerts_path or ALERTS_PATH

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if type(frame).__name__ == "LLMContextFrame":
            try:
                self._ground_turn()
            except Exception as exc:  # a grounding bug must never kill the turn
                logger.error("turn_grounding_failed", error=str(exc))
        await self.push_frame(frame, direction)

    # ── internals ────────────────────────────────────────────────────────────

    def _ground_turn(self) -> None:
        messages = list(self._context.messages)
        query = self._last_user_text(messages)
        if not query:
            return

        # Drop notes injected for earlier turns.
        messages = [m for m in messages if not self._is_note(m)]

        note = self._knowledge_note(query)
        if note:
            messages.append({"role": "system", "content": note})
        if self._safety_hit(query):
            messages.append({"role": "system", "content": _SAFETY_NOTE})
        self._context.set_messages(messages)

    @staticmethod
    def _last_user_text(messages: list) -> str:
        for msg in reversed(messages):
            role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
            if role == "user":
                content = (
                    msg.get("content") if isinstance(msg, dict)
                    else getattr(msg, "content", "")
                )
                return content if isinstance(content, str) else ""
        return ""

    @staticmethod
    def _is_note(msg) -> bool:
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
        content = (
            msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        )
        return role == "system" and isinstance(content, str) and (
            content.startswith(GROUNDING_PREFIX) or content.startswith(SAFETY_PREFIX)
        )

    def _knowledge_note(self, query: str) -> str | None:
        hits = self._store.search(query)
        if hits:
            lines = [
                f"{GROUNDING_PREFIX} Trả lời DỰA TRÊN các tài liệu sau, nêu kèm nguồn:"
            ]
            for hit in hits:
                line = (
                    f"- {hit.answer_evidence} "
                    f"(Nguồn: {hit.source_title}, phiên bản {hit.source_version}, "
                    f"hiệu lực {hit.effective_date})"
                )
                if hit.stale_warning:
                    line += f" [{hit.stale_warning}]"
                lines.append(line)
            logger.info("knowledge_injected", hits=len(hits), query=query[:60])
            return "\n".join(lines)
        if _SCHOOL_TOPIC.search(query):
            logger.info("knowledge_no_data", query=query[:60])
            return (
                f"{GROUNDING_PREFIX} KHÔNG có tài liệu nào cho câu hỏi này. "
                "BẮT BUỘC trả lời rằng mình chưa có thông tin trong dữ liệu nhà "
                "trường và gợi ý hỏi phòng ban phụ trách. CẤM đưa ra bất kỳ con số, "
                "ngày, mức phí, số phòng hay tên người cụ thể nào."
            )
        return None

    def _safety_hit(self, query: str) -> bool:
        matched = [name for name, pattern in _SAFETY_PATTERNS if pattern.search(query)]
        if not matched:
            return False
        try:
            self._alerts_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._alerts_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "categories": matched,
                    "excerpt": query[:100],
                }, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.error("safety_alert_write_failed", error=str(exc))
        logger.warning("safety_alert", categories=matched)
        return True
