from __future__ import annotations

from datetime import datetime
from pathlib import Path


MAX_BACKUPS = 10


class BackupStorage:
    """Gestiona la carpeta de respaldos y sus archivos asociados."""

    def __init__(self, reference_file: str, folder_name: str = "backups"):
        base_dir = Path(reference_file).resolve().parent.parent
        self.folder = base_dir / folder_name
        self.folder.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def is_automatic(name: str) -> bool:
        return name.startswith("backup_") and len(name) == 18

    def build_timestamped_path(self, prefix: str) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return str(self.folder / f"{prefix}_{stamp}.sql")

    def list_backups(self) -> list[dict]:
        backups = []
        for path in self.folder.glob("*.sql"):
            stat = path.stat()
            backups.append({
                "name": path.name,
                "path": str(path),
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M"),
                "mtime": stat.st_mtime,
                "tag": "auto" if self.is_automatic(path.name) else "manual",
            })
        backups.sort(key=lambda item: item["mtime"], reverse=True)
        return backups

    def cleanup_old_backups(self, limit: int = MAX_BACKUPS) -> None:
        for item in self.list_backups()[limit:]:
            try:
                Path(item["path"]).unlink()
            except OSError:
                pass

    def delete_backup(self, path: str) -> None:
        Path(path).unlink()
