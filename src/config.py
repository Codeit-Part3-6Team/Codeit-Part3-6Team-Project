from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_config(path: str | Path) -> dict[str, Any]:
    """실험 설정 파일을 읽어 dict로 반환합니다.

    기본은 PyYAML을 사용합니다. 다만 smoke test가 아주 최소 환경에서도
    돌아갈 수 있도록 작은 fallback parser를 함께 둡니다.
    """
    config_path = Path(path)
    # Windows/Excel/일부 에디터가 붙인 UTF-8 BOM이 최상위 key에 섞이지 않게 제거합니다.
    text = config_path.read_text(encoding="utf-8-sig")
    try:
        # 팀 프로젝트에서는 PyYAML을 쓰는 것이 기본이고, fallback은 최소 실행을 위한 안전망입니다.
        import yaml  # type: ignore
    except ImportError:
        return _parse_simple_yaml(text)
    loaded = yaml.safe_load(text)
    return loaded or {}


def write_config_copy(
    config_path: str | Path,
    output_dir: str | Path,
    filename: str = "config.yaml",
) -> None:
    """실험에 사용한 config를 산출물 폴더에 복사합니다."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    source = Path(config_path)
    (output / filename).write_text(source.read_text(encoding="utf-8-sig"), encoding="utf-8")


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    """사람이 읽기 좋은 UTF-8 JSON 산출물을 저장합니다."""
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """스캐폴드 config에서 쓰는 작은 YAML 부분집합만 파싱합니다.

    dict, 단순 list, 기본 scalar 정도만 지원합니다. 완전한 YAML parser가
    아니므로 실제 프로젝트 환경에서는 PyYAML 설치를 전제로 봅니다.
    """
    lines = [
        raw.rstrip()
        for raw in text.splitlines()
        if raw.strip() and not raw.lstrip().startswith("#")
    ]
    index = 0

    def parse_block(indent: int) -> Any:
        nonlocal index
        # 같은 indentation의 첫 줄이 list item이면 list, 아니면 dict로 해석합니다.
        container: Any = [] if _current_line_is_list(index, indent) else {}
        while index < len(lines):
            raw_line = lines[index]
            current_indent = len(raw_line) - len(raw_line.lstrip(" "))
            if current_indent < indent:
                break
            if current_indent > indent:
                raise ValueError(f"Unexpected indentation: {raw_line}")
            line = raw_line.strip()
            if isinstance(container, list):
                if not line.startswith("- "):
                    break
                container.append(_parse_scalar(line[2:].strip()))
                index += 1
                continue
            key, _, value_text = line.partition(":")
            key = key.strip()
            value_text = value_text.strip()
            index += 1
            if value_text:
                container[key] = _parse_scalar(value_text)
            elif index < len(lines):
                # 값이 비어 있으면 다음 indentation block을 nested 값으로 읽습니다.
                next_indent = len(lines[index]) - len(lines[index].lstrip(" "))
                container[key] = parse_block(next_indent) if next_indent > indent else None
            else:
                container[key] = None
        return container

    def _current_line_is_list(line_index: int, indent: int) -> bool:
        if line_index >= len(lines):
            return False
        raw_line = lines[line_index]
        current_indent = len(raw_line) - len(raw_line.lstrip(" "))
        return current_indent == indent and raw_line.strip().startswith("- ")

    return parse_block(0)


def _parse_scalar(value: str) -> Any:
    """문자열 scalar를 bool, number, list, None 등으로 변환합니다."""
    if value in {"", "null", "None", "~"}:
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if value.startswith("[") and value.endswith("]"):
        inside = value[1:-1].strip()
        if not inside:
            return []
        return [_parse_scalar(part.strip()) for part in inside.split(",")]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value.strip("'\"")
