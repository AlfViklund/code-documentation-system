---
id: web-backend
title: FastAPI REST & WebSocket Server
status: implemented
priority: p1
tags:
- web
- fastapi
- websocket
anchors:
- type: symbol
  path: docify/src/docify/web/app.py
  symbol: get_features
  kind: function
  body_hash: 1521471c6c5cc3c87782e68a76a0637b4c42892a4b3e59fea9838c185d70c9b8
- type: symbol
  path: docify/src/docify/web/app.py
  symbol: websocket_endpoint
  kind: function
  body_hash: ef609e156d1571ce00249a4271a61586c34e58f1bdce4d68c0dee450e836935c
updated_at: '2026-07-18'
verified_commit: f7bbc09f04df53261a13e2b955057316c0057bc7
---

## Что делает

Модуль `web` предоставляет асинхронный REST API и WebSocket-сервер на базе `FastAPI` для взаимодействия с фронтенд-дашбордом и внешними системами.

### Ключевые эндпоинты

- `GET /api/features`: Возвращает список всех фич с их статусами старения.
- `GET /api/features/{id}`: Подробные данные по фиче, анкорам и связам.
- `POST /api/features`: Создание или обновление фичи.
- `POST /api/features/{id}/mark-updated`: Сброс предупреждений устаревания и перерасчет хэшей.
- `POST /api/features/{id}/link`: Привязка новых кодовых анкоров.
- `GET /api/specs` & `GET /api/backlog`: Получение списков ТЗ и бэклога.
- `POST /api/specs/ingest`: Парсинг и приёмка новых спецификаций.

### WebSocket и Live Hot-Reloading (`/api/ws`)

Сервер асинхронно отслеживает изменения в папках `docs/features`, `docs/specs` и `docs/backlog` через `watchfiles`. При изменении файлов на диске WebSocket мгновенно отправляет сигнал `reload` в веб-клиент.

Для надежности при работе через VPN или прокси WebSocket отправляет фоновые `ping`-кадры каждые 15 секунд.
