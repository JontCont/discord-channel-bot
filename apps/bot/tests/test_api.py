import importlib.util
import unittest
from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from typing import Any
from urllib.parse import parse_qs, urlparse


HAS_API_DEPENDENCIES = all(
    importlib.util.find_spec(module) is not None for module in ("fastapi", "httpx")
)

if HAS_API_DEPENDENCIES:
    import httpx

    from api import ApiConfig, create_api
    from api.app import SESSION_COOKIE
    from service.skill_service import SkillService
    from cogs.slash.party import PartyCommands
    from cogs.slash.skill_commands import SkillCommands


@dataclass
class FakeSettings:
    auto_voice_limit: int = 8
    skill_panel_channel: str = "skills"
    skill_panel_title: str = "Skills"

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
            "skill_panel_channel": self.skill_panel_channel,
            "skill_panel_title": self.skill_panel_title,
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
        unknown = set(changes) - {"auto_voice_limit", "skill_panel_title"}
        if unknown:
            raise ValueError(f"unknown setting keys: {', '.join(sorted(unknown))}")
        settings = await self.get(guild_id)
        if "auto_voice_limit" in changes:
            if type(changes["auto_voice_limit"]) is not int:
                raise ValueError("auto_voice_limit must be an integer")
            settings.auto_voice_limit = changes["auto_voice_limit"]
        if "skill_panel_title" in changes:
            settings.skill_panel_title = changes["skill_panel_title"]
        self.updates.append((guild_id, dict(changes)))
        return settings


@dataclass
class FakeCategory:
    id: int
    name: str


@dataclass
class FakeGuild:
    id: int = 100
    categories: list[FakeCategory] = field(default_factory=list)
    text_channels: list[Any] = field(default_factory=list)
    roles: list[Any] = field(default_factory=list)
    default_role: Any = field(default_factory=Mock)


