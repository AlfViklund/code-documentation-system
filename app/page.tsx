'use client'

import React, { useEffect, useState, useRef } from 'react'
import {
  ListFilter,
  FileCode,
  AlertTriangle,
  Play,
  RotateCw,
  GitBranch,
  Terminal as TermIcon,
  Tag,
  CheckCircle,
  Plus,
  BookOpen,
  ArrowRight,
  Code,
  Flame,
  LayoutGrid,
  FileText,
  Bookmark,
  Send,
  X,
} from 'lucide-react'

// Backend base URL
const API_BASE = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:4321'

interface Feature {
  id: string
  title: string
  status: 'planned' | 'in-progress' | 'implemented' | 'needs-update' | 'deprecated'
  priority: 'p0' | 'p1' | 'p2' | 'p3'
  tags: string[]
  state: 'fresh' | 'stale' | 'broken' | 'unindexed'
}

interface Spec {
  id: string
  title: string
  received_at?: string
  source?: string
  status: 'open' | 'in-progress' | 'done'
  features: { id: string; action: 'create' | 'update' }[]
  body?: string
}

interface BacklogItem {
  id: string
  title: string
  type: 'debt' | 'growth'
  priority: 'p0' | 'p1' | 'p2' | 'p3'
  features: string[]
  status: 'open' | 'in-progress' | 'done' | 'wontfix'
  body?: string
}

interface Anchor {
  type: 'file' | 'symbol'
  path: string
  state: 'fresh' | 'stale' | 'broken' | 'unindexed'
  detail?: string
  symbol?: string
  kind?: string
  blob?: string
  body_hash?: string
}

interface FeatureDetail extends Feature {
  updated_at?: string
  verified_commit?: string
  anchors: Anchor[]
  relations: { type: string; id: string }[]
  specs: string[]
  body: string
}

