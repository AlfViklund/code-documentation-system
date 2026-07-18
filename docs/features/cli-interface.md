---
id: cli-interface
title: Typer CLI Command Line Interface
status: implemented
priority: p1
tags:
- cli
- typer
anchors:
- type: symbol
  path: docify/src/docify/cli/app.py
  symbol: main
  kind: function
  body_hash: 7ed4810cf9d2059f09fc8c0ebe413f1f56dd2a29afe1055ed7f161479c719d31
- type: symbol
  path: docify/src/docify/cli/app.py
  symbol: mark_updated
  kind: function
  body_hash: 84eba6ab4fca5d9e8e0491b1dbc8d122245f597485d1b0ecfe7689b8876a2306
updated_at: '2026-07-18'
verified_commit: f7bbc09f04df53261a13e2b955057316c0057bc7
---

## Что делает

Модуль `cli` предоставляет удобный консольный интерфейс для разработчиков и скриптов автоматизации на базе библиотеки `Typer`.

### Главные команды

- `docify init`: Инициализирует структуру каталогов `docs/features`, `docs/specs`, `docs/backlog` и создаёт файл настроек `.docify/config.yaml`.
- `docify check [--full] [--fix-anchors]`: Запускает проверку актуальности всей документации проекта.
- `docify feature add <id> --title <title>`: Создает новый стандартный документ фичи.
- `docify link <feature-id> <target>`: Привязывает файл или AST-символ (например, `src/auth.ts::AuthService.login`) к фиче.
- `docify mark-updated <feature-id>`: Обновляет метаданные фичи, пересчитывает хэши и сбрасывает предупреждения об устаревании.
- `docify serve [--host <host>] [--port <port>]`: Запускает локальный веб-дашборд и REST API на базе FastAPI.
- `docify mcp`: Запускает MCP-сервер по протоколу stdio.
- `docify install [--project]`: Настраивает подкючение MCP-сервера в `claude_desktop_config.json`, `.cursor/mcp.json` и создаёт инструкции в `CLAUDE.md`.
