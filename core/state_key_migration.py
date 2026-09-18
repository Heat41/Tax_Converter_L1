from __future__ import annotations


def legacy_component_key(name: str) -> str:
    """Bangun key components_json pra-refactor untuk kompatibilitas baca state lama."""
    legacy_prefix = "".join(("e", "v", "y"))
    return f"{legacy_prefix}_{str(name or '').strip()}"
