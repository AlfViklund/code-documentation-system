---
id: specs-and-backlog
title: Specification Ingestion & Tech Debt Backlog Engine
status: implemented
priority: p1
tags:
- specs
- backlog
- debt
anchors:
- type: symbol
  path: docify/src/docify/core/store.py
  symbol: Store.load_spec_file
  kind: method
  body_hash: fa208e64c92f6d5bc7f763fddffaa8da32104a2cdb00c5e6b46122516a097339
- type: symbol
  path: docify/src/docify/core/store.py
  symbol: Store.load_backlog_file
  kind: method
  body_hash: 29af51322f09771c2b0555f3ac7ad104847fbf02dac23ad560b1678fd688898f
updated_at: '2026-07-18'
verified_commit: f7bbc09f04df53261a13e2b955057316c0057bc7
---

## Что делает

Модуль `specs-and-backlog` реализует жизненный цикл входящих технических заданий (ТЗ) и управление задачами технического долга в проекте.

### Парсинг и приёмка спецификаций (`ingest_spec`)

1. **Формат ТЗ (`docs/specs/<id>.md`)**:
   - Принимает Markdown с YAML-фронтматтером.
   - Метаданные содержат `id`, `title`, `received_at`, `source` и список действий `features: [{id, action}]`.

2. **Автоматическое влияние на фичи**:
   - Если указано действие `action: create`, система автоматически создает новую фичу со статусом `planned`.
   - Если указано действие `action: update`, существующая фича переводится в статус `needs-update`.

### Управление бэклогом (`docs/backlog/<id>.md`)

- Позволяет вести учет техдолга (`type: debt`) и задач роста (`type: growth`).
- Каждая задача имеет приоритет `P0`-`P3`, статус выполнения (`open`, `in-progress`, `done`, `wontfix`) и ссылки на связанные фичи.
