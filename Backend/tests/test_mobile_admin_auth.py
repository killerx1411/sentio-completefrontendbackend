"""Sentio Mobile Admin integration against the single auth authority.

Covers the boundary the Mobile Admin backend relies on: distinct roles,
a disjoint permission namespace, and access tokens that cannot cross between
the B2B product and Sentio Mobile.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from flask import Flask, jsonify

from auth.constants.applications import (
    APP_B2B,
    APP_MOBILE,
    APPLICATIONS,
    audience_for,
    normalize_application,
)
from auth.constants.roles import (
    ADMIN_ROLES,
    MOBILE_ADMIN_ROLES,
    PRIVILEGED_ROLES,
    ROLE_CONFIG,
    applications_for_role,
    roles_for_application,
)
from auth.db.migrate_mobile_admin import PERMISSION_META
from auth.helpers.jwt_helper import (
    TokenApplicationError,
    decode_token,
    generate_access_token,
    generate_mfa_pending_token,
    token_application,
)
from auth.middleware.auth_middleware import require_auth

BACKEND_DIR = Path(__file__).resolve().parents[1]

MOBILE_SUPER = "mobile_super_admin"
MOBILE_SECONDARY = "mobile_secondary_admin"


def _b2b_permissions() -> set:
    perms = set()
    for role in roles_for_application(APP_B2B):
        perms.update(ROLE_CONFIG[role]["permissions"])
    return perms


def _mobile_permissions() -> set:
    perms = set()
    for role in roles_for_application(APP_MOBILE):
        perms.update(ROLE_CONFIG[role]["permissions"])
    return perms


class TestMobileRolesAreDistinct:
    def test_mobile_roles_registered(self):
        assert MOBILE_ADMIN_ROLES == {MOBILE_SUPER, MOBILE_SECONDARY}
        for role in MOBILE_ADMIN_ROLES:
            assert role in ROLE_CONFIG

    def test_mobile_roles_are_not_aliases_of_b2b_admin_tier(self):
        assert not (MOBILE_ADMIN_ROLES & ADMIN_ROLES)
        for role in MOBILE_ADMIN_ROLES:
            cfg = ROLE_CONFIG[role]
            for b2b_role in ADMIN_ROLES:
                assert cfg["scope"] != ROLE_CONFIG[b2b_role]["scope"]
                assert set(cfg["permissions"]) != set(
                    ROLE_CONFIG[b2b_role]["permissions"]
                )

    def test_permission_namespaces_are_disjoint(self):
        assert not (_mobile_permissions() & _b2b_permissions())
        assert all(p.startswith("mobile.") for p in _mobile_permissions())

    def test_mobile_secondary_is_strictly_narrower_than_super(self):
        sup = set(ROLE_CONFIG[MOBILE_SUPER]["permissions"])
        sec = set(ROLE_CONFIG[MOBILE_SECONDARY]["permissions"])
        assert sec < sup
        assert "mobile.admins.manage" not in sec
        assert "mobile.users.delete" not in sec

    def test_mobile_scopes_unknown_to_b2b_row_level_engine(self):
        # MOBILE_* must never be a scope that widens school/class access.
        for role in MOBILE_ADMIN_ROLES:
            assert ROLE_CONFIG[role]["scope"] not in (
                "GLOBAL",
                "MONITORING",
                "SCHOOL",
                "SCHOOL_FLAGGED",
                "CLASS",
                "ANALYTICS",
            )

    def test_mobile_roles_are_admin_tier_for_assignment_checks(self):
        assert MOBILE_ADMIN_ROLES <= PRIVILEGED_ROLES


class TestApplicationEntitlement:
    def test_role_application_mapping(self):
        assert applications_for_role(MOBILE_SUPER) == {APP_MOBILE}
        assert applications_for_role("Super Admin") == {APP_B2B}
        assert applications_for_role("Unknown Role") == frozenset()

    def test_normalize_application(self):
        assert normalize_application("sentio-mobile") == APP_MOBILE
        assert normalize_application(None) == APP_B2B
        assert normalize_application("not-a-product") is None


class TestTokenApplicationBinding:
    def _mobile_token(self):
        return generate_access_token(
            7,
            "admin@mobile.test",
            roles=[{"name": MOBILE_SUPER}],
            role="MOBILE_SUPER_ADMIN",
            scope_type="MOBILE_GLOBAL",
            permissions=ROLE_CONFIG[MOBILE_SUPER]["permissions"],
            application=APP_MOBILE,
        )

    def _b2b_token(self):
        return generate_access_token(
            8,
            "admin@b2b.test",
            roles=[{"name": "Super Admin"}],
            role="SUPER_ADMIN",
            scope_type="GLOBAL",
            permissions=ROLE_CONFIG["Super Admin"]["permissions"],
            application=APP_B2B,
        )

    def test_mobile_token_carries_mobile_audience_and_app_claim(self):
        payload = decode_token(self._mobile_token())
        assert payload["aud"] == audience_for(APP_MOBILE)
        assert payload["app"] == APP_MOBILE
        assert token_application(payload) == APP_MOBILE

    def test_b2b_audience_is_unchanged(self):
        payload = decode_token(self._b2b_token())
        assert payload["aud"] == "sentio-mind-api"
        assert payload["app"] == APP_B2B

    def test_b2b_token_rejected_when_mobile_expected(self):
        with pytest.raises(TokenApplicationError):
            decode_token(self._b2b_token(), expected_application=APP_MOBILE)

    def test_mobile_token_rejected_when_b2b_expected(self):
        with pytest.raises(TokenApplicationError):
            decode_token(self._mobile_token(), expected_application=APP_B2B)

    def test_mfa_pending_token_keeps_application(self):
        pending = generate_mfa_pending_token(
            7, "admin@mobile.test", application=APP_MOBILE
        )
        payload = decode_token(pending)
        assert payload["type"] == "mfa_pending"
        assert token_application(payload) == APP_MOBILE

    def test_legacy_token_without_app_claim_resolves_to_b2b(self):
        import jwt as pyjwt

        from auth.config import get_config
        from auth.helpers.jwt_helper import JWT_ISSUER

        now = datetime.datetime.utcnow()
        legacy = pyjwt.encode(
            {
                "exp": now + datetime.timedelta(minutes=5),
                "iat": now,
                "sub": "9",
                "email": "legacy@b2b.test",
                "type": "access",
                "jti": "legacy-jti",
                "iss": JWT_ISSUER,
                "aud": "sentio-mind-api",
            },
            get_config().JWT_SECRET_KEY,
            algorithm="HS256",
        )
        assert decode_token(legacy)["app"] == APP_B2B


def _app_with_protected_routes():
    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.route("/mobile-only")
    @require_auth(application=APP_MOBILE)
    def mobile_only():
        return jsonify({"ok": True})

    @app.route("/b2b-only")
    @require_auth(application=APP_B2B)
    def b2b_only():
        return jsonify({"ok": True})

    return app


class TestMiddlewareApplicationEnforcement:
    @pytest.fixture
    def client(self, mock_db):
        _conn, cur = mock_db
        cur.fetchone.return_value = {
            "is_first_login": False,
            "registration_status": "APPROVED",
            "status": "active",
        }
        return _app_with_protected_routes().test_client()

    def _headers(self, application, role):
        token = generate_access_token(
            5,
            "u@test.com",
            roles=[{"name": role}],
            application=application,
        )
        return {"Authorization": f"Bearer {token}"}

    def test_mobile_token_accepted_on_mobile_route(self, client):
        with patch(
            "auth.middleware.auth_middleware.is_token_revoked", return_value=False
        ):
            r = client.get(
                "/mobile-only", headers=self._headers(APP_MOBILE, MOBILE_SUPER)
            )
        assert r.status_code == 200

    def test_b2b_token_rejected_on_mobile_route(self, client):
        with patch(
            "auth.middleware.auth_middleware.is_token_revoked", return_value=False
        ):
            r = client.get(
                "/mobile-only", headers=self._headers(APP_B2B, "Super Admin")
            )
        assert r.status_code == 401

    def test_mobile_token_rejected_on_b2b_route(self, client):
        with patch(
            "auth.middleware.auth_middleware.is_token_revoked", return_value=False
        ):
            r = client.get("/b2b-only", headers=self._headers(APP_MOBILE, MOBILE_SUPER))
        assert r.status_code == 401


class TestLoginApplicationEntitlement:
    def _login(self, mock_db, role, application):
        _conn, cur = mock_db
        cur.fetchone.return_value = {
            "id": 3,
            "email": "u@test.com",
            "full_name": "U",
            "password_hash": "hash",
            "status": "active",
            "registration_status": "APPROVED",
            "mfa_enabled": False,
            "is_first_login": False,
        }
        from auth.services import auth_service

        with patch(
            "auth.services.auth_service.verify_password", return_value=True
        ), patch("auth.services.auth_service.is_locked_out", return_value=False), patch(
            "auth.services.auth_service.clear_attempts"
        ), patch(
            "auth.services.auth_service.record_failed_attempt"
        ), patch(
            "auth.services.auth_service._get_user_roles",
            return_value=[{"id": 1, "name": role}],
        ), patch(
            "auth.services.auth_service._enforce_session_limit"
        ), patch(
            "auth.services.auth_service.create_refresh_token_row"
        ):
            return auth_service.login_user("u@test.com", "pw", application=application)

    def test_mobile_admin_can_log_into_mobile(self, mock_db):
        result = self._login(mock_db, MOBILE_SUPER, APP_MOBILE)
        assert result.get("access_token")
        assert result["application"] == APP_MOBILE
        payload = decode_token(result["access_token"])
        assert payload["app"] == APP_MOBILE
        assert payload["scope_type"] == "MOBILE_GLOBAL"
        assert "mobile.users.read" in payload["permissions"]
        assert "users.read" not in payload["permissions"]

    def test_mobile_admin_cannot_log_into_b2b(self, mock_db):
        result = self._login(mock_db, MOBILE_SUPER, APP_B2B)
        assert result.get("status") == 403
        assert "access_token" not in result

    def test_b2b_admin_cannot_log_into_mobile(self, mock_db):
        result = self._login(mock_db, "Super Admin", APP_MOBILE)
        assert result.get("status") == 403
        assert "access_token" not in result

    def test_unknown_application_rejected(self, mock_db):
        from auth.services import auth_service

        result = auth_service.login_user("u@test.com", "pw", application="sentio-nope")
        assert result["status"] == 400


class TestRefreshKeepsApplication:
    def test_rotation_reissues_token_for_same_application(self, mock_db):
        from auth.services import auth_service

        _conn, cur = mock_db
        cur.fetchone.return_value = {
            "email": "u@test.com",
            "full_name": "U",
            "status": "active",
            "registration_status": "APPROVED",
        }
        rotation = {
            "user_id": 3,
            "refresh_token": "new-raw",
            "remember": False,
            "application": APP_MOBILE,
            "rotated": True,
        }
        with patch(
            "auth.services.auth_service.rotate_refresh_token", return_value=rotation
        ), patch(
            "auth.services.auth_service._get_user_roles",
            return_value=[{"id": 1, "name": MOBILE_SUPER}],
        ):
            result = auth_service.refresh_session("raw")

        assert result["application"] == APP_MOBILE
        assert decode_token(result["access_token"])["app"] == APP_MOBILE

    def test_rotation_denied_when_role_lost_entitlement(self, mock_db):
        from auth.services import auth_service

        _conn, cur = mock_db
        cur.fetchone.return_value = {
            "email": "u@test.com",
            "full_name": "U",
            "status": "active",
            "registration_status": "APPROVED",
        }
        rotation = {
            "user_id": 3,
            "refresh_token": "new-raw",
            "remember": False,
            "application": APP_MOBILE,
            "rotated": True,
        }
        with patch(
            "auth.services.auth_service.rotate_refresh_token", return_value=rotation
        ), patch(
            "auth.services.auth_service._get_user_roles",
            return_value=[{"id": 1, "name": "Super Admin"}],
        ), patch(
            "auth.services.auth_service.revoke_family_for_token"
        ) as revoke:
            result = auth_service.refresh_session("raw")

        assert result["status"] == 403
        assert "access_token" not in result
        revoke.assert_called_once()


class TestDatabaseParity:
    """The DB seed/migration must not drift from ROLE_CONFIG."""

    def test_migration_metadata_covers_every_mobile_permission(self):
        assert _mobile_permissions() <= set(PERMISSION_META)

    @pytest.mark.parametrize("path", ["auth/db/seed.sql", "MIGRATIONS.sql"])
    def test_sql_declares_mobile_roles_and_permissions(self, path):
        sql = (BACKEND_DIR / path).read_text(encoding="utf-8")
        for role in MOBILE_ADMIN_ROLES:
            assert f"'{role}'" in sql, f"{path} missing role {role}"
        for perm in _mobile_permissions():
            assert f"'{perm}'" in sql, f"{path} missing permission {perm}"

    def test_sql_binds_sessions_to_an_application(self):
        sql = (BACKEND_DIR / "MIGRATIONS.sql").read_text(encoding="utf-8")
        assert re.search(r"user_sessions\s+ADD COLUMN IF NOT EXISTS application", sql)
        assert re.search(r"refresh_tokens\s+ADD COLUMN IF NOT EXISTS application", sql)

    def test_every_registered_application_has_a_unique_audience(self):
        auds = [cfg["audience"] for cfg in APPLICATIONS.values()]
        assert len(auds) == len(set(auds))


def _app_with_authority_and_service_routes():
    """A deployment shaped like production b2bapi.sentiomind.in.

    SERVICE_APPLICATIONS=sentio-b2b (resource-server boundary) while the
    authority still mints and identifies both applications.
    """
    from auth.middleware.auth_middleware import require_authority_auth

    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.route("/authority-identity")
    @require_authority_auth
    def authority_identity():
        return jsonify({"ok": True})

    @app.route("/b2b-business")
    @require_auth
    def b2b_business():
        return jsonify({"ok": True})

    return app


class TestAuthorityVersusResourceServerBoundary:
    """SERVICE_APPLICATIONS=sentio-b2b must not lock Mobile Admins out of login.

    b2bapi.sentiomind.in is two things at once: the single authentication
    authority for every product, and the B2B resource server. Narrowing
    SERVICE_APPLICATIONS to sentio-b2b correctly closes the B2B business routes
    to Mobile tokens, but the authority's own identity/MFA endpoints must keep
    serving the sentio-mobile tokens it just minted — otherwise the Mobile Admin
    pages of the B2B console can never resolve a session.
    """

    @pytest.fixture
    def client(self, mock_db):
        _conn, cur = mock_db
        cur.fetchone.return_value = {
            "is_first_login": False,
            "registration_status": "APPROVED",
            "status": "active",
        }
        return _app_with_authority_and_service_routes().test_client()

    def _headers(self, application, role):
        token = generate_access_token(
            7, "admin@test.com", roles=[{"name": role}], application=application
        )
        return {"Authorization": f"Bearer {token}"}

    def _get(self, client, path, application, role):
        with patch(
            "auth.middleware.auth_middleware.is_token_revoked", return_value=False
        ):
            return client.get(path, headers=self._headers(application, role))

    def test_authority_endpoint_accepts_mobile_token(self, client):
        r = self._get(client, "/authority-identity", APP_MOBILE, MOBILE_SUPER)
        assert r.status_code == 200

    def test_authority_endpoint_accepts_b2b_token(self, client):
        r = self._get(client, "/authority-identity", APP_B2B, "Super Admin")
        assert r.status_code == 200

    def test_business_route_still_refuses_mobile_token(self, monkeypatch):
        """The resource-server boundary is unchanged by the authority dial."""
        from auth.middleware import auth_middleware

        monkeypatch.setattr(
            auth_middleware.config, "SERVICE_APPLICATIONS", [APP_B2B], raising=False
        )
        app = Flask(__name__)
        app.config["TESTING"] = True

        @app.route("/b2b-business")
        @require_auth
        def b2b_business():
            return jsonify({"ok": True})

        with patch(
            "auth.middleware.auth_middleware.is_token_revoked", return_value=False
        ), patch(
            "auth.middleware.auth_middleware.get_db_connection"
        ) as mock_conn:
            cur = mock_conn.return_value.cursor.return_value
            cur.fetchone.return_value = {
                "is_first_login": False,
                "registration_status": "APPROVED",
                "status": "active",
            }
            r = app.test_client().get(
                "/b2b-business",
                headers=self._headers(APP_MOBILE, MOBILE_SUPER),
            )
        assert r.status_code == 401

    def test_authority_default_covers_every_registered_application(self):
        """A new product must not silently lose access to /api/auth/me."""
        from auth.config import get_config as _get_config

        assert set(_get_config().AUTH_AUTHORITY_APPLICATIONS) == set(APPLICATIONS)
