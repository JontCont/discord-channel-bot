import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import urlencode

import httpx
import discord as discord_api
from fastapi import Body, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from cogs.repository.skill_invite_repository import SkillInviteRepository
from cogs.service.guild_settings_service import GuildSettingsService
from cogs.service.skill_service import SkillService
from cogs.slash.party import PartyCommands
from cogs.slash.skill_commands import SkillCommands


logger = logging.getLogger(__name__)

DISCORD_API_URL = "https://discord.com/api/v10"
DISCORD_AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
SESSION_COOKIE = "discord_bot_session"
STATE_COOKIE = "discord_oauth_state"
ADMINISTRATOR = 1 << 3
MANAGE_GUILD = 1 << 5
BOT_INVITE_PERMISSIONS = sum(
    1 << bit
    for bit in (
        10,  # View channels
        13,  # Manage channels
        14,  # Manage roles
        16,  # Manage webhooks
        20,  # Manage messages
        21,  # Embed links
        22,  # Attach files
        26,  # Connect
        27,  # Speak
        28,  # Move members
        34,  # Manage threads
        38,  # Send messages in threads
    )
)


@dataclass(frozen=True, slots=True)
class ApiConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    web_base_url: str
    session_cookie_secure: bool = True
    session_ttl_seconds: int = 8 * 60 * 60
    state_ttl_seconds: int = 10 * 60

    @classmethod
    def from_env(cls) -> "ApiConfig":
        return cls(
            client_id=os.getenv("DISCORD_CLIENT_ID", ""),
            client_secret=os.getenv("DISCORD_CLIENT_SECRET", ""),
            redirect_uri=os.getenv("DISCORD_REDIRECT_URI", ""),
            web_base_url=os.getenv("WEB_BASE_URL", "/"),
            session_cookie_secure=_env_bool("SESSION_COOKIE_SECURE", False),
        )

    def require_oauth(self) -> None:
        missing = [
            name
            for name, value in (
                ("DISCORD_CLIENT_ID", self.client_id),
                ("DISCORD_CLIENT_SECRET", self.client_secret),
                ("DISCORD_REDIRECT_URI", self.redirect_uri),
            )
            if not value
        ]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Discord OAuth is not configured",
            )


@dataclass(frozen=True, slots=True)
class Session:
    user: dict[str, Any]
    access_token: str
    expires_at: float


class SessionStore(Protocol):
    def create(
        self, user: Mapping[str, Any], access_token: str, ttl_seconds: int
    ) -> str: ...

    def get(self, session_id: str) -> Session | None: ...

    def delete(self, session_id: str) -> None: ...


class StateStore(Protocol):
    def create(self, ttl_seconds: int) -> str: ...

    def consume(self, state: str) -> bool: ...


class InMemorySessionStore:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._sessions: dict[str, Session] = {}

    def create(
        self, user: Mapping[str, Any], access_token: str, ttl_seconds: int
    ) -> str:
        self._purge_expired()
        session_id = secrets.token_urlsafe(32)
        self._sessions[session_id] = Session(
            user=dict(user),
            access_token=access_token,
            expires_at=self._clock() + ttl_seconds,
        )
        return session_id

    def get(self, session_id: str) -> Session | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.expires_at <= self._clock():
            self._sessions.pop(session_id, None)
            return None
        return session

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def _purge_expired(self) -> None:
        now = self._clock()
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if session.expires_at <= now
        ]
        for session_id in expired:
            self._sessions.pop(session_id, None)


class OneTimeStateStore:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._states: dict[str, float] = {}

    def create(self, ttl_seconds: int) -> str:
        self._purge_expired()
        state_value = secrets.token_urlsafe(32)
        self._states[state_value] = self._clock() + ttl_seconds
        return state_value

    def consume(self, state_value: str) -> bool:
        expires_at = self._states.pop(state_value, None)
        return expires_at is not None and expires_at > self._clock()

    def _purge_expired(self) -> None:
        now = self._clock()
        for state_value, expires_at in list(self._states.items()):
            if expires_at <= now:
                self._states.pop(state_value, None)


