import json
from pathlib import Path


class SkillInviteRepository:
    """Data layer: persistent storage for skill invite codes."""

    def __init__(self, path: str | Path = "data/skill_invites.json"):
        self.path = Path(path)
        self._codes: dict[str, str] = {}
        self._load()

    @staticmethod
    def _key(guild_id: int, skill_name: str) -> str:
        return f"{guild_id}:{skill_name.strip().lower()}"

    def _load(self):
        try:
            if self.path.exists():
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._codes = {
                        str(k): str(v).upper().strip() for k, v in data.items() if v
                    }
        except (json.JSONDecodeError, OSError):
            self._codes = {}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._codes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get(self, guild_id: int, skill_name: str) -> str | None:
        return self._codes.get(self._key(guild_id, skill_name))

    def set(self, guild_id: int, skill_name: str, code: str):
        self._codes[self._key(guild_id, skill_name)] = code.upper().strip()
        self._save()

    def delete(self, guild_id: int, skill_name: str):
        key = self._key(guild_id, skill_name)
        if key in self._codes:
            del self._codes[key]
            self._save()

    def codes_for_guild(self, guild_id: int) -> set[str]:
        return {
            code for key, code in self._codes.items() if key.startswith(f"{guild_id}:")
        }
