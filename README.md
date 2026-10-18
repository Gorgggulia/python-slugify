# ЛР1: метрики покриття та мутаційне тестування — артефакти

Проєкт: python-slugify 9.1.3 — https://github.com/un33k/python-slugify
Коміт: 35aca63fc2672cba2c739ff6dff685a4f26a4f9a
Інструменти: Python 3.12.3, pytest 9.1.1, coverage.py 7.16.2, mutmut 3.8.0
(Unidecode 1.4.0, anyascii 0.3.3, text-unidecode 1.3 для опційних бекендів)

## Windows
Див. START_HERE_WINDOWS.txt. Коротко: WSL (Ubuntu) + `bash run_all.sh`, результати в папці results/.

## Відтворення вручну (Linux/WSL)
    git clone https://github.com/un33k/python-slugify.git && cd python-slugify
    git checkout 35aca63fc2672cba2c739ff6dff685a4f26a4f9a
    python3 -m venv .venv && . .venv/bin/activate
    pip install -e . pytest "coverage[toml]" mutmut Unidecode anyascii text-unidecode
    coverage run --branch --source=slugify -m pytest -q
    coverage report -m --fail-under=0
    coverage html -d htmlcov --fail-under=0

У pyproject.toml додати:

    [tool.mutmut]
    paths_to_mutate = ["slugify/"]
    tests_dir = ["tests/"]
    also_copy = ["tools/", "README.md", "CHANGELOG.md", "docs/", "pyproject.toml", "setup.py"]

    mutmut run --max-children 2
    mutmut results
    mutmut show <ім'я_мутанта>
    cd mutants && python ../per_test_analysis/per_test_analysis.py

## Вміст
- coverage/ — звіти покриття (до змін) та підсумки після додавання тестів
- mutation/ — результати mutmut, вижилі до і після, diff-и вижилих
- per_test_analysis/ — скрипт аналізу «який тест вбиває якого мутанта», per_test.json, фаззинг еквівалентності
- added_tests/ — 66 додаткових тестів (мої), що вбивають вижилих мутантів
- logs/ — скорочені логи запусків