class DiscordClient:
    def __init__(self, http_client: httpx.AsyncClient, config: ApiConfig):
        self._http_client = http_client
        self._config = config

    async def exchange_code(self, code: str) -> tuple[str, int]:
        response = await self._http_client.post(
            f"{DISCORD_API_URL}/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._config.redirect_uri,
            },
            auth=(self._config.client_id, self._config.client_secret),
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
        access_token = payload["access_token"]
        expires_in = int(payload.get("expires_in", self._config.session_ttl_seconds))
        if not isinstance(access_token, str) or not access_token:
            raise ValueError("Discord returned an invalid access token")
        return access_token, max(1, expires_in)

    async def get_user(self, access_token: str) -> dict[str, Any]:
        payload = await self._get("/users/@me", access_token)
        if not isinstance(payload, dict):
            raise ValueError("Discord returned an invalid user")
        return payload

    async def get_guilds(self, access_token: str) -> list[dict[str, Any]]:
        payload = await self._get("/users/@me/guilds", access_token)
        if not isinstance(payload, list) or any(
            not isinstance(guild, dict) for guild in payload
        ):
            raise ValueError("Discord returned invalid guilds")
        return payload

    async def _get(self, path: str, access_token: str) -> Any:
        response = await self._http_client.get(
            f"{DISCORD_API_URL}{path}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        return response.json()


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    session_id: str
    session: Session


def create_api(
    settings_service: Any,
    discord_bot: Any,
    *,
    config: ApiConfig | None = None,
    http_client: httpx.AsyncClient | None = None,
    session_store: SessionStore | None = None,
    state_store: StateStore | None = None,
) -> FastAPI:
    api_config = config or ApiConfig.from_env()
    sessions = session_store or InMemorySessionStore()
    states = state_store or OneTimeStateStore()
    owns_http_client = http_client is None
    discord_http = http_client or httpx.AsyncClient(timeout=10.0)
    discord = DiscordClient(discord_http, api_config)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            if owns_http_client:
                await discord_http.aclose()

    app = FastAPI(lifespan=lifespan)

    app.state.session_store = sessions
    app.state.state_store = states
    app.state.discord_client = discord

    def require_session(request: Request) -> AuthenticatedSession:
        session_id = request.cookies.get(SESSION_COOKIE)
        session = sessions.get(session_id) if session_id else None
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        return AuthenticatedSession(session_id=session_id, session=session)

    async def current_guilds(auth: AuthenticatedSession) -> list[dict[str, Any]]:
        try:
            return await discord.get_guilds(auth.session.access_token)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN):
                sessions.delete(auth.session_id)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Discord authorization expired",
                ) from None
            logger.warning("Discord guild request failed with status %s", exc.response.status_code)
            raise _discord_unavailable() from None
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            logger.warning("Discord guild request failed", exc_info=True)
            raise _discord_unavailable() from None

    async def require_guild(
        guild_id: int, auth: AuthenticatedSession
    ) -> dict[str, Any]:
        guilds = await current_guilds(auth)
        guild = next(
            (item for item in guilds if str(item.get("id")) == str(guild_id)),
            None,
        )
        if guild is None or not _can_manage_guild(guild) or discord_bot.get_guild(guild_id) is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot manage this guild",
            )
        return guild

    @app.get("/api/auth/login")
    async def login() -> RedirectResponse:
        api_config.require_oauth()
        state_value = states.create(api_config.state_ttl_seconds)
        query = urlencode(
            {
                "response_type": "code",
                "client_id": api_config.client_id,
                "scope": "identify guilds",
                "state": state_value,
                "redirect_uri": api_config.redirect_uri,
            }
        )
        response = RedirectResponse(
            f"{DISCORD_AUTHORIZE_URL}?{query}", status_code=status.HTTP_302_FOUND
        )
        response.set_cookie(
            STATE_COOKIE,
            state_value,
            max_age=api_config.state_ttl_seconds,
            httponly=True,
            secure=api_config.session_cookie_secure,
            samesite="lax",
            path="/api/auth/callback",
        )
        return response

    @app.get("/api/bot/invite")
    async def invite_bot() -> RedirectResponse:
        api_config.require_oauth()
        query = urlencode(
            {
                "client_id": api_config.client_id,
                "scope": "bot applications.commands",
                "permissions": str(BOT_INVITE_PERMISSIONS),
            }
        )
        return RedirectResponse(
            f"{DISCORD_AUTHORIZE_URL}?{query}", status_code=status.HTTP_302_FOUND
        )

    @app.get("/api/auth/callback")
    async def callback(request: Request, code: str, state: str) -> RedirectResponse:
        api_config.require_oauth()
        cookie_state = request.cookies.get(STATE_COOKIE)
        valid_state = bool(cookie_state) and secrets.compare_digest(cookie_state, state)
        valid_state = states.consume(state) and valid_state
        if not valid_state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth state",
            )

        try:
            access_token, token_ttl = await discord.exchange_code(code)
            user = await discord.get_user(access_token)
            _validate_user(user)
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            logger.warning("Discord OAuth callback failed", exc_info=True)
            raise _discord_unavailable() from None

        session_ttl = min(api_config.session_ttl_seconds, token_ttl)
        session_id = sessions.create(user, access_token, session_ttl)
        response = RedirectResponse(api_config.web_base_url, status_code=status.HTTP_302_FOUND)
        response.delete_cookie(STATE_COOKIE, path="/api/auth/callback")
        response.set_cookie(
            SESSION_COOKIE,
            session_id,
            max_age=session_ttl,
            httponly=True,
            secure=api_config.session_cookie_secure,
            samesite="lax",
            path="/",
        )
        return response

    @app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
    async def logout(request: Request, response: Response) -> None:
        session_id = request.cookies.get(SESSION_COOKIE)
        if session_id:
            sessions.delete(session_id)
        response.delete_cookie(
            SESSION_COOKIE,
            path="/",
            secure=api_config.session_cookie_secure,
            httponly=True,
            samesite="lax",
        )

    @app.get("/api/me")
    async def me(auth: AuthenticatedSession = Depends(require_session)) -> dict[str, Any]:
        return {"user": _public_user(auth.session.user)}

    @app.get("/api/guilds")
    async def guilds(
        auth: AuthenticatedSession = Depends(require_session),
    ) -> dict[str, Any]:
        user_guilds = await current_guilds(auth)
        manageable = [
            _public_guild(guild)
            for guild in user_guilds
            if _can_manage_guild(guild)
            and _guild_id(guild) is not None
            and discord_bot.get_guild(_guild_id(guild)) is not None
        ]
        return {"guilds": manageable}

    @app.get("/api/guilds/{guild_id}/settings")
    async def get_settings(
        guild_id: int,
        auth: AuthenticatedSession = Depends(require_session),
    ) -> dict[str, Any]:
        await require_guild(guild_id, auth)
        settings = await settings_service.get(guild_id)
        return {"settings": settings.to_dict()}

    @app.get("/api/guilds/{guild_id}/categories")
    async def get_categories(
        guild_id: int,
        auth: AuthenticatedSession = Depends(require_session),
    ) -> dict[str, Any]:
        await require_guild(guild_id, auth)
        guild = discord_bot.get_guild(guild_id)
        categories = [
            {"id": str(category.id), "name": category.name}
            for category in guild.categories
        ]
        return {"categories": categories}

    @app.get("/api/guilds/{guild_id}/channels")
    async def get_channels(
        guild_id: int,
        auth: AuthenticatedSession = Depends(require_session),
    ) -> dict[str, Any]:
        await require_guild(guild_id, auth)
        guild = discord_bot.get_guild(guild_id)
        channels = [
            {
                "id": str(channel.id),
                "name": channel.name,
                "category": getattr(getattr(channel, "category", None), "name", None),
            }
            for channel in getattr(guild, "text_channels", [])
        ]
        return {"channels": channels}

    fallback_skill_service: SkillService | None = None

    def get_skill_service() -> SkillService:
        nonlocal fallback_skill_service
        skill_cog = discord_bot.get_cog("skill")
        service = getattr(skill_cog, "skill_service", None)
        if isinstance(service, SkillService):
            return service
        if fallback_skill_service is None:
            fallback_skill_service = SkillService(SkillInviteRepository())
        return fallback_skill_service

    def serialize_skill(
        guild: Any,
        settings: Any,
        skill_service: SkillService,
        skill_name: str,
        emoji: str | None,
    ) -> dict[str, Any]:
        prefix = getattr(settings, "skill_prefix", "湯技：")
        direct_skills = tuple(getattr(settings, "skill_panel_direct_join_skills", ()))
        category = skill_service.find_category(guild, skill_name, prefix)
        role = (
            skill_service.find_role(guild, skill_name, prefix, emoji)
            if hasattr(guild, "roles")
            else None
        )
        member_count = len(getattr(role, "members", [])) if role else 0
        invite_code = skill_service.ensure_invite_code(guild.id, skill_name)
        return {
            "name": skill_name,
            "emoji": emoji,
            "category_name": (
                category.name
                if category
                else skill_service.skill_category_name(skill_name, prefix, emoji)
            ),
            "role_name": role.name if role else f"{prefix}{skill_name}",
            "member_count": member_count,
            "invite_code": invite_code,
            "direct_join": skill_name in direct_skills,
        }

    @app.get("/api/guilds/{guild_id}/skills")
    async def get_skills(
        guild_id: int,
        auth: AuthenticatedSession = Depends(require_session),
    ) -> dict[str, Any]:
        await require_guild(guild_id, auth)
        guild = discord_bot.get_guild(guild_id)
        settings = await settings_service.get(guild_id)
        prefix = getattr(settings, "skill_prefix", "湯技：")
        skill_service = get_skill_service()
        skills = [
            serialize_skill(guild, settings, skill_service, name, emoji)
            for name, emoji in skill_service.get_skills(guild, prefix)
        ]
        return {"skills": skills}

    @app.post("/api/guilds/{guild_id}/skills", status_code=status.HTTP_201_CREATED)
    async def create_skill(
        guild_id: int,
        payload: dict[str, Any] = Body(...),
        auth: AuthenticatedSession = Depends(require_session),
    ) -> dict[str, Any]:
        await require_guild(guild_id, auth)
        raw_name = payload.get("name")
        raw_emoji = payload.get("emoji")
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Skill name is required",
            )
        name = raw_name.strip()
        if " " in name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Skill name cannot contain spaces",
            )
        emoji = raw_emoji.strip() if isinstance(raw_emoji, str) and raw_emoji.strip() else None

        guild = discord_bot.get_guild(guild_id)
        settings = await settings_service.get(guild_id)
        prefix = getattr(settings, "skill_prefix", "湯技：")
        auto_voice_trigger = getattr(settings, "auto_voice_trigger", "➕ 點我開房")
        skill_service = get_skill_service()

        if skill_service.find_category(guild, name, prefix):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"湯技「{name}」已經存在",
            )

        role_name = name if name.startswith(prefix) else f"{prefix}{name}"
        try:
            role = await guild.create_role(
                name=role_name,
                colour=SkillCommands._auto_skill_role_color(name),
                mentionable=True,
                reason="Skill create via Web console",
            )
            overwrites = skill_service.skill_overwrites(guild, role)
            category_name = skill_service.skill_category_name(name, prefix, emoji)
            category = await guild.create_category(
                name=category_name,
                overwrites=overwrites,
                reason="Skill create via Web console",
            )
            await category.create_forum(f"{name}-討論")
            await category.create_text_channel(f"{name}-聊天")
            await category.create_voice_channel(auto_voice_trigger)
            skill_service.set_invite_code(guild_id, name)

            skill_cog = discord_bot.get_cog("skill")
            if isinstance(skill_cog, SkillCommands):
                await skill_cog._refresh_panel(guild, settings)
        except discord_api.HTTPException as exc:
            logger.exception("Failed to create skill %s in guild %s", name, guild_id)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to create skill in Discord: {exc}",
            ) from None

        return {"skill": serialize_skill(guild, settings, skill_service, name, emoji)}

    @app.post("/api/guilds/{guild_id}/skills/{skill_name}/regenerate-code")
    async def regenerate_skill_code(
        guild_id: int,
        skill_name: str,
        auth: AuthenticatedSession = Depends(require_session),
    ) -> dict[str, Any]:
        await require_guild(guild_id, auth)
        name = skill_name.strip()
        guild = discord_bot.get_guild(guild_id)
        settings = await settings_service.get(guild_id)
        prefix = getattr(settings, "skill_prefix", "湯技：")
        skill_service = get_skill_service()

        category = skill_service.find_category(guild, name, prefix)
        role = (
            skill_service.find_role(guild, name, prefix)
            if hasattr(guild, "roles")
            else None
        )
        if not category and not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到湯技「{name}」",
            )

        invite_code = skill_service.set_invite_code(guild_id, name)
        return {"invite_code": invite_code}

    @app.delete(
        "/api/guilds/{guild_id}/skills/{skill_name}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def delete_skill(
        guild_id: int,
        skill_name: str,
        auth: AuthenticatedSession = Depends(require_session),
    ) -> None:
        await require_guild(guild_id, auth)
        name = skill_name.strip()
        guild = discord_bot.get_guild(guild_id)
        settings = await settings_service.get(guild_id)
        prefix = getattr(settings, "skill_prefix", "湯技：")
        skill_service = get_skill_service()

        category = skill_service.find_category(guild, name, prefix)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到湯技「{name}」",
            )

        try:
            for channel in list(getattr(category, "channels", [])):
                await channel.delete(reason="Skill delete via Web console")
            await category.delete(reason="Skill delete via Web console")
            role = (
                skill_service.find_role(guild, name, prefix)
                if hasattr(guild, "roles")
                else None
            )
            if role:
                await role.delete(reason="Skill delete via Web console")
            skill_service.delete_invite_code(guild_id, name)

            skill_cog = discord_bot.get_cog("skill")
            if isinstance(skill_cog, SkillCommands):
                await skill_cog._refresh_panel(guild, settings)
        except discord_api.HTTPException as exc:
            logger.exception("Failed to delete skill %s in guild %s", name, guild_id)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to delete skill in Discord: {exc}",
            ) from None

    @app.put("/api/guilds/{guild_id}/settings")
    async def update_settings(
        guild_id: int,
        changes: dict[str, Any] = Body(...),
        auth: AuthenticatedSession = Depends(require_session),
    ) -> dict[str, Any]:
        await require_guild(guild_id, auth)
        try:
            settings = await settings_service.update(guild_id, changes)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from None
        if set(changes) & (GuildSettingsService.PANEL_TEXT_LIMITS.keys() | {
            "skill_panel_channel", "skill_panel_direct_join_skills",
        }):
            guild = discord_bot.get_guild(guild_id)
            channel = discord_api.utils.get(guild.text_channels, name=settings.skill_panel_channel)
            if channel is None:
                logger.warning("Settings saved but community panel channel is missing in guild %s", guild_id)
            else:
                try:
                    skill_cog = discord_bot.get_cog("skill")
                    party_cog = discord_bot.get_cog("party")
                    if not isinstance(skill_cog, SkillCommands) or not isinstance(party_cog, PartyCommands):
                        raise RuntimeError("Community panel commands are not ready.")
                    await skill_cog._refresh_panel(guild, settings)
                    await party_cog._refresh_panel(channel)
                except (discord_api.HTTPException, ValueError, RuntimeError) as exc:
                    logger.exception("Settings saved but panel refresh failed in guild %s", guild_id)
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Settings were saved, but Discord panels could not be fully updated: {exc}",
                    ) from None
        return {"settings": settings.to_dict()}

    return app


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def _discord_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Discord API is unavailable",
    )


