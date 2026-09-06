"""Admin blueprint: organization management + basic user administration.

Org CRUD here backs the admin org-management UI
(`frontend-react/src/components/admin/OrgsSection.jsx`, via a new
`api/org.js` client) — `organizations.py` already implements the
underlying storage; this module exposes it over HTTP behind
`require_admin`. User listing/role-management is the natural minimal
counterpart, backed by `auth.py`'s user store.
"""
from flask import Blueprint, jsonify, request

import organizations
from auth import require_admin, VALID_ROLES

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.get("/orgs")
@require_admin
def list_orgs():
    return jsonify({"orgs": organizations.list_orgs()})


@admin_bp.get("/orgs/<org_id>")
@require_admin
def get_org(org_id):
    org = organizations.get_org(org_id)
    if not org:
        return jsonify({"error": "Org not found"}), 404
    return jsonify(org)


@admin_bp.post("/orgs")
@require_admin
def create_org():
    data = request.get_json(silent=True) or {}
    org = organizations.create_org(data)
    return jsonify(org), 201


@admin_bp.put("/orgs/<org_id>")
@require_admin
def update_org(org_id):
    data = request.get_json(silent=True) or {}
    org = organizations.update_org(org_id, data)
    if not org:
        return jsonify({"error": "Org not found"}), 404
    return jsonify(org)


@admin_bp.delete("/orgs/<org_id>")
@require_admin
def delete_org(org_id):
    success = organizations.delete_org(org_id)
    if not success:
        return jsonify({"error": "Org not found"}), 404
    return jsonify({"message": "Org deleted"})


@admin_bp.get("/users")
@require_admin
def list_users():
    from auth import _load_users
    users = _load_users()
    return jsonify({
        "users": [
            {
                "id": u["id"],
                "username": u["username"],
                "role": u["role"],
                "org_id": u.get("org_id", "default"),
                "created_at": u.get("created_at"),
            }
            for u in users.values()
        ]
    })


@admin_bp.put("/users/<user_id>/role")
@require_admin
def update_user_role(user_id):
    from auth import _load_users, _save_users
    data = request.get_json(silent=True) or {}
    new_role = data.get("role")
    if new_role not in VALID_ROLES:
        return jsonify({"error": f"Invalid role. Must be one of {list(VALID_ROLES)}"}), 400
    users = _load_users()
    match = next((k for k, u in users.items() if u["id"] == user_id), None)
    if not match:
        return jsonify({"error": "User not found"}), 404
    users[match]["role"] = new_role
    _save_users(users)
    return jsonify({"message": "Role updated", "user_id": user_id, "role": new_role})
