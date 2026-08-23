#!/usr/bin/env bash
set -euo pipefail

# Запоминаем путь, откуда запустили скрипт
START_DIR="$(pwd)"

BASE_DIR="$HOME/Projects/light/light_control/externals/openwrt"
cd "$BASE_DIR"

echo "=== Шаг 1: Обновление индекса пакетов (чтобы OpenWrt увидел light_control) ==="
make package/index

echo "=== Шаг 2: Сборка пакета с подробным логом ==="
# 1. Очищаем пакет
make package/light_control/clean

# 2. Удаляем папку сборки полностью (чтобы исчез CMakeCache.txt и CMakeFiles)
rm -rf build_dir/target-mips_24kc_musl/light_control-*

# 3. (Надёжный вариант) Удаляем все следы CMake для этого пакета
find . -type d -path "*/light_control*" -name "CMakeFiles" -exec rm -rf {} + 2>/dev/null || true
find . -path "*/light_control*" -name "CMakeCache.txt" -delete 2>/dev/null || true

make package/light_control/compile V=s

# Возвращаемся в исходную директорию
cd "$START_DIR"

echo "=== Готово. Вернулись в: $START_DIR ==="

echo "Сборка завершена."

# --- Путь к готовому .ipk (правильный, без дублирования externals/openwrt) ---
IPK_PATH="${BASE_DIR}/bin/packages/mips_24kc/light_control/light_control_1.0.23-1_mips_24kc.ipk"

if [[ ! -f "$IPK_PATH" ]]; then
  echo "Ошибка: .ipk не найден по пути: $IPK_PATH" >&2
  exit 1
fi

echo "=== Пакет найден: ==="
ls -lh "$IPK_PATH"
