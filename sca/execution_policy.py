from dataclasses import dataclass

@dataclass
class ExecPolicy:
    auto: int = 2
    safe_mode: str = "on"
    dry_run: str = "on"

    @classmethod
    def from_strings(cls, auto: str, safe_mode: str, dry_run: str):
        return cls(auto=int(auto), safe_mode=safe_mode, dry_run=dry_run)

    def allow_write(self) -> bool:
        return self.auto >= 2 and self.dry_run == "off"

    def allow_multi_phase(self) -> bool:
        return self.auto >= 3

    def require_confirmation(self) -> bool:
        return self.auto <= 1
