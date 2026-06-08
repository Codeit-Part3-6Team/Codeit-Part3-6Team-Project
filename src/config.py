from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_config(path: str | Path) -> dict[str, Any]:
    """Load an experiment config.

    PyYAML is used when available. The fallback parser exists so the tiny smoke
    pipeline can still run in very minimal environments, but production-style
    configs should be parsed with PyYAML via `requirements.txt`.
    """
    config_path = Path(path)
    text = config_path.read_text(encoding="utf-8")
    try:
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
    """Copy the config used for a run into the experiment artifact directory."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    source = Path(config_path)
    (output / filename).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    """Write UTF-8 JSON with stable indentation for human-readable artifacts."""
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the small YAML subset used by scaffold configs.

    This is intentionally limited to nested dictionaries, simple lists, and
    scalar values. It is not a full YAML implementation.
    """
    lines = [
        raw.rstrip()
        for raw in text.splitlines()
        if raw.strip() and not raw.lstrip().startswith("#")
    ]
    index = 0

    def parse_block(indent: int) -> Any:
        nonlocal index
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
    """Convert a simple YAML scalar into a Python value."""
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