class FakeBot:
    def __init__(self, guild_ids: set[int]):
        self.cogs: dict[str, Any] = {}
        self.guilds = {
            guild_id: FakeGuild(
                id=guild_id,
                categories=[
                    FakeCategory(guild_id + 1, "遊戲術"),
                    FakeCategory(guild_id + 2, "私人包廂"),
                ],
            )
            for guild_id in guild_ids
        }

    def get_guild(self, guild_id: int) -> FakeGuild | None:
        return self.guilds.get(guild_id)

    def get_cog(self, name: str):
        return self.cogs.get(name)


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
        self.bot = FakeBot({100, 200, 300})
        self.app = create_api(
            self.settings_service,
            self.bot,
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
            ("GET", "/api/guilds/100/categories"),
            ("GET", "/api/guilds/100/channels"),
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

    async def test_panel_copy_update_refreshes_both_existing_panels(self):
        self.authenticate()
        skill = Mock(spec=SkillCommands)
        skill._refresh_panel = AsyncMock()
        party = Mock(spec=PartyCommands)
        party._refresh_panel = AsyncMock()
        self.bot.cogs = {"skill": skill, "party": party}
        guild = self.bot.get_guild(100)
        channel = SimpleNamespace(name="skills")
        guild.text_channels = [channel]
        response = await self.client.put(
            "/api/guilds/100/settings", json={"skill_panel_title": "My interests"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["settings"]["skill_panel_title"], "My interests")
        skill._refresh_panel.assert_awaited_once()
        party._refresh_panel.assert_awaited_once_with(channel)

    async def test_failed_panel_refresh_reports_saved_settings_and_retries(self):
        self.authenticate()
        skill = Mock(spec=SkillCommands)
        skill._refresh_panel = AsyncMock()
        party = Mock(spec=PartyCommands)
        party._refresh_panel = AsyncMock(side_effect=RuntimeError("Panel unavailable"))
        self.bot.cogs = {"skill": skill, "party": party}
        self.bot.get_guild(100).text_channels = [SimpleNamespace(name="skills")]
        with self.assertLogs("api.app", level="ERROR"):
            failed = await self.client.put(
                "/api/guilds/100/settings", json={"skill_panel_title": "My interests"},
            )
        self.assertEqual(failed.status_code, 502)
        self.assertIn("Settings were saved", failed.json()["detail"])
        self.assertEqual((await self.settings_service.get(100)).skill_panel_title, "My interests")
        party._refresh_panel.side_effect = None
        retried = await self.client.put(
            "/api/guilds/100/settings", json={"skill_panel_title": "My interests"},
        )
        self.assertEqual(retried.status_code, 200)
        self.assertEqual(party._refresh_panel.await_count, 2)

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

    async def test_categories_returns_guild_categories(self):
        self.authenticate()

        response = await self.client.get("/api/guilds/100/categories")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["categories"],
            [
                {"id": "101", "name": "遊戲術"},
                {"id": "102", "name": "私人包廂"},
            ],
        )

    async def test_channels_returns_guild_text_channels(self):
        self.authenticate()
        guild = self.bot.get_guild(100)
        guild.text_channels = [
            SimpleNamespace(
                id=1001,
                name="📣｜揪團通知",
                category=SimpleNamespace(name="湯技：遊戲術 🎮"),
            ),
            SimpleNamespace(
                id=1002,
                name="一般閒聊",
                category=None,
            ),
        ]

        response = await self.client.get("/api/guilds/100/channels")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["channels"],
            [
                {"id": "1001", "name": "📣｜揪團通知", "category": "湯技：遊戲術 🎮"},
                {"id": "1002", "name": "一般閒聊", "category": None},
            ],
        )

    async def test_skills_list_create_regenerate_and_delete(self):
        self.authenticate()
        guild = self.bot.get_guild(100)
        codes: dict[str, str] = {}

        class InMemoryInviteRepo:
            def get(self, guild_id: int, skill_name: str):
                return codes.get(f"{guild_id}:{skill_name.lower()}")

            def set(self, guild_id: int, skill_name: str, code: str):
                codes[f"{guild_id}:{skill_name.lower()}"] = code

            def delete(self, guild_id: int, skill_name: str):
                codes.pop(f"{guild_id}:{skill_name.lower()}", None)

            def codes_for_guild(self, guild_id: int):
                return {v for k, v in codes.items() if k.startswith(f"{guild_id}:")}

        skill_cog = Mock(spec=SkillCommands)
        skill_cog.skill_service = SkillService(InMemoryInviteRepo())
        skill_cog._refresh_panel = AsyncMock()
        self.bot.cogs = {"skill": skill_cog}

        async def create_role(name: str, **kwargs):
            role = Mock()
            role.name = name
            role.members = [SimpleNamespace(id=1)]
            role.delete = AsyncMock()
            guild.roles.append(role)
            return role

        async def create_category(name: str, **kwargs):
            cat = SimpleNamespace(
                id=999,
                name=name,
                channels=[],
                create_forum=AsyncMock(),
                create_text_channel=AsyncMock(),
                create_voice_channel=AsyncMock(),
                delete=AsyncMock(),
            )
            guild.categories.append(cat)
            return cat

        guild.create_role = AsyncMock(side_effect=create_role)
        guild.create_category = AsyncMock(side_effect=create_category)

        created = await self.client.post(
            "/api/guilds/100/skills",
            json={"name": "音樂術", "emoji": "🎵"},
        )
        self.assertEqual(created.status_code, 201)
        skill_payload = created.json()["skill"]
        self.assertEqual(skill_payload["name"], "音樂術")
        self.assertEqual(skill_payload["emoji"], "🎵")
        self.assertEqual(skill_payload["category_name"], "湯技：音樂術 🎵")
        self.assertEqual(len(skill_payload["invite_code"]), 8)

        listed = await self.client.get("/api/guilds/100/skills")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["skills"]), 1)

        old_code = skill_payload["invite_code"]
        regenerated = await self.client.post("/api/guilds/100/skills/音樂術/regenerate-code")
        self.assertEqual(regenerated.status_code, 200)
        self.assertEqual(len(regenerated.json()["invite_code"]), 8)
        self.assertNotEqual(regenerated.json()["invite_code"], old_code)

        deleted = await self.client.delete("/api/guilds/100/skills/音樂術")
        self.assertEqual(deleted.status_code, 204)
        self.assertIsNone(codes.get("100:音樂術"))

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