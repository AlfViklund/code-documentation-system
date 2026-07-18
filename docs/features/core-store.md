---
id: core-store
title: Core Storage & Models Engine
status: implemented
priority: p0
tags:
- core
- storage
- pydantic
anchors:
- type: symbol
  path: docify/src/docify/core/store.py
  symbol: Store
  kind: class
  body_hash: 31290b5d02fdf945942369e7394a0552645e0988ea7fa05954ce7b5becf17f04
- type: symbol
  path: docify/src/docify/core/models.py
  symbol: Feature
  kind: class
  body_hash: 2ee82946e05989320a883e2ea4c94c27b7e3c0e3ae72eeb33491c355963441ee
- type: symbol
  path: docify/src/docify/core/models.py
  symbol: Spec
  kind: class
  body_hash: 638976eebf30ad47789e58bf1a5c057cfb79e1f5b69d0e746edffa191234941c
- type: symbol
  path: docify/src/docify/core/models.py
  symbol: BacklogItem
  kind: class
  body_hash: 67616556d9e2c5941f0ca109ae5e8107dbac9a5e3e9596eb8cf4c621fba88d75
updated_at: '2026-07-18'
verified_commit: f7bbc09f04df53261a13e2b955057316c0057bc7
---

## Что делает

Модуль `core` отвечает за персистентное хранение всех данных проекта на диске в прозрачном для человека и Git формате (Markdown с YAML-фронтматтером), а также за строгую Pydantic-валидацию структур в Python.

### Основные компоненты

1. **`Store` (`core/store.py`)**:
   - Читает и записывает файлы фич в `docs/features/<id>.md`.
   - Читает и записывает технические спецификации в `docs/specs/<id>.md`.
   - Читает и записывает элементы техдолга и бэклога в `docs/backlog/<id>.md`.
   - Поддерживает кэш-индекс `.docify/index.json` с хэшами последних проверок.
   - Загружает глобальную конфигурацию `.docify/config.yaml`.

2. **`models.py` (`core/models.py`)**:
   - `Feature`: метаданные фичи, список кодовых якорных ссылок (`FileAnchor` или `SymbolAnchor`), статус реализации и текст документации.
   - `Spec`: принятые технические задания с датой, источником и списком привязанных действий к фичам (`create`/`update`).
   - `BacklogItem`: элементы технического долга и перспективного развития (`debt`/`growth`) с приоритетами `P0-P3`.
   - `FeatureCheckResult`: агрегатор статусов старения (`FRESH`, `STALE`, `BROKEN`, `UNIMPLEMENTED`, `EMPTY_BODY`).

### Архитектурные решения

Все данные хранятся прямо в Git-репозитории пользователя без внешней СУБД. Это гарантирует, что документация версионируется вместе с кодом, а ветки и PR естественным образом переносят изменения в документации.
