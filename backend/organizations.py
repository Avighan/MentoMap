"""
Organizations / Tenant module for Mento Platform.
Supports lightweight multi-tenancy: orgs can have custom branding,
custom dimension sets, and per-org game catalog visibility.
"""

import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

_ORGS_FILE = os.path.join(os.path.dirname(__file__), "data", "organizations.json")

_DEFAULT_FEATURES = {
    "mystery_room_enabled": False,
}


def default_features() -> dict:
    """Return a copy of the default per-org feature flags."""
    return dict(_DEFAULT_FEATURES)


_DEFAULT_ORG = {
    "id": "default",
    "name": "MentoApp",
    "primary_color": "#6C5CE7",
    "accent_color": "#00B894",
    "logo_url": "",
    "custom_dimensions": None,
    "game_ids": None,
    "features": dict(_DEFAULT_FEATURES),
    "created_at": "2026-01-01T00:00:00+00:00"
}


def _load_orgs() -> list:
    if not os.path.exists(_ORGS_FILE):
        _save_orgs([_DEFAULT_ORG])
        return [_DEFAULT_ORG]
    with open(_ORGS_FILE, "r") as f:
        data = json.load(f)
    return data.get("orgs", [_DEFAULT_ORG])


def _save_orgs(orgs: list) -> None:
    os.makedirs(os.path.dirname(_ORGS_FILE), exist_ok=True)
    with open(_ORGS_FILE, "w") as f:
        json.dump({"orgs": orgs}, f, indent=2)


def get_org(org_id: str) -> Optional[dict]:
    """Return org dict by id, or None if not found."""
    orgs = _load_orgs()
    return next((o for o in orgs if o["id"] == org_id), None)


def get_default_org() -> dict:
    """Return the default org (always exists)."""
    return get_org("default") or _DEFAULT_ORG


def list_orgs() -> list:
    """Return all orgs."""
    return _load_orgs()


def create_org(data: dict) -> dict:
    """Create a new org. Returns the created org dict."""
    orgs = _load_orgs()
    _features = dict(_DEFAULT_FEATURES)
    if isinstance(data.get("features"), dict):
        _features.update({k: v for k, v in data["features"].items() if k in _DEFAULT_FEATURES})
    org = {
        "id": str(uuid.uuid4())[:8],
        "name": data.get("name", "New Organisation"),
        "primary_color": data.get("primary_color", "#6C5CE7"),
        "accent_color": data.get("accent_color", "#00B894"),
        "logo_url": data.get("logo_url", ""),
        "custom_dimensions": data.get("custom_dimensions"),  # None or list of strings
        "game_ids": data.get("game_ids"),  # None = all games visible
        "features": _features,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    orgs.append(org)
    _save_orgs(orgs)
    return org


def update_org(org_id: str, data: dict) -> Optional[dict]:
    """Update an existing org. Returns updated org or None if not found."""
    orgs = _load_orgs()
    for i, o in enumerate(orgs):
        if o["id"] == org_id:
            allowed = ("name", "primary_color", "accent_color", "logo_url",
                       "custom_dimensions", "game_ids")
            for key in allowed:
                if key in data:
                    orgs[i][key] = data[key]
            # Merge feature flags (only known flags, preserve untouched ones)
            if isinstance(data.get("features"), dict):
                current = dict(_DEFAULT_FEATURES)
                current.update(orgs[i].get("features") or {})
                for k, v in data["features"].items():
                    if k in _DEFAULT_FEATURES:
                        current[k] = bool(v)
                orgs[i]["features"] = current
            _save_orgs(orgs)
            return orgs[i]
    return None


def get_org_feature(org_id: Optional[str], flag: str) -> bool:
    """Return whether a feature flag is enabled for the given org.

    Falls back to _DEFAULT_FEATURES (default = disabled) for unknown orgs
    or missing flags so behaviour is safe-by-default.
    """
    if not flag:
        return False
    org = get_org(org_id) if org_id else None
    if org is None:
        org = get_default_org()
    features = org.get("features") if isinstance(org, dict) else None
    if not isinstance(features, dict):
        features = _DEFAULT_FEATURES
    return bool(features.get(flag, _DEFAULT_FEATURES.get(flag, False)))


def delete_org(org_id: str) -> bool:
    """Delete an org. Returns True on success, False if not found or is default."""
    if org_id == "default":
        return False  # cannot delete the default org
    orgs = _load_orgs()
    new_orgs = [o for o in orgs if o["id"] != org_id]
    if len(new_orgs) == len(orgs):
        return False
    _save_orgs(new_orgs)
    return True
