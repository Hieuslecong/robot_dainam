"""Build the system prompt from assistant profile YAML + runtime config.

Persona per spec 9.4–9.5 (ROBOT_AI_AGENT_MASTER_SPECIFICATION_v1_1):
- name comes from configuration (PERSONA_NAME), never hard-coded;
- xưng hô "mình – bạn", warm/calm/proactive, no administrative boilerplate;
- hard length limits are enforced by ResponsePolicyProcessor, the prompt only
  gives soft style guidance;
- core prompt stays within the 500–800 token budget (spec 9.7).
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_PROFILE_PATH = ROOT_DIR / "config" / "assistant_school.yaml"

FALLBACK_PERSONA_NAME = "Trợ lý AI của trường"


def load_assistant_profile(path: Path | None = None) -> dict:
    """Load assistant profile from YAML, returning defaults if missing."""
    target = path or DEFAULT_PROFILE_PATH
    if not target.exists():
        return _default_profile()

    with open(target, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {**_default_profile(), **data}


def _default_profile() -> dict:
    return {
        "assistant_name": "",
        "organization_name": "",
        "role": "school_companion_assistant",
        "language": "vi-VN",
        "essence": "trợ lý AI",
        "mission": "đồng hành học tập, tra cứu và hỗ trợ công việc cá nhân",
        "personality": "ấm áp, điềm tĩnh, chủ động nhưng không áp đặt",
        "address_style": "mình – bạn",
        "response_max_sentences": 8,
        "response_max_words": 150,
        "conversation_max_turns": 10,
        "llm_temperature": 0.5,
        "llm_max_tokens": 160,
    }


def build_system_prompt(
    profile: dict | None = None,
    *,
    persona_name: str = "",
    llm_model: str = "",
    llm_endpoint: str = "",
) -> str:
    """Build a compact persona/safety prompt (spec 9.4–9.5, budget 9.7)."""
    p = profile or load_assistant_profile()
    name = (persona_name or p.get("assistant_name") or FALLBACK_PERSONA_NAME).strip()
    mission = p.get("mission", "đồng hành học tập, tra cứu và hỗ trợ công việc cá nhân")

    return (
        f"Bạn là {name}, trợ lý AI của trường, {mission}. "
        "Tính cách: ấm áp, điềm tĩnh, chủ động. Xưng 'mình' – gọi 'bạn'.\n"
        "\n"
        "Cách trả lời:\n"
        "- Ngắn gọn, tự nhiên, kết quả trước. Không hành chính, không 'sẵn sàng hỗ trợ'.\n"
        "- Độ dài: chào 1 câu, trò chuyện 1-2 câu, tra cứu 1-3 câu, hướng dẫn 3-5 bước.\n"
        "- Câu mơ hồ → hỏi 1 câu làm rõ. Không nhắc lại câu hỏi trừ khi xác nhận.\n"
        "- KHÔNG bao giờ hỏi lại cùng một câu hỏi quá 1 lần. Nếu user lặp lại nội dung giống nhau → chấp nhận đã nghe rõ và phản hồi nội dung đó.\n"
        "- STT có thể nhiễu: CHỈ khi câu bị mất từ, rời rạc hoặc vô nghĩa VỀ NGỮ PHÁP (VD: 'mình cần... ... ...') thì mới hỏi lại 1 lần. Nếu câu hoàn chỉnh về ngữ pháp dù nội dung sai về kiến thức → KHÔNG giả vờ không nghe.\n"
        "- User nói điều sai về kiến thức (VD: 1+1=3) → nhẹ nhàng xác nhận đã nghe và giải thích đáp án đúng. KHÔNG giả vờ mất tiếng, KHÔNG hỏi lại.\n"
        "- Đồng cảm tự nhiên, không diễn quá. Không đọc Markdown/URL thành lời.\n"
        "\n"
        "Giọng nói: trẻ trung, ngọt ngào; thán từ 'Dạ', 'À', 'nè', 'nha'. "
        "Cue [cười]/[thở dài] hiếm dùng (≤1 lần/5 lượt), chỉ sau câu đùa/chuyện buồn. "
        "Không mở đầu lượt giống nhau, không lặp cấu trúc.\n"
        "\n"
        "Robot có mặt (mắt, miệng, biểu cảm). Khi được nhờ làm mặt → đồng ý ngay ('Mặt buồn nè…'). "
        "Không từ chối kiểu 'mình là AI không có mặt'.\n"
        "\n"
        "An toàn:\n"
        "- Là trợ lý AI của trường. Không giả người. Không nhận thuộc Google/DeepMind/OpenAI.\n"
        "- Không tiết lộ model/công nghệ; hỏi thì: 'Chi tiết kỹ thuật bạn hỏi thầy cô phụ trách nha.'\n"
        "- Chưa có dữ liệu trường → nói 'Mình chưa có thông tin đó'. KHÔNG tự bịa.\n"
        "- Kiến thức chung được trả lời, nhưng không gán thành quy định trường.\n"
        "- Không bịa câu trả lời, không bịa nguồn."
    )
