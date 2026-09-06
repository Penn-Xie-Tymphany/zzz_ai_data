"""文本 JSON 协议层：抽取 → schema 校验 → 结构化错误（供重试使用）。

设计取舍（对应官方 REACT 的教训）：
- 官方用「宽容解析 + 错误回灌」，一旦模型连续输出非法 JSON，步数预算被空转烧掉；
- 本协议层改为「**严格 schema 校验 + 显式错误回灌重试**」：解析失败不再算作一步工具动作，
  而是把 `SchemaError` 的具体原因附在下一次请求里让模型改正，且重试次数单独计预算。

schema 描述格式（自研轻量版，不引三方依赖）：
    {"type": "object", "required": [...], "properties": {key: {...}}}
    字段规则：type(str/int/float/bool/list/dict/any)、items(list 元素规则)、
             min_len、max_len、enum、nullable
"""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class SchemaError(Exception):
    """schema 校验失败，携带人类可读的错误清单。"""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def strip_fences(text: str) -> str:
    match = _FENCE_RE.search(text)
    return match.group(1).strip() if match else text.strip()


def iter_json_candidates(text: str) -> list[Any]:
    """从文本中抽取全部 JSON 对象候选（按出现顺序）。

    用 `raw_decode` 逐个扫描 `{` 起点，能同时兼容：无围栏、带围栏、前后有解释文字的情况。
    """
    candidates: list[Any] = []
    decoder = json.JSONDecoder()
    cleaned = strip_fences(text)
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(cleaned[index:])
        except ValueError:
            continue
        if isinstance(obj, dict):
            candidates.append(obj)
    return candidates


def extract_first_json(text: str) -> dict | None:
    candidates = iter_json_candidates(text)
    return candidates[0] if candidates else None


def validate(obj: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """按轻量 schema 校验对象，返回错误清单（空列表表示通过）。"""
    errors: list[str] = []
    expected = schema.get("type", "any")
    if obj is None:
        if not schema.get("nullable", False):
            errors.append(f"{path}: 不能为 null")
        return errors
    if expected != "any" and not _type_matches(obj, expected):
        return [f"{path}: 类型应为 {expected}，实际为 {type(obj).__name__}"]

    if expected == "list":
        if "min_len" in schema and len(obj) < schema["min_len"]:
            errors.append(f"{path}: 至少需要 {schema['min_len']} 个元素，实际 {len(obj)}")
        if "max_len" in schema and len(obj) > schema["max_len"]:
            errors.append(f"{path}: 最多允许 {schema['max_len']} 个元素，实际 {len(obj)}")
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(obj):
                errors.extend(validate(item, item_schema, f"{path}[{i}]"))
        return errors

    if expected == "str":
        if "min_len" in schema and len(obj) < schema["min_len"]:
            errors.append(f"{path}: 不能为空字符串")
        if "enum" in schema and obj not in schema["enum"]:
            errors.append(f"{path}: 取值必须是 {schema['enum']} 之一，实际为 {obj!r}")
        return errors

    if expected == "int" and "enum" in schema and obj not in schema["enum"]:
        errors.append(f"{path}: 取值必须是 {schema['enum']} 之一，实际为 {obj!r}")
    if "enum" in schema and expected in ("any", "float", "bool") and obj not in schema["enum"]:
        errors.append(f"{path}: 取值必须是 {schema['enum']} 之一，实际为 {obj!r}")
    if expected != "object" and expected != "dict":
        return errors

    if not isinstance(obj, dict):
        return [f"{path}: 应为对象"]
    for key in schema.get("required", []):
        if key not in obj or obj[key] is None:
            errors.append(f"{path}: 缺少必填字段 `{key}`")
    properties: dict[str, Any] = schema.get("properties", {})
    for key, sub_schema in properties.items():
        if key in obj:
            errors.extend(validate(obj[key], sub_schema, f"{path}.{key}"))
    for key in obj:
        if key not in properties and schema.get("additional_properties", True) is False:
            errors.append(f"{path}: 出现未声明字段 `{key}`")
    return errors


def _type_matches(obj: Any, expected: str) -> bool:
    match expected:
        case "any":
            return True
        case "object" | "dict":
            return isinstance(obj, dict)
        case "list":
            return isinstance(obj, list)
        case "str":
            return isinstance(obj, str)
        case "int":
            return isinstance(obj, int) and not isinstance(obj, bool)
        case "float":
            return isinstance(obj, (int, float)) and not isinstance(obj, bool)
        case "bool":
            return isinstance(obj, bool)
        case _:
            return True


def parse_with_schema(text: str, schema: dict[str, Any]) -> dict:
    """抽取并校验，成功返回 dict，失败抛 SchemaError（含全部候选的错误说明）。"""
    candidates = iter_json_candidates(text)
    if not candidates:
        raise SchemaError(["未能在回复中找到 JSON 对象（必须输出且仅输出一个 JSON 对象）"])
    errors: list[str] = []
    for obj in candidates:
        issues = validate(obj, schema)
        if not issues:
            return obj
        errors.extend(issues[:5])
    raise SchemaError(errors[:8])


def dumps_compact(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)
