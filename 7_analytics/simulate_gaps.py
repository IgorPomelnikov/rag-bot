import os
import shutil
from pathlib import Path


KB_DIR = Path(__file__).resolve().parents[1] / "2_knowledge_base" / "knowledge_base"
GAPS_DIR = Path(__file__).resolve().parent / "gaps_backup"

# 2-3 ключевые сущности для искусственных пробелов в покрытии.
TARGET_ENTITIES = [
    "Цирюльник (Оксенфурт).md",
    "Купец (торговец рыбой).md",
    "Шеймус Хольт.md",
]


def move_to_gaps():
    GAPS_DIR.mkdir(parents=True, exist_ok=True)
    moved = []

    for filename in TARGET_ENTITIES:
        src = KB_DIR / filename
        if not src.exists():
            print(f"[WARN] Не найден: {src}")
            continue
        dst = GAPS_DIR / filename
        shutil.move(str(src), str(dst))
        moved.append(filename)
        print(f"[OK] Перемещен в пробелы: {filename}")

    print(f"Итог: перемещено {len(moved)} файлов")


def restore_from_gaps():
    if not GAPS_DIR.exists():
        print("[INFO] Папка пробелов не найдена, восстанавливать нечего")
        return

    restored = []
    for filename in TARGET_ENTITIES:
        src = GAPS_DIR / filename
        if not src.exists():
            continue
        dst = KB_DIR / filename
        shutil.move(str(src), str(dst))
        restored.append(filename)
        print(f"[OK] Восстановлен: {filename}")

    print(f"Итог: восстановлено {len(restored)} файлов")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Создать/откатить искусственные пробелы в базе знаний")
    parser.add_argument(
        "--restore",
        action="store_true",
        help="Восстановить удаленные сущности из gaps_backup обратно в knowledge_base",
    )
    args = parser.parse_args()

    if args.restore:
        restore_from_gaps()
    else:
        move_to_gaps()
