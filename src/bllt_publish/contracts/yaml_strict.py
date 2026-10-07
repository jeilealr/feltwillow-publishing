"""Strict YAML loading for publishing records (ported from the v2 checker's StrictLoader).

Safe loader only (no Python tags), string keys only, duplicate keys rejected. YAML timestamps are kept as
strings by the callers' schemas (quote them). Requires PyYAML.
"""
from __future__ import annotations

import yaml


class StrictLoader(yaml.SafeLoader):
    pass


def _unique_mapping(loader, node, deep=False):
    out = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ValueError("YAML mapping keys must be strings")
        if key in out:
            raise ValueError("duplicate YAML key: " + key)
        out[key] = loader.construct_object(value_node, deep=deep)
    return out


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def load_yaml(text: str):
    return yaml.load(text, Loader=StrictLoader)  # noqa: S506 - StrictLoader derives from SafeLoader
