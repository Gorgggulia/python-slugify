#!/usr/bin/env bash
# Запуск усієї ЛР1 одним скриптом (Linux / WSL Ubuntu). Результати: папка results/ поруч зі скриптом.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$HOME/lab1_work"
OUT="$HERE/results"
COMMIT=35aca63fc2672cba2c739ff6dff685a4f26a4f9a
strip() { sed 's/\x1b\[[0-9;]*m//g' | tr '\r' '\n'; }

for c in git python3; do command -v $c >/dev/null || { echo "Не знайдено $c. Виконайте: sudo apt update && sudo apt install -y git python3 python3-venv python3-pip"; exit 1; }; done
python3 -m venv --help >/dev/null 2>&1 || { echo "Виконайте: sudo apt install -y python3-venv python3-pip"; exit 1; }

rm -rf "$WORK" "$OUT"; mkdir -p "$WORK" "$OUT"; cd "$WORK"
echo "[1/5] Клонування проєкту й встановлення інструментів..."
git clone -q https://github.com/un33k/python-slugify.git
cd python-slugify && git checkout -q "$COMMIT"
python3 -m venv .venv && . .venv/bin/activate
pip -q install --upgrade pip
pip -q install -e . pytest==9.1.1 "coverage[toml]==7.16.2" mutmut==3.8.0 Unidecode anyascii text-unidecode

echo "[2/5] Покриття (оригінальні тести)..."
coverage erase
coverage run --branch --source=slugify -m pytest -q --color=no -p no:cacheprovider tests 2>&1 | tail -3 | tee "$OUT/pytest_baseline.txt"
coverage combine -q 2>/dev/null || true
coverage report -m --fail-under=0 | tee "$OUT/coverage_baseline.txt"
coverage html -d "$OUT/htmlcov_baseline" --fail-under=0 -q

cat >> pyproject.toml <<'EOF'

[tool.mutmut]
paths_to_mutate = ["slugify/"]
tests_dir = ["tests/"]
also_copy = ["tools/", "README.md", "CHANGELOG.md", "docs/", "pyproject.toml", "setup.py"]
pytest_add_cli_args = ["-p", "no:cacheprovider"]
EOF

summ() { # $1 = label
  mutmut results --all true 2>/dev/null | strip > "$OUT/mutmut_all_$1.txt"
  K=$(grep -c ': killed' "$OUT/mutmut_all_$1.txt" || true); S=$(grep -c ': survived' "$OUT/mutmut_all_$1.txt" || true)
  T=$((K+S)); echo "$1: усього=$T вбито=$K вижило=$S mutation score=$(python3 -c "print(round(100*$K/$T,2))")%" | tee -a "$OUT/SUMMARY.txt"
}

echo "[3/5] Мутаційне тестування (оригінальні тести), кілька хвилин..."
rm -rf mutants
mutmut run --max-children 2 > "$OUT/mutmut_run_baseline.log" 2>&1 || true
summ baseline

echo "[4/5] Додаємо 66 тестів і повторюємо..."
cp "$HERE/added_tests/test_mutation_killers.py" tests/
coverage erase
coverage run --branch --source=slugify -m pytest -q --color=no -p no:cacheprovider tests 2>&1 | tail -3 | tee "$OUT/pytest_after.txt"
coverage combine -q 2>/dev/null || true
coverage report -m --fail-under=0 | tee "$OUT/coverage_after.txt"
rm -rf mutants
mutmut run --max-children 2 > "$OUT/mutmut_run_after.log" 2>&1 || true
summ after

echo "[5/5] Готово. Результати: $OUT"
