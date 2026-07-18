---
id: mcp-server
title: FastMCP Agent Integration Server
status: implemented
priority: p1
tags:
- mcp
- fastmcp
- ai-agents
anchors:
- type: symbol
  path: docify/src/docify/mcp/server.py
  symbol: get_overview
  kind: function
  body_hash: 17b55d9af7273459db2b9eb11b01d0ab0cbef589a4eebef3359b75023a66829c
- type: symbol
  path: docify/src/docify/mcp/server.py
  symbol: ingest_spec
  kind: function
  body_hash: 5369ee85bc62ee30299284c368c2509d5b1442992707f744853c12b4763b72ab
updated_at: '2026-07-18'
verified_commit: f7bbc09f04df53261a13e2b955057316c0057bc7
---

## Что делает

Модуль `mcp` реализует интеграцию по протоколу **Model Context Protocol (MCP)** на базе фреймворка `FastMCP`, позволяя AI-кодинг агентам (Claude Code, Cursor, Windsurf, OpenClaude) взаимодействовать с документацией проекта в контексте их рабочих сессий.

### Доступные инструменты и ресурсы

1. **Ресурсы (`docify://overview`)**:
   - Предоставляет краткий сводный обзор всех фич проекта и их текущего состояния старения.

2. **Промпты (`workflow`)**:
   - Шаблонный алгоритм действий для AI-агентов: перед изменением кода проверить связанные фичи через `find_features_for_code`, прочитать бизнес-требования через `get_feature`, обновить документацию и вызвать `mark_updated`.

3. **Инструменты (Tools)**:
   - `list_features`: фильтрация фич по статусу и тегам.
   - `get_feature`: получение полного текста фичи, всех привязанных анкоров и их состояния.
   - `find_features_for_code`: обратный поиск фич по списку файлов `paths`.
   - `check_staleness`: запуск детектора устаревания.
   - `ingest_spec`: сохранение технического задания и автоматическое обновление статусов привязанных фич.
