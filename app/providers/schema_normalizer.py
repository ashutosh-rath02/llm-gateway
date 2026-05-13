from __future__ import annotations

from copy import deepcopy
from typing import Any


def normalize_openai_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Normalize JSON Schema to the subset required by OpenAI strict outputs."""
    normalized = deepcopy(schema)
    _normalize_node(normalized)
    return normalized


def _normalize_node(node: Any) -> None:
    if isinstance(node, dict):
        is_object_schema = node.get("type") == "object" or "properties" in node
        if is_object_schema and "additionalProperties" not in node:
            node["additionalProperties"] = False

        properties = node.get("properties")
        if isinstance(properties, dict):
            for child in properties.values():
                _normalize_node(child)

        defs = node.get("$defs")
        if isinstance(defs, dict):
            for child in defs.values():
                _normalize_node(child)

        definitions = node.get("definitions")
        if isinstance(definitions, dict):
            for child in definitions.values():
                _normalize_node(child)

        items = node.get("items")
        if items is not None:
            _normalize_node(items)

        prefix_items = node.get("prefixItems")
        if isinstance(prefix_items, list):
            for child in prefix_items:
                _normalize_node(child)

        for key in ("anyOf", "oneOf", "allOf"):
            variants = node.get(key)
            if isinstance(variants, list):
                for child in variants:
                    _normalize_node(child)

    elif isinstance(node, list):
        for child in node:
            _normalize_node(child)
