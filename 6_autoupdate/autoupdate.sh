#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/autoupdate_$(date +%Y%m%d_%H%M%S).log"

log() {
    local msg
    msg="$(date '+%Y-%m-%d %H:%M:%S') [$1] $2"
    echo "$msg" | tee -a "$LOG_FILE"
}

cleanup_old_logs() {
    local keep=10
    local count
    count=$(find "$LOG_DIR" -name 'autoupdate_*.log' -type f | wc -l)
    if [ "$count" -gt "$keep" ]; then
        find "$LOG_DIR" -name 'autoupdate_*.log' -type f -printf '%T@ %p\n' \
            | sort -n \
            | head -n $(( count - keep )) \
            | cut -d' ' -f2- \
            | xargs rm -f
        log "INFO" "Очищено $(( count - keep )) старых лог-файлов"
    fi
}

# ──────────────────────────────────────────────
log "INFO" "=========================================="
log "INFO" "Автообновление индекса — старт"
log "INFO" "=========================================="

# 1. Получение документов из источника (Ведьмак-вики)
log "INFO" "[1/3] Сканирование источника и загрузка документов..."
WIKI_SCRIPT="$PROJECT_ROOT/2_knowledge_base/get_witcher_wiki.py"

if [ -f "$WIKI_SCRIPT" ]; then
    log "INFO" "Запуск $WIKI_SCRIPT"
    if python "$WIKI_SCRIPT" >> "$LOG_FILE" 2>&1; then
        log "INFO" "Загрузка документов завершена успешно"
    else
        log "WARN" "Загрузка документов завершилась с ошибкой (код $?), продолжаем с имеющимися файлами"
    fi
else
    log "WARN" "Скрипт загрузки не найден: $WIKI_SCRIPT — пропуск этапа"
fi

KB_DIR="$PROJECT_ROOT/2_knowledge_base/knowledge_base"
DOC_COUNT=$(find "$KB_DIR" -name '*.md' -type f 2>/dev/null | wc -l)
log "INFO" "Документов в базе знаний: $DOC_COUNT"

# 2. Инкрементальное обновление индекса (чанкинг + эмбеддинги + upsert в ChromaDB)
log "INFO" "[2/3] Обновление векторного индекса (чанкинг → эмбеддинги → ChromaDB)..."
UPDATE_SCRIPT="$SCRIPT_DIR/update_index.py"

if [ -f "$UPDATE_SCRIPT" ]; then
    if LOG_LEVEL=INFO python "$UPDATE_SCRIPT" >> "$LOG_FILE" 2>&1; then
        log "INFO" "Индекс успешно обновлён"
    else
        log "ERROR" "Обновление индекса завершилось с ошибкой (код $?)"
        exit 1
    fi
else
    log "ERROR" "Скрипт обновления не найден: $UPDATE_SCRIPT"
    exit 1
fi

# 3. Итоги
log "INFO" "[3/3] Очистка старых логов..."
cleanup_old_logs

log "INFO" "=========================================="
log "INFO" "Автообновление завершено"
log "INFO" "Лог: $LOG_FILE"
log "INFO" "=========================================="