def _validate_user(user: Mapping[str, Any]) -> None:
    if not isinstance(user.get("id"), str) or not isinstance(user.get("username"), str):
        raise ValueError("Discord returned an invalid user")


def _public_user(user: Mapping[str, Any]) -> dict[str, Any]:
    avatar = user.get("avatar")
    user_id = str(user["id"])
    return {
        "id": user_id,
        "username": str(user["username"]),
        "global_name": user.get("global_name"),
        "avatar_url": (
            f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.webp?size=128"
            if avatar
            else None
        ),
    }


def _guild_id(guild: Mapping[str, Any]) -> int | None:
    try:
        guild_id = int(guild["id"])
        return guild_id if guild_id > 0 else None
    except (KeyError, TypeError, ValueError):
        return None


def _can_manage_guild(guild: Mapping[str, Any]) -> bool:
    try:
        permissions = int(guild.get("permissions", 0))
    except (TypeError, ValueError):
        return False
    return bool(permissions & (ADMINISTRATOR | MANAGE_GUILD))


def _public_guild(guild: Mapping[str, Any]) -> dict[str, Any]:
    guild_id = str(guild["id"])
    icon = guild.get("icon")
    return {
        "id": guild_id,
        "name": str(guild.get("name", "")),
        "icon": icon,
        "icon_url": (
            f"https://cdn.discordapp.com/icons/{guild_id}/{icon}.webp?size=96"
            if icon
            else None
        ),
    }