export default function Dashboard() {
  const [features, setFeatures] = useState<Feature[]>([])
  const [specs, setSpecs] = useState<Spec[]>([])
  const [backlog, setBacklog] = useState<BacklogItem[]>([])
  
  const [selectedFeature, setSelectedFeature] = useState<FeatureDetail | null>(null)
  const [selectedSpec, setSelectedSpec] = useState<Spec | null>(null)
  
  const [activeTab, setActiveTab] = useState<'features' | 'specs' | 'backlog'>('features')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [filterTag, setFilterTag] = useState<string>('all')

  const [loading, setLoading] = useState<boolean>(false)
  const [logs, setLogs] = useState<string[]>(['[system] docify dashboard ready.'])

  // Ingest modals / state
  const [showIngestSpec, setShowIngestSpec] = useState<boolean>(false)
  const [specInput, setSpecInput] = useState<string>(`---
id: spec-2026-07-oauth
title: Добавить OAuth-провайдеры
received_at: 2026-07-18
source: "ТЗ от продакта"
features:
  - id: auth-login
    action: update
  - id: auth-oauth
    action: create
status: open
---

## Описание ТЗ
Добавить интеграцию с OAuth авторизацией (Google, Yandex).`)

  // Add Feature modal
  const [showAddFeature, setShowAddFeature] = useState<boolean>(false)
  const [newFeatureId, setNewFeatureId] = useState('')
  const [newFeatureTitle, setNewFeatureTitle] = useState('')
  const [newFeaturePriority, setNewFeaturePriority] = useState<'p0' | 'p1' | 'p2' | 'p3'>('p2')
  const [newFeatureTags, setNewFeatureTags] = useState('')

  // Add Backlog Item modal
  const [showAddBacklog, setShowAddBacklog] = useState<boolean>(false)
  const [newBackId, setNewBackId] = useState('')
  const [newBackTitle, setNewBackTitle] = useState('')
  const [newBackType, setNewBackType] = useState<'debt' | 'growth'>('debt')
  const [newBackPriority, setNewBackPriority] = useState<'p0' | 'p1' | 'p2' | 'p3'>('p2')
  const [newBackFeatures, setNewBackFeatures] = useState('')

  // Link Anchor fields
  const [newAnchorType, setNewAnchorType] = useState<'file' | 'symbol'>('file')
  const [newAnchorPath, setNewAnchorPath] = useState('')
  const [newAnchorSymbol, setNewAnchorSymbol] = useState('')

  const logRef = useRef<HTMLDivElement>(null)

  // System logging helper
  const addLog = (msg: string) => {
    setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`])
  }

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [logs])

  // Fetch all data
  const loadData = async () => {
    try {
      setLoading(true)
      const [resF, resS, resB] = await Promise.all([
        fetch(`${API_BASE}/api/features`).then((r) => r.json()),
        fetch(`${API_BASE}/api/specs`).then((r) => r.json()),
        fetch(`${API_BASE}/api/backlog`).then((r) => r.json()),
      ])
      setFeatures(resF)
      setSpecs(resS)
      setBacklog(resB)
      addLog(`Loaded ${resF.length} features, ${resS.length} specs, ${resB.length} backlog items.`)
    } catch (e) {
      addLog(`Connection error to docify API server. Is it running?`)
    } finally {
      setLoading(false)
    }
  }

  const [wsStatus, setWsStatus] = useState<'connected' | 'reconnecting' | 'disconnected'>('disconnected')

  // Initial load + WS live link
  useEffect(() => {
    loadData()

    let ws: WebSocket | null = null
    let retryTimeout: NodeJS.Timeout
    let currentDelay = 1000

    const connectWS = () => {
      const host = typeof window !== 'undefined' ? window.location.host : 'localhost:4321'
      const wsProtocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      ws = new WebSocket(`${wsProtocol}//${host}/api/ws`)

      ws.onopen = () => {
        setWsStatus('connected')
        currentDelay = 1000
        addLog('Live link established via WebSocket.')
      }

      ws.onmessage = (event) => {
        if (event.data === 'ping') {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send('pong')
          }
          return
        }
        if (event.data === 'reload') {
          addLog('Index / docs modified on disk. Checking and reloading...')
          loadData()
          if (selectedFeature) selectFeature(selectedFeature.id)
        }
      }

      ws.onerror = (err) => {
        addLog(`Live link socket error occurred.`)
      }

      ws.onclose = (event) => {
        setWsStatus('reconnecting')
        const reasonStr = event.reason ? `: ${event.reason}` : ''
        addLog(`Live link disconnected (code ${event.code}${reasonStr}). Retrying in ${Math.round(currentDelay / 1000)}s...`)
        retryTimeout = setTimeout(() => {
          connectWS()
        }, currentDelay)
        currentDelay = Math.min(currentDelay * 1.5, 30000)
      }
    }

    connectWS()

    return () => {
      if (ws) ws.close()
      if (retryTimeout) clearTimeout(retryTimeout)
    }
  }, [])

  const selectFeature = async (id: string) => {
    try {
      const detail: FeatureDetail = await fetch(`${API_BASE}/api/features/${id}`).then((r) => r.json())
      setSelectedFeature(detail)
      addLog(`Fetched feature details for "${id}".`)
    } catch (e) {
      addLog(`Failed to fetch details for feature ${id}`)
    }
  }

  const handleMarkUpdated = async (id: string) => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/api/features/${id}/mark-updated`, {
        method: 'POST',
      }).then((r) => r.json())
      if (res.status === 'ok') {
        addLog(`Feature ${id} successfully marked up to date!`)
        loadData()
        selectFeature(id)
      }
    } catch (e) {
      addLog(`Error marking updated: ${e}`)
    } finally {
      setLoading(false)
    }
  }

  const handleLinkAnchor = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFeature) return
    if (!newAnchorPath) return

    try {
      setLoading(true)
      const anchorPayload = {
        type: newAnchorType,
        path: newAnchorPath,
        ...(newAnchorType === 'symbol' ? { symbol: newAnchorSymbol } : {}),
      }
      const res = await fetch(`${API_BASE}/api/features/${selectedFeature.id}/link`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ anchors: [anchorPayload] }),
      }).then((r) => r.json())
      if (res.status === 'ok') {
        addLog(`Linked anchor ${newAnchorPath} to feature ${selectedFeature.id}`)
        setNewAnchorPath('')
        setNewAnchorSymbol('')
        selectFeature(selectedFeature.id)
        loadData()
      }
    } catch (e) {
      addLog(`Error linking anchor: ${e}`)
    } finally {
      setLoading(false)
    }
  }

  const triggerCheck = async () => {
    try {
      setLoading(true)
      addLog('Running documentation staleness check...')
      const res = await fetch(`${API_BASE}/api/check`).then((r) => r.json())
      addLog(`Staleness check complete. Found ${res.length} checked elements.`)
      loadData()
      if (selectedFeature) {
        selectFeature(selectedFeature.id)
      }
    } catch (e) {
      addLog(`Staleness check failed: ${e}`)
    } finally {
      setLoading(false)
    }
  }

  const handleIngestSpec = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/api/specs/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: specInput }),
      }).then((r) => r.json())
      if (res.status === 'ok') {
        addLog(`Technical spec successfully ingested into docs/specs!`)
        setShowIngestSpec(false)
        loadData()
      }
    } catch (e) {
      addLog(`Spec ingestion failed: ${e}`)
    } finally {
      setLoading(false)
    }
  }

  const handleAddFeature = async () => {
    try {
      setLoading(true)
      const payload = {
        id: newFeatureId,
        title: newFeatureTitle,
        priority: newFeaturePriority,
        tags: newFeatureTags.split(',').map((t) => t.trim()).filter(Boolean),
        status: 'planned',
        body: `## Что делает\n\n(Подробное описание фичи ${newFeatureId} )`,
      }
      const res = await fetch(`${API_BASE}/api/features`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }).then((r) => r.json())
      if (res.status === 'ok') {
        addLog(`Feature ${newFeatureId} created.`)
        setShowAddFeature(false)
        setNewFeatureId('')
        setNewFeatureTitle('')
        loadData()
      }
    } catch (e) {
      addLog(`Feature creation failed: ${e}`)
    } finally {
      setLoading(false)
    }
  }

  const handleAddBacklog = async () => {
    try {
      setLoading(true)
      const payload = {
        id: newBackId,
        title: newBackTitle,
        type: newBackType,
        priority: newBackPriority,
        features: newBackFeatures.split(',').map((f) => f.trim()).filter(Boolean),
        status: 'open',
        body: `## Описание\n\n(описание техдолга ${newBackId})`,
      }
      const res = await fetch(`${API_BASE}/api/backlog`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }).then((r) => r.json())
      if (res.status === 'ok') {
        addLog(`Backlog item ${newBackId} logged.`)
        setShowAddBacklog(false)
        setNewBackId('')
        setNewBackTitle('')
        setNewBackFeatures('')
        loadData()
      }
    } catch (e) {
      addLog(`Backlog logging failed: ${e}`)
    } finally {
      setLoading(false)
    }
  }

  // Get distinct tags
  const tagsList = Array.from(new Set(features.flatMap((f) => f.tags || [])))

  const renderFormattedText = (text: string) => {
    const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g)
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} className="font-bold text-zinc-100">{part.slice(2, -2)}</strong>
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return <code key={i} className="bg-zinc-900 border border-zinc-700 text-pink-400 px-1 py-0.5 rounded text-xs">{part.slice(1, -1)}</code>
      }
      return part
    })
  }

  // Styled Markdown Viewer
  const renderMarkdown = (md: string) => {
    if (!md) return <p className="text-zinc-500 italic">No description written yet.</p>
    const lines = md.split('\n')
    const elements: React.ReactNode[] = []
    let inCodeBlock = false
    let codeBlockBuffer: string[] = []

    lines.forEach((line, idx) => {
      if (line.trim().startsWith('```')) {
        if (inCodeBlock) {
          elements.push(
            <pre key={`code-${idx}`} className="bg-zinc-950 border border-cyan-500/30 p-3 rounded text-xs text-cyan-300 font-mono overflow-x-auto my-3 shadow-[0_0_10px_rgba(34,211,238,0.1)]">
              <code>{codeBlockBuffer.join('\n')}</code>
            </pre>
          )
          codeBlockBuffer = []
          inCodeBlock = false
        } else {
          inCodeBlock = true
        }
        return
      }

      if (inCodeBlock) {
        codeBlockBuffer.push(line)
        return
      }

      if (line.startsWith('# ')) {
        elements.push(
          <h1 key={idx} className="text-emerald-400 text-xl font-bold mt-6 mb-2 border-b border-zinc-800 pb-1">
            {renderFormattedText(line.slice(2))}
          </h1>
        )
      } else if (line.startsWith('## ')) {
        elements.push(
          <h2 key={idx} className="text-pink-400 text-lg font-bold mt-4 mb-2">
            {renderFormattedText(line.slice(3))}
          </h2>
        )
      } else if (line.startsWith('### ')) {
        elements.push(
          <h3 key={idx} className="text-cyan-400 text-base font-bold mt-3 mb-1">
            {renderFormattedText(line.slice(4))}
          </h3>
        )
      } else if (line.startsWith('- ') || line.startsWith('* ')) {
        elements.push(
          <div key={idx} className="flex items-start ml-4 my-1">
            <span className="text-pink-500 mr-2">»</span>
            <span>{renderFormattedText(line.slice(2))}</span>
          </div>
        )
      } else if (line.startsWith('> ')) {
        elements.push(
          <blockquote key={idx} className="border-l-2 border-cyan-500 bg-cyan-950/20 px-3 py-1 my-2 italic text-cyan-200">
            {renderFormattedText(line.slice(2))}
          </blockquote>
        )
      } else if (line.trim()) {
        elements.push(<p key={idx} className="my-1.5 leading-relaxed">{renderFormattedText(line)}</p>)
      }
    })

    return <div className="space-y-1 font-mono text-zinc-300 text-sm">{elements}</div>
  }

  return (
    <div className="min-h-screen bg-black text-zinc-50 flex flex-col font-mono selection:bg-pink-500 selection:text-black">
      
      {/* HEADER */}
      <header className="border-b border-pink-500/30 bg-zinc-950/80 backdrop-blur-md sticky top-0 z-50 py-3 px-6 flex items-center justify-between shadow-[0_0_15px_rgba(244,63,94,0.15)]">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded border border-cyan-400 flex items-center justify-center bg-cyan-950/50 shadow-[0_0_10px_rgba(34,211,238,0.3)] animate-pulse">
            <Flame className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-black tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-pink-500 to-emerald-400">
                DOCIFY // Live Doc System
              </h1>
              <span className={`text-[9px] font-bold px-2 py-0.5 rounded border flex items-center space-x-1 ${
                wsStatus === 'connected'
                  ? 'border-emerald-500/40 bg-emerald-950/40 text-emerald-400'
                  : 'border-yellow-500/40 bg-yellow-950/40 text-yellow-400 animate-pulse'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${wsStatus === 'connected' ? 'bg-emerald-400' : 'bg-yellow-400'}`} />
                <span>{wsStatus === 'connected' ? 'LIVE LINK' : 'RECONNECTING'}</span>
              </span>
            </div>
            <p className="text-[10px] text-zinc-500 uppercase tracking-widest">
              Living feature documentation & staleness guard
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <button
            onClick={triggerCheck}
            disabled={loading}
            className="border border-pink-500/50 bg-pink-950/30 hover:bg-pink-500 hover:text-black text-pink-400 px-3 py-1.5 rounded text-xs font-bold transition duration-200 flex items-center space-x-2 shadow-[0_0_10px_rgba(244,63,94,0.2)]"
          >
            <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>RUN STALENESS CHECK</span>
          </button>
          
          <button
            onClick={loadData}
            className="border border-cyan-500/50 bg-cyan-950/30 hover:bg-cyan-400 hover:text-black text-cyan-400 px-3 py-1.5 rounded text-xs font-bold transition duration-200"
          >
            REFRESH
          </button>
        </div>
      </header>

      {/* CORE WORKSPACE */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
        
        {/* SIDE BAR / SELECTOR VIEW */}
        <aside className="w-full md:w-80 border-b md:border-b-0 md:border-r border-zinc-800 bg-zinc-950 flex flex-col">
          
          {/* TAB HEADERS */}
          <div className="grid grid-cols-3 border-b border-zinc-800 text-xs">
            <button
              onClick={() => setActiveTab('features')}
              className={`py-3 text-center transition-colors font-bold ${
                activeTab === 'features'
                  ? 'bg-zinc-900 text-cyan-400 border-b-2 border-cyan-400'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              FEATURES
            </button>
            <button
              onClick={() => setActiveTab('specs')}
              className={`py-3 text-center transition-colors font-bold ${
                activeTab === 'specs'
                  ? 'bg-zinc-900 text-pink-500 border-b-2 border-pink-500'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              SPECS
            </button>
            <button
              onClick={() => setActiveTab('backlog')}
              className={`py-3 text-center transition-colors font-bold ${
                activeTab === 'backlog'
                  ? 'bg-zinc-900 text-emerald-400 border-b-2 border-emerald-400'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              BACKLOG
            </button>
          </div>

          {/* TAB VIEWS */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {activeTab === 'features' && (
              <>
                {/* Filters */}
                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between text-zinc-500">
                    <span className="flex items-center space-x-1">
                      <ListFilter className="w-3 h-3" />
                      <span>FILTERS</span>
                    </span>
                    <button
                      onClick={() => setShowAddFeature(true)}
                      className="text-cyan-400 hover:underline flex items-center space-x-1"
                    >
                      <Plus className="w-3 h-3" />
                      <span>NEW FEATURE</span>
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <select
                      value={filterStatus}
                      onChange={(e) => setFilterStatus(e.target.value)}
                      className="bg-black border border-zinc-800 rounded px-2 py-1 text-zinc-300"
                    >
                      <option value="all">ALL STATUS</option>
                      <option value="planned">PLANNED</option>
                      <option value="in-progress">IN PROGRESS</option>
                      <option value="implemented">IMPLEMENTED</option>
                      <option value="needs-update">NEEDS UPDATE</option>
                    </select>

                    <select
                      value={filterTag}
                      onChange={(e) => setFilterTag(e.target.value)}
                      className="bg-black border border-zinc-800 rounded px-2 py-1 text-zinc-300"
                    >
                      <option value="all">ALL TAGS</option>
                      {tagsList.map((t) => (
                        <option value={t} key={t}>{t.toUpperCase()}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Features List */}
                <div className="space-y-2">
                  {features
                    .filter((f) => filterStatus === 'all' || f.status === filterStatus)
                    .filter((f) => filterTag === 'all' || f.tags.includes(filterTag))
                    .map((f) => {
                      const isSelected = selectedFeature?.id === f.id
                      const stateColors = {
                        fresh: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
                        stale: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30 shadow-[0_0_10px_rgba(234,179,8,0.1)]',
                        broken: 'bg-red-500/20 text-red-500 border-red-500/30 animate-pulse shadow-[0_0_10px_rgba(239,68,68,0.2)]',
                        unindexed: 'bg-zinc-800 text-zinc-400 border-zinc-700',
                      }
                      
                      return (
                        <div
                          key={f.id}
                          onClick={() => selectFeature(f.id)}
                          className={`p-3 rounded border transition cursor-pointer select-none ${
                            isSelected
                              ? 'bg-zinc-900 border-cyan-400'
                              : 'bg-zinc-950 border-zinc-800 hover:border-zinc-700'
                          }`}
                        >
                          <div className="flex items-start justify-between">
                            <span className="font-bold text-sm text-zinc-200 truncate">{f.id}</span>
                            <span className={`text-[8.5px] uppercase font-bold px-1.5 py-0.5 rounded border ${stateColors[f.state] || stateColors.unindexed}`}>
                              {f.state}
                            </span>
                          </div>
                          <p className="text-[11px] text-zinc-400 mt-1 line-clamp-1">{f.title}</p>
                          <div className="flex items-center space-x-2 mt-2">
                            <span className="text-[9px] bg-zinc-900 border border-zinc-800 text-cyan-400 px-1 py-0.2 rounded font-bold uppercase">
                              {f.priority}
                            </span>
                            <span className="text-[9px] text-zinc-500">
                              {f.status.toUpperCase()}
                            </span>
                          </div>
                        </div>
                      )
                    })}
                </div>
              </>
            )}

            {activeTab === 'specs' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between text-xs text-zinc-500">
                  <span>SPECIFICATIONS</span>
                  <button
                    onClick={() => setShowIngestSpec(true)}
                    className="text-pink-500 hover:underline flex items-center space-x-1"
                  >
                    <Plus className="w-3 h-3" />
                    <span>INGEST SPEC</span>
                  </button>
                </div>

                <div className="space-y-2">
                  {specs.map((s) => {
                    const isSelected = selectedSpec?.id === s.id
                    return (
                      <div
                        key={s.id}
                        onClick={() => setSelectedSpec(s)}
                        className={`p-3 rounded border transition cursor-pointer bg-zinc-950 border-zinc-800 ${
                          isSelected ? 'border-pink-500 bg-zinc-900' : 'hover:border-zinc-700'
                        }`}
                      >
                        <div className="flex justify-between items-start">
                          <span className="text-zinc-200 font-bold text-xs truncate">{s.id}</span>
                          <span className={`text-[9px] font-bold px-1.5 py-0.5 border uppercase rounded ${
                            s.status === 'done' ? 'border-emerald-500/30 text-emerald-400' : 'border-pink-500/30 text-pink-400'
                          }`}>
                            {s.status}
                          </span>
                        </div>
                        <p className="text-[11px] text-zinc-400 font-semibold mt-1">{s.title}</p>
                        <p className="text-[9px] text-zinc-500 mt-2">Source: {s.source}</p>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {activeTab === 'backlog' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between text-xs text-zinc-500">
                  <span>BACKLOG & TECH DEBT</span>
                  <button
                    onClick={() => setShowAddBacklog(true)}
                    className="text-emerald-400 hover:underline flex items-center space-x-1"
                  >
                    <Plus className="w-3 h-3" />
                    <span>NEW TASK</span>
                  </button>
                </div>

                <div className="space-y-2">
                  {backlog.map((b) => (
                    <div
                      key={b.id}
                      className="p-3 rounded border bg-zinc-950 border-zinc-800 hover:border-zinc-700"
                    >
                      <div className="flex justify-between items-start">
                        <span className="text-zinc-200 font-bold text-xs">{b.id}</span>
                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase ${
                          b.type === 'debt' ? 'border-pink-500/35 text-pink-400' : 'border-cyan-400/35 text-cyan-400'
                        }`}>
                          {b.type}
                        </span>
                      </div>
                      <p className="text-[11px] text-zinc-300 mt-1 font-semibold">{b.title}</p>
                      <div className="flex items-center space-x-2 mt-2">
                        <span className="text-[9px] bg-zinc-900 border border-zinc-800 text-zinc-400 px-1 py-0.2 rounded font-bold">
                          {b.priority.toUpperCase()}
                        </span>
                        <span className="text-[9px] text-emerald-400 font-bold uppercase">{b.status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </aside>

        {/* MAIN PANEL CONTENT */}
        <main className="flex-1 bg-zinc-900/40 flex flex-col overflow-hidden">
          
          {/* Main workspace logic */}
          {activeTab === 'features' && selectedFeature ? (
            <div className="flex-1 flex flex-col lg:flex-row overflow-y-auto lg:overflow-hidden">
              
              {/* Document/Content View */}
              <div className="flex-1 overflow-y-auto p-6 border-r border-zinc-800 space-y-6">
                
                {/* Feature Metadata summary */}
                <div className="p-4 rounded border border-zinc-800 bg-zinc-950/80">
                  <div className="flex items-center justify-between border-b border-zinc-800 pb-3 mb-3">
                    <div>
                      <span className="text-[10px] text-cyan-400 font-bold uppercase tracking-wider">
                        FEATURE DOCUMENT
                      </span>
                      <h2 className="text-xl font-bold tracking-tight text-zinc-100 mt-1">
                        {selectedFeature.title}
                      </h2>
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleMarkUpdated(selectedFeature.id)}
                        className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/50 hover:bg-emerald-500 hover:text-black font-bold px-3 py-1.5 rounded text-xs transition duration-200 flex items-center space-x-1"
                      >
                        <CheckCircle className="w-3.5 h-3.5" />
                        <span>MARK UPDATED (RESET HASHES)</span>
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-4 gap-4 text-xs">
                    <div>
                      <span className="text-zinc-500 block uppercase text-[9px]">Status</span>
                      <span className="text-zinc-200 mt-0.5 block uppercase tracking-wide font-bold">
                        {selectedFeature.status}
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-500 block uppercase text-[9px]">Priority</span>
                      <span className="text-indigo-400 mt-0.5 block uppercase tracking-wide font-bold">
                        {selectedFeature.priority}
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-500 block uppercase text-[9px]">Verified Commit</span>
                      <span className="text-zinc-400 mt-0.5 block font-mono text-[10px] truncate max-w-[120px]">
                        {selectedFeature.verified_commit ? selectedFeature.verified_commit.slice(0, 8) : 'Not indexed'}
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-500 block uppercase text-[9px]">Last Checked State</span>
                      <span className={`mt-0.5 block font-bold uppercase ${
                        selectedFeature.state === 'fresh' ? 'text-emerald-400' : 'text-yellow-400'
                      }`}>
                        {selectedFeature.state}
                      </span>
                    </div>
                  </div>

                  {selectedFeature.tags && selectedFeature.tags.length > 0 && (
                    <div className="flex items-center space-x-2 mt-3 pt-3 border-t border-zinc-900">
                      <Tag className="w-3.5 h-3.5 text-zinc-500" />
                      <div className="flex items-center gap-1.5">
                        {selectedFeature.tags.map((tag) => (
                          <span key={tag} className="text-[10px] bg-zinc-900 border border-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Feature body content */}
                <div className="p-6 rounded border border-zinc-800 bg-zinc-950/40">
                  {renderMarkdown(selectedFeature.body)}
                </div>

              </div>

              {/* Anchors/Git side panel */}
              <div className="w-96 overflow-y-auto p-6 bg-zinc-950/70 space-y-6">
                
                {/* Code Anchors List */}
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <h3 className="text-xs font-bold text-cyan-400 tracking-wider">
                      CODE ANCHORS ({selectedFeature.anchors.length})
                    </h3>
                  </div>

                  {selectedFeature.anchors.length === 0 ? (
                    <div className="border border-dashed border-zinc-850 p-4 rounded text-center text-xs text-zinc-500 leading-relaxed">
                      This feature is not anchored to any files or symbols yet. Use the tool below to link code.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {selectedFeature.anchors.map((anc, idx) => {
                        const stateColors = {
                          fresh: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
                          stale: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
                          broken: 'text-red-500 bg-red-500/10 border-red-500/20',
                          unindexed: 'text-zinc-400 bg-zinc-800/10 border-zinc-700',
                        }
                        return (
                          <div key={idx} className="border border-zinc-800 bg-black/40 rounded p-3">
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] text-zinc-500 font-bold uppercase">
                                {anc.type} Anchor
                              </span>
                              <span className={`text-[8.5px] uppercase font-bold border rounded px-1.5 py-0.5 ${stateColors[anc.state] || stateColors.unindexed}`}>
                                {anc.state}
                              </span>
                            </div>

                            <p className="text-xs font-mono text-zinc-300 mt-2 truncate select-all">{anc.path}</p>
                            
                            {anc.symbol && (
                              <div className="bg-zinc-900 border border-zinc-850 rounded p-1.5 mt-2 flex items-center justify-between">
                                <span className="text-[10px] text-cyan-300 font-mono truncate">{anc.symbol}</span>
                                <span className="text-[7.5px] uppercase bg-cyan-950 border border-cyan-800 text-cyan-400 px-1 rounded font-mono font-bold">
                                  {anc.kind}
                                </span>
                              </div>
                            )}

                            {anc.detail && (
                              <div className="text-[10px] bg-yellow-950/20 border border-yellow-500/30 text-yellow-300 rounded p-2 mt-2 leading-relaxed whitespace-pre-wrap select-all">
                                {anc.detail}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}

                  {/* Add Anchor Form */}
                  <form onSubmit={handleLinkAnchor} className="border border-zinc-800 bg-black p-4 rounded space-y-3">
                    <h4 className="text-[11px] font-bold text-zinc-400 uppercase">
                      Link Code Anchor
                    </h4>
                    
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <button
                        type="button"
                        onClick={() => setNewAnchorType('file')}
                        className={`py-1 rounded text-center border font-bold ${
                          newAnchorType === 'file' ? 'border-cyan-400 text-cyan-400 bg-cyan-950/10' : 'border-zinc-800 text-zinc-500'
                        }`}
                      >
                        File Anchor
                      </button>
                      <button
                        type="button"
                        onClick={() => setNewAnchorType('symbol')}
                        className={`py-1 rounded text-center border font-bold ${
                          newAnchorType === 'symbol' ? 'border-cyan-400 text-cyan-400 bg-cyan-950/10' : 'border-zinc-800 text-zinc-500'
                        }`}
                      >
                        Symbol Anchor
                      </button>
                    </div>

                    <div className="space-y-1">
                      <label className="text-[10px] text-zinc-500 uppercase block">Relative File Path</label>
                      <input
                        type="text"
                        placeholder="src/login.ts"
                        value={newAnchorPath}
                        onChange={(e) => setNewAnchorPath(e.target.value)}
                        className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-200 outline-none focus:border-cyan-400 font-mono"
                      />
                    </div>

                    {newAnchorType === 'symbol' && (
                      <div className="space-y-1">
                        <label className="text-[10px] text-zinc-500 uppercase block">Qualified Symbol Name</label>
                        <input
                          type="text"
                          placeholder="LoginService.authenticate"
                          value={newAnchorSymbol}
                          onChange={(e) => setNewAnchorSymbol(e.target.value)}
                          className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-200 outline-none focus:border-cyan-400 font-mono"
                        />
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={loading}
                      className="w-full bg-cyan-950 text-cyan-400 border border-cyan-700/50 hover:bg-cyan-400 hover:text-black py-1.5 rounded text-xs font-bold transition duration-200 shadow-sm"
                    >
                      LINK ANCHOR
                    </button>
                  </form>

                </div>

              </div>

            </div>
          ) : activeTab === 'specs' && selectedSpec ? (
            <div className="flex-1 p-6 space-y-6 overflow-y-auto max-w-4xl mx-auto w-full">
              
              <div className="p-4 rounded border border-pink-500/20 bg-zinc-950/80">
                <span className="text-[10px] text-pink-500 font-bold uppercase tracking-wider">
                  Technical Specification
                </span>
                <h2 className="text-xl font-bold tracking-tight text-zinc-100 mt-1">
                  {selectedSpec.title}
                </h2>
                
                <div className="grid grid-cols-3 gap-4 text-xs mt-3 pt-3 border-t border-zinc-900">
                  <div>
                    <span className="text-zinc-500">ID</span>
                    <span className="block text-zinc-200 font-bold mt-0.5">{selectedSpec.id}</span>
                  </div>
                  <div>
                    <span className="text-zinc-500">Received At</span>
                    <span className="block text-zinc-200 font-bold mt-0.5">{selectedSpec.received_at || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-zinc-500">Source</span>
                    <span className="block text-zinc-200 font-bold mt-0.5">{selectedSpec.source || 'N/A'}</span>
                  </div>
                </div>
              </div>

              {/* Ingest mapping summary */}
              <div className="p-4 rounded border border-zinc-800 bg-zinc-950/40 space-y-3">
                <h3 className="text-xs font-bold text-pink-400 uppercase tracking-wider">
                  Impacted features defined in Spec
                </h3>

                <div className="space-y-1.5">
                  {selectedSpec.features.map((f, i) => (
                    <div key={i} className="flex justify-between items-center bg-black/60 p-2 border border-zinc-850 rounded text-xs font-mono">
                      <span>Feature: <strong className="text-cyan-400">{f.id}</strong></span>
                      <span className={`text-[9px] font-bold px-1.5 rounded border uppercase ${
                        f.action === 'create' ? 'border-emerald-500/30 text-emerald-400' : 'border-pink-500/30 text-pink-400'
                      }`}>
                        Action: {f.action}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Spec body markdown */}
              <div className="p-6 rounded border border-zinc-800 bg-zinc-950/60 font-mono">
                {selectedSpec.body ? renderMarkdown(selectedSpec.body) : <p className="text-zinc-500 italic">No notes.</p>}
              </div>

            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 space-y-6">
              <div className="w-16 h-16 rounded-full border border-pink-500/30 bg-pink-950/15 flex items-center justify-center text-pink-500 shadow-[0_0_20px_rgba(244,63,94,0.15)] animate-pulse">
                <BookOpen className="w-8 h-8" />
              </div>
              <div className="max-w-md">
                <h3 className="text-lg font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-pink-500 uppercase tracking-wider">
                  No Feature Selected
                </h3>
                <p className="text-xs text-zinc-500 leading-relaxed mt-2 uppercase tracking-wide">
                  Select a feature from the left panel to inspect its living documentation, verify code anchors state, or link files and AST symbols.
                </p>
              </div>
            </div>
          )}

          {/* LOWER LOGS / CONSOLE SECTION */}
          <footer className="h-44 border-t border-zinc-800 bg-black flex flex-col">
            <div className="bg-zinc-950 px-4 py-1.5 border-b border-zinc-900 flex justify-between items-center text-[10px] text-zinc-400 font-bold uppercase tracking-wider">
              <span className="flex items-center space-x-1.5 text-cyan-400">
                <TermIcon className="w-3 h-3" />
                <span>Console Log / Watch Output</span>
              </span>
              <button
                onClick={() => setLogs(['[system] Console cleared.'])}
                className="text-zinc-500 hover:text-zinc-300 font-normal hover:underline"
              >
                Clear logs
              </button>
            </div>
            
            <div
              ref={logRef}
              className="flex-1 p-3 overflow-y-auto font-mono text-[10px] text-zinc-400 space-y-0.5 leading-relaxed bg-black/85 scrollbar-thin scrollbar-thumb-zinc-800"
            >
              {logs.map((log, index) => (
                <div key={index} className="whitespace-pre-wrap select-all">
                  {log.includes('error') || log.includes('failed') ? (
                    <span className="text-red-500">{log}</span>
                  ) : log.includes('success') || log.includes('successfully') ? (
                    <span className="text-emerald-400">{log}</span>
                  ) : log.includes('Live link') ? (
                    <span className="text-pink-400">{log}</span>
                  ) : (
                    log
                  )}
                </div>
              ))}
            </div>
          </footer>

        </main>
      </div>

      {/* MODALS */}
      
      {/* 1. Ingest Spec Modal */}
      {showIngestSpec && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-zinc-950 border border-pink-500 rounded p-6 w-full max-w-2xl space-y-4 shadow-[0_0_30px_rgba(244,63,94,0.3)]">
            <div className="flex justify-between items-center border-b border-zinc-900 pb-3">
              <h3 className="text-sm font-bold text-pink-400 uppercase tracking-widest flex items-center space-x-2">
                <FileCode className="w-4 h-4" />
                <span>Ingest Product Spec Markdown</span>
              </h3>
              <button onClick={() => setShowIngestSpec(false)} className="text-zinc-500 hover:text-zinc-300">
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-[10px] text-zinc-500 leading-relaxed uppercase">
              Provide markdown text containing `id`, `title`, and associated `features` mapped actions in the YAML frontmatter.
            </p>

            <textarea
              className="w-full h-80 bg-black border border-zinc-800 rounded p-3 text-xs font-mono text-zinc-300 outline-none focus:border-pink-500"
              value={specInput}
              onChange={(e) => setSpecInput(e.target.value)}
            />

            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setShowIngestSpec(false)}
                className="border border-zinc-800 hover:bg-zinc-850 px-4 py-2 rounded text-xs font-bold"
              >
                CANCEL
              </button>
              <button
                onClick={handleIngestSpec}
                className="bg-pink-950 border border-pink-700/60 hover:bg-pink-500 hover:text-black px-4 py-2 rounded text-xs font-bold transition duration-200"
              >
                INGEST SPEC
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 2. Add Feature Modal */}
      {showAddFeature && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-zinc-950 border border-cyan-400 rounded p-6 w-full max-w-md space-y-4 shadow-[0_0_30px_rgba(34,211,238,0.3)]">
            <div className="flex justify-between items-center border-b border-zinc-900 pb-3">
              <h3 className="text-sm font-bold text-cyan-400 uppercase tracking-widest">
                Create New Feature Doc
              </h3>
              <button onClick={() => setShowAddFeature(false)} className="text-zinc-500 hover:text-zinc-300">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="space-y-1">
                <label className="text-[10px] text-zinc-500 block uppercase">Feature ID (slug-id)</label>
                <input
                  type="text"
                  placeholder="auth-logout"
                  value={newFeatureId}
                  onChange={(e) => setNewFeatureId(e.target.value)}
                  className="w-full bg-black border border-zinc-800 rounded px-2.5 py-2 outline-none focus:border-cyan-400"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[10px] text-zinc-500 block uppercase">Feature Title</label>
                <input
                  type="text"
                  placeholder="Выход из учетной записи"
                  value={newFeatureTitle}
                  onChange={(e) => setNewFeatureTitle(e.target.value)}
                  className="w-full bg-black border border-zinc-800 rounded px-2.5 py-2 outline-none focus:border-cyan-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[10px] text-zinc-500 block uppercase">Priority</label>
                  <select
                    value={newFeaturePriority}
                    onChange={(e: any) => setNewFeaturePriority(e.target.value)}
                    className="w-full bg-black border border-zinc-800 rounded px-2.5 py-2 outline-none focus:border-cyan-400"
                  >
                    <option value="p0">P0 (HIGH)</option>
                    <option value="p1">P1</option>
                    <option value="p2">P2</option>
                    <option value="p3">P3</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] text-zinc-500 block uppercase">Tags (comma-separated)</label>
                  <input
                    type="text"
                    placeholder="auth, api"
                    value={newFeatureTags}
                    onChange={(e) => setNewFeatureTags(e.target.value)}
                    className="w-full bg-black border border-zinc-800 rounded px-2.5 py-2 outline-none focus:border-cyan-400 font-mono"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setShowAddFeature(false)}
                className="border border-zinc-800 p-2 rounded text-xs font-bold"
              >
                CANCEL
              </button>
              <button
                onClick={handleAddFeature}
                className="bg-cyan-950 border border-cyan-700/60 hover:bg-cyan-400 hover:text-black px-4 py-2 rounded text-xs font-bold transition duration-200"
              >
                CREATE FEATURE
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. Add Backlog Item Modal */}
      {showAddBacklog && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-zinc-950 border border-emerald-400 rounded p-6 w-full max-w-md space-y-4 shadow-[0_0_30px_rgba(52,211,153,0.3)]">
            <div className="flex justify-between items-center border-b border-zinc-900 pb-3">
              <h3 className="text-sm font-bold text-emerald-400 uppercase tracking-widest">
                Log New Backlog Item
              </h3>
              <button onClick={() => setShowAddBacklog(false)} className="text-zinc-500 hover:text-zinc-300">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="space-y-1">
                <label className="text-[10px] text-zinc-500 block uppercase">Task Code / Unique ID</label>
                <input
                  type="text"
                  placeholder="bl-043"
                  value={newBackId}
                  onChange={(e) => setNewBackId(e.target.value)}
                  className="w-full bg-black border border-zinc-800 rounded px-2.5 py-2 outline-none focus:border-emerald-400"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[10px] text-zinc-500 block uppercase">Item Title / Description</label>
                <input
                  type="text"
                  placeholder="Refactor JWT validation rules"
                  value={newBackTitle}
                  onChange={(e) => setNewBackTitle(e.target.value)}
                  className="w-full bg-black border border-zinc-800 rounded px-2.5 py-2 outline-none focus:border-emerald-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[10px] text-zinc-500 block uppercase">Type</label>
                  <select
                    value={newBackType}
                    onChange={(e: any) => setNewBackType(e.target.value)}
                    className="w-full bg-black border border-zinc-800 rounded px-2.5 py-2 outline-none focus:border-emerald-400"
                  >
                    <option value="debt">TECH DEBT</option>
                    <option value="growth">ROADMAP / GROWTH</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] text-zinc-500 block uppercase">Priority</label>
                  <select
                    value={newBackPriority}
                    onChange={(e: any) => setNewBackPriority(e.target.value)}
                    className="w-full bg-black border border-zinc-800 rounded px-2.5 py-2 outline-none focus:border-emerald-400"
                  >
                    <option value="p0">P0 (CRITICAL)</option>
                    <option value="p1">P1</option>
                    <option value="p2">P2</option>
                    <option value="p3">P3</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] text-zinc-500 block uppercase">Linked Features (comma-separated id list)</label>
                <input
                  type="text"
                  placeholder="auth-login, api-auth"
                  value={newBackFeatures}
                  onChange={(e) => setNewBackFeatures(e.target.value)}
                  className="w-full bg-black border border-zinc-800 rounded px-2.5 py-2 outline-none focus:border-emerald-400 font-mono"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setShowAddBacklog(false)}
                className="border border-zinc-800 px-4 py-2 rounded text-xs font-bold"
              >
                CANCEL
              </button>
              <button
                onClick={handleAddBacklog}
                className="bg-emerald-950 border border-emerald-700/60 hover:bg-emerald-400 hover:text-black px-4 py-2 rounded text-xs font-bold transition duration-200"
              >
                LOG TASK
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}
