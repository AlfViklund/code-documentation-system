---
id: symbol-anchors
title: Tree-sitter Symbol Extractor & Hash Engine
status: implemented
priority: p0
tags:
- tree-sitter
- ast
- git
anchors:
- type: symbol
  path: docify/src/docify/anchors/symbols.py
  symbol: find_symbol
  kind: function
  body_hash: cfc6d46414baf2dd993573838c23751c45420cb537d455618db0022519cc7315
- type: symbol
  path: docify/src/docify/anchors/symbols.py
  symbol: extract_symbols
  kind: function
  body_hash: 7515c2a9d5b8d30fc81654bcf03e467bdcb41801f749cfc1581c481817b7c59a
- type: symbol
  path: docify/src/docify/anchors/gitops.py
  symbol: GitRepo
  kind: class
  body_hash: 3e0ff113666f75f212c2583dba170f3f66ef9029b0302e198e737b7cd798b0f2
updated_at: '2026-07-18'
verified_commit: f7bbc09f04df53261a13e2b955057316c0057bc7
---

## Что делает

Модуль `anchors` отвечает за извлечение AST-символов из исходного кода на разных языках программирования и расчет устойчивых SHA-256 хешей их тел для отслеживания изменений.

### Основные функции

1. **Экстракция AST символов (`symbols.py`)**:
   - Использует библиотека `tree-sitter` и `tree-sitter-language-pack`.
   - Поддерживает Python, TypeScript, JavaScript и Go.
   - Извлекает функции, классы и квалифицированные имена методов (`ClassName.method_name`).

2. **Нормализация и хеширование тела (`_normalize`, `_hash_body`)**:
   - Удаляет комментарии и избыточные пробельные символы для устранения чувствительности к форматированию кода.
   - **Исключение имени символа**: Узел имени символа исключается из хешируемого тела. Это позволяет системе распознавать переименование метода или функции без изменения его логики (`Symbol Renaming Detection`).

3. **Интеграция с Git (`gitops.py`)**:
   - Класс `GitRepo` обертывает вызовы `git` CLI.
   - Получает blob-хеши файлов, последние коммиты и список измененных/переименованных файлов (`git status --porcelain --find-renames`).

### Ограничения и Edge Cases

- **Строковые литералы и нормализация**: Нормализация кода (`_normalize`) использует регулярные выражения по всему тексту тела символа, включая строковые литералы. Изменение только количества пробелов внутри строкового литерала (например, `"hello  world"` -> `"hello world"`) приводит к одинаковой нормализованной строке и не триггерит предупреждение об изменении хэша тела. Это зафиксировано регрессионным тестом `test_normalize_string_literal_whitespace_limitation`.
