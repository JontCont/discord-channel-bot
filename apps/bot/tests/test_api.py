import importlib.util
import unittest
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse


HAS_API_DEPENDENCIES = all(
    importlib.util.find_spec(module) is not None for module in ("fastapi", "httpx")
)

if HAS_API_DEPENDENCIES:
    import httpx

    from cogs.api import ApiConfig, create_api
    from cogs.api.app import SESSION_COOKIE


@dataclass
class FakeSettings:
    auto_voice_limit: int = 8

    def to_dict(self) -> dict[str, Any]:
        return {
            "auto_voice_trigger": "Create Channel",
            "auto_voice_suffix": "Room",
            "auto_voice_limit": self.auto_voice_limit,
            "private_category": "Private",
            "private_trigger": "Create Private",
            "private_suffix": "Room",
            "private_limit": 5,
            "password_channel": "passwords",
            "skill_prefix": "!",
            "skill_panel_channel": "skills",
            "skill_panel_direct_join_skills": ["Music"],
            "xp_per_message_min": 1,
            "xp_per_message_max": 3,
            "xp_message_cooldown": 10,
            "xp_per_voice_tick": 1,
            "xp_voice_interval": 60,
            "xp_daily_base": 5,
            "levelup_channel": "levels",
            "level_roles": [[1, "Member", 0]],
        }


class FakeSettingsService:
    def __init__(self):
        self.settings: dict[int, FakeSettings] = {}
        self.updates: list[tuple[int, dict[str, Any]]] = []

    async def get(self, guild_id: int) -> FakeSettings:
        return self.settings.setdefault(guild_id, FakeSettings())

    async def update(
        self, guild_id: int, changes: dict[str, Any]
    ) -> FakeSettings:
        unknown = set(changes) - {"auto_voice_limit"}
        if unknown:
            raise ValueError(f"unknown setting keys: {', '.join(sorted(unknown))}")
        settings = await self.get(guild_id)
        if "auto_voice_limit" in changes:
            if type(changes["auto_voice_limit"]) is not int:
                raise ValueError("auto_voice_limit must be an integer")
            settings.auto_voice_limit = changes["auto_voice_limit"]
        self.updates.append((guild_id, dict(changes)))
        return settings


class FakeBot:
    def __init__(self, guild_ids: set[int]):
        self.guild_ids = guild_ids

    def get_guild(self, guild_id: int) -> object | None:
        return object() if guild_id in self.guild_ids else None


@unittest.skipUnless(HAS_API_DEPENDENCIES, "FastAPI and HTTPX are not installed")
class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.discord_guilds = [
            {
                "id": "100",
                "name": "Manageable",
                "icon": "iconhash",
                "permissions": str(1 << 5),
            },
            {
                "id": "200",
                "name": "Administrator",
                "icon": None,
                "permissions": str(1 << 3),
            },
            {
                "id": "300",
                "name": "No permission",
                "icon": None,
                "permissions": "0",
            },
            {
                "id": "400",
                "name": "Bot absent",
                "icon": None,
                "permissions": str(1 << 5),
            },
        ]
        self.discord_requests: list[httpx.Request] = []

        def discord_handler(request: httpx.Request) -> httpx.Response:
            self.discord_requests.append(request)
            if request.url.path == "/api/v10/oauth2/token":
                return httpx.Response(
                    200,
                    json={
                        "access_token": "secret-access-token",
                        "refresh_token": "secret-refresh-token",
                        "expires_in": 3600,
                    },
                )
            if request.url.path == "/api/v10/users/@me":
                return httpx.Response(
                    200,
                    json={
                        "id": "42",
                        "username": "tester",
                        "global_name": "Test User",
                        "avatar": "avatarhash",
                    },
                )
            if request.url.path == "/api/v10/users/@me/guilds":
                return httpx.Response(200, json=self.discord_guilds)
            return httpx.Response(404)

        self.discord_http = httpx.AsyncClient(
            transport=httpx.MockTransport(discord_handler)
        )
        self.settings_service = FakeSettingsService()
        self.app = create_api(
            self.settings_service,
            FakeBot({100, 200, 300}),
            config=ApiConfig(
                client_id="client-id",
                client_secret="client-secret",
                redirect_uri="https://example.test/api/auth/callback",
                web_base_url="https://example.test/app",
                session_cookie_secure=True,
            ),
            http_client=self.discord_http,
        )
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app),
            base_url="https://example.test",
            follow_redirects=False,
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.discord_http.aclose()

    def authenticate(self) -> None:
        session_id = self.app.state.session_store.create(
            {"id": "42", "username": "tester", "global_name": None},
            "secret-access-token",
            3600,
        )
        self.client.cookies.set(SESSION_COOKIE, session_id)

    async def test_unauthenticated_endpoints_return_401(self):
        for method, path in (
            ("GET", "/api/me"),
            ("GET", "/api/guilds"),
            ("GET", "/api/guilds/100/settings"),
            ("PUT", "/api/guilds/100/settings"),
        ):
            with self.subTest(method=method, path=path):
                response = await self.client.request(method, path, json={})
                self.assertEqual(response.status_code, 401)

    async def test_guilds_filters_permissions_and_bot_presence(self):
        self.authenticate()

        response = await self.client.get("/api/guilds")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [guild["id"] for guild in response.json()["guilds"]], ["100", "200"]
        )
        manageable = response.json()["guilds"][0]
        self.assertEqual(
            manageable["icon_url"],
            "https://cdn.discordapp.com/icons/100/iconhash.webp?size=96",
        )

    async def test_settings_get_and_update_revalidate_authorization(self):
        self.authenticate()

        fetched = await self.client.get("/api/guilds/100/settings")
        updated = await self.client.put(
            "/api/guilds/100/settings", json={"auto_voice_limit": 12}
        )

        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["settings"]["auto_voice_limit"], 8)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["settings"]["auto_voice_limit"], 12)
        self.assertEqual(self.settings_service.updates, [(100, {"auto_voice_limit": 12})])
        guild_checks = [
            request
            for request in self.discord_requests
            if request.url.path == "/api/v10/users/@me/guilds"
        ]
        self.assertEqual(len(guild_checks), 2)

    async def test_settings_rejects_unauthorized_and_unknown_values(self):
        self.authenticate()

        no_permission = await self.client.get("/api/guilds/300/settings")
        bot_absent = await self.client.get("/api/guilds/400/settings")
        unknown = await self.client.put(
            "/api/guilds/100/settings", json={"not_a_setting": True}
        )

        self.assertEqual(no_permission.status_code, 403)
        self.assertEqual(bot_absent.status_code, 403)
        self.assertEqual(unknown.status_code, 422)
        self.assertIn("unknown setting keys", unknown.json()["detail"])

    async def test_oauth_callback_sets_opaque_secure_http_only_cookie(self):
        login = await self.client.get("/api/auth/login")
        authorization = urlparse(login.headers["location"])
        state_value = parse_qs(authorization.query)["state"][0]

        callback = await self.client.get(
            "/api/auth/callback", params={"code": "one-time-code", "state": state_value}
        )

        self.assertEqual(login.status_code, 302)
        self.assertEqual(parse_qs(authorization.query)["scope"], ["identify guilds"])
        self.assertEqual(callback.status_code, 302)
        self.assertEqual(callback.headers["location"], "https://example.test/app")
        cookies = callback.headers.get_list("set-cookie")
        session_cookie = next(
            cookie for cookie in cookies if cookie.startswith(f"{SESSION_COOKIE}=")
        )
        self.assertIn("HttpOnly", session_cookie)
        self.assertIn("SameSite=lax", session_cookie)
        self.assertIn("Secure", session_cookie)
        self.assertNotIn("secret-access-token", session_cookie)
        self.assertNotIn("secret-refresh-token", callback.text)

        repeated = await self.client.get(
            "/api/auth/callback", params={"code": "another-code", "state": state_value}
        )
        self.assertEqual(repeated.status_code, 400)

    async def test_bot_invite_redirects_to_discord_with_required_permissions(self):
        response = await self.client.get("/api/bot/invite")
        authorization = urlparse(response.headers["location"])
        query = parse_qs(authorization.query)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(authorization.netloc, "discord.com")
        self.assertEqual(query["client_id"], ["client-id"])
        self.assertEqual(query["scope"], ["bot applications.commands"])
        self.assertGreater(int(query["permissions"][0]), 0)

    async def test_logout_invalidates_session_and_clears_cookie(self):
        self.authenticate()

        response = await self.client.post("/api/auth/logout")
        after_logout = await self.client.get("/api/me")

        self.assertEqual(response.status_code, 204)
        self.assertIn(f"{SESSION_COOKIE}=", response.headers["set-cookie"])
        self.assertIn("Max-Age=0", response.headers["set-cookie"])
        self.assertEqual(after_logout.status_code, 401)


if __name__ == "__main__":
    unittest.main()