import React, { useState, useEffect, useRef, useCallback } from 'react'

// ── GraphQL ────────────────────────────────────────────────────────
const Q_GET_POD = `query($id:String!){pod(input:{podId:$id}){id name desiredStatus costPerHr machine{gpuDisplayName} runtime{uptimeInSeconds ports{ip isIpPublic privatePort publicPort}}}}`
const M_RESUME = `mutation($id:String!){podResume(input:{podId:$id,gpuCount:1}){id desiredStatus}}`
const M_STOP = `mutation($id:String!){podStop(input:{podId:$id}){id desiredStatus}}`

const STATUS_PROGRESS = { CREATED:10, BUILDING:30, STARTING:50, PULLING:60, RUNNING:100, EXITED:0, TERMINATED:0 }

const C = {
  base:'#1e1e2e', mantle:'#181825', crust:'#11111b',
  s0:'#313244', s1:'#45475a', s2:'#585b70',
  ov0:'#6c7086', ov1:'#7f849c',
  text:'#cdd6f4', sub0:'#a6adc8',
  blue:'#89b4fa', green:'#a6e3a1', red:'#f38ba8',
  peach:'#fab387', yellow:'#f9e2af', mauve:'#cba6f7',
  teal:'#94e2d5', lav:'#b4befe',
}

// ── Helpers ────────────────────────────────────────────────────────
function ts() { return new Date().toLocaleTimeString('en-US',{hour12:false}) }

function statusColor(s) {
  if (s==='RUNNING') return C.green
  if (['STARTING','PULLING','BUILDING','CREATED'].includes(s)) return C.yellow
  if (s==='EXITED'||s==='TERMINATED') return C.ov0
  return C.sub0
}

function statusAnim(s) {
  if (s==='RUNNING') return 'animate-glow'
  if (['STARTING','PULLING','BUILDING'].includes(s)) return 'animate-spin1'
  return ''
}

// ── Main App ───────────────────────────────────────────────────────
export default function App() {
  const [apiKey, setApiKey] = useState('')
  const [apiKeyVisible, setApiKeyVisible] = useState(false)
  const [podId, setPodId] = useState('')
  const [pod, setPod] = useState(null)
  const [logs, setLogs] = useState([`[${ts()}] FunPod v2 ready`])
  const [launching, setLaunching] = useState(false)
  const [polling, setPolling] = useState(false)
  const pollRef = useRef(null)
  const didLaunch = useRef(false)
  const logRef = useRef(null)

  // Load persisted data
  useEffect(() => {
    window.api?.store.get('apiKey').then(k => k && setApiKey(k))
    window.api?.store.get('lastPodId').then(id => id && setPodId(id))
  }, [])

  // Auto-scroll logs
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [logs])

  const log = useCallback((msg) => {
    setLogs(prev => [...prev.slice(-49), `[${ts()}] ${msg}`])
  }, [])

  const gql = useCallback(async (query, variables) => {
    const res = await window.api?.gql(query, variables)
    if (res?.error) { log(`❌ ${res.error}`); return null }
    return res?.data
  }, [log])

  const fetchPod = useCallback(async (id) => {
    if (!id) return
    const data = await gql(Q_GET_POD, { id })
    if (data?.pod) {
      setPod(data.pod)
      return data.pod
    }
    return null
  }, [gql])

  // Polling
  const stopPoll = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
    setPolling(false)
  }, [])

  const startPoll = useCallback((id, intervalMs=5000) => {
    stopPoll()
    setPolling(true)
    pollRef.current = setInterval(async () => {
      const p = await fetchPod(id)
      if (!p) return
      const s = p.desiredStatus
      log(`↻ ${s}${p.runtime ? ` · ${Math.floor((p.runtime.uptimeInSeconds||0)/60)}m` : ''}`)
      if (s === 'RUNNING' && p.runtime) {
        stopPoll()
        setLaunching(false)
        if (didLaunch.current) {
          didLaunch.current = false
          log('🎮 POD LIVE — connecting...')
          setTimeout(() => window.api?.openExternal(`https://${id}-80.proxy.runpod.net/`), 800)
        }
      }
      if (s === 'EXITED' || s === 'TERMINATED') {
        stopPoll(); setLaunching(false)
      }
    }, intervalMs)
  }, [fetchPod, stopPoll, log])

  useEffect(() => () => stopPoll(), [stopPoll])

  const onApiKeyChange = (v) => {
    setApiKey(v)
    window.api?.store.set('apiKey', v)
  }

  const onPodIdChange = (v) => {
    setPodId(v)
    window.api?.store.set('lastPodId', v)
    setPod(null)
  }

  const handleRefresh = async () => {
    if (!podId) return
    log(`🔍 Fetching ${podId}...`)
    const p = await fetchPod(podId)
    if (p) {
      log(`• ${p.name || podId} — ${p.desiredStatus}${p.machine?.gpuDisplayName ? ' · '+p.machine.gpuDisplayName : ''}`)
      if (p.desiredStatus === 'STARTING' || p.desiredStatus === 'BUILDING') startPoll(podId)
    }
  }

  const handleLaunch = async () => {
    if (!podId) { log('❌ Enter a pod ID'); return }
    log(`🚀 Starting ${podId}...`)
    setLaunching(true)
    didLaunch.current = true
    const data = await gql(M_RESUME, { id: podId })
    if (!data) { setLaunching(false); return }
    log('✓ Start command sent — polling...')
    startPoll(podId, 5000)
  }

  const handleConnect = () => {
    if (!podId) return
    const url = `https://${podId}-80.proxy.runpod.net/`
    log(`🔗 Opening ${url}`)
    window.api?.openExternal(url)
  }

  const handleStop = async () => {
    if (!podId) return
    log(`⏹ Stopping ${podId}...`)
    stopPoll()
    await gql(M_STOP, { id: podId })
    await fetchPod(podId)
    log('✓ Stop sent')
  }

  const status = pod?.desiredStatus || null
  const isRunning = status === 'RUNNING' && pod?.runtime
  const isStarting = ['STARTING','BUILDING','PULLING','CREATED'].includes(status)
  const progress = STATUS_PROGRESS[status] ?? 0

  return (
    <div className="flex flex-col h-screen bg-crust text-text font-ui select-none overflow-hidden">

      {/* ── Title bar ── */}
      <div className="drag flex items-center justify-between px-4 h-10 bg-crust border-b border-surface0">
        <div className="flex items-center gap-2 no-drag">
          <span className="text-lg">🎮</span>
          <span className="font-bold text-sm tracking-wide text-text">FunPod</span>
          <span className="text-xs text-overlay0">v2</span>
        </div>
        <div className="flex items-center gap-3 flex-1 mx-6 no-drag">
          <span className="text-xs text-overlay0 whitespace-nowrap">API Key</span>
          <div className="flex items-center gap-1 flex-1 max-w-xs">
            <input
              type={apiKeyVisible ? 'text' : 'password'}
              value={apiKey}
              onChange={e => onApiKeyChange(e.target.value)}
              placeholder="Paste RunPod API key..."
              className="flex-1 bg-surface0 text-sub0 text-xs px-2 py-1 rounded border border-surface1 outline-none focus:border-blue font-mono"
            />
            <button
              onClick={() => setApiKeyVisible(v => !v)}
              className="text-overlay0 hover:text-text text-xs px-1"
            >{apiKeyVisible ? '🙈' : '👁'}</button>
          </div>
        </div>
        <div className="flex gap-2 no-drag">
          {pod?.costPerHr && (
            <span className="text-xs text-yellow font-mono mr-2">${pod.costPerHr.toFixed(2)}/hr</span>
          )}
          <button onClick={() => window.api?.minimize()} className="w-7 h-7 rounded hover:bg-surface0 text-sub0 flex items-center justify-center text-lg leading-none">─</button>
          <button onClick={() => window.api?.close()} className="w-7 h-7 rounded hover:bg-red hover:text-crust text-sub0 flex items-center justify-center text-sm">✕</button>
        </div>
      </div>

      {/* ── Body ── */}
      <div className="flex flex-col flex-1 p-5 gap-4 overflow-hidden">

        {/* Pod ID input */}
        <div className="flex flex-col gap-1">
          <label className="text-xs text-overlay0 font-medium">Pod ID</label>
          <input
            value={podId}
            onChange={e => onPodIdChange(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleRefresh()}
            placeholder="Paste pod ID here..."
            className="w-full bg-surface0 text-text font-mono text-base px-4 py-3 rounded-xl border border-surface1 outline-none focus:border-blue placeholder-overlay0 text-center tracking-widest"
          />
        </div>

        {/* Status card */}
        <div className="rounded-xl bg-mantle border border-surface0 p-4 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {status && (
                <span
                  className={`w-3 h-3 rounded-full ${statusAnim(status)}`}
                  style={{ background: statusColor(status), boxShadow: isRunning ? `0 0 8px ${C.green}` : 'none' }}
                />
              )}
              <span className="font-bold text-base" style={{ color: status ? statusColor(status) : C.ov0 }}>
                {status || 'Not connected'}
              </span>
            </div>
            <div className="flex gap-4 text-xs">
              {pod?.machine?.gpuDisplayName && (
                <span className="text-mauve font-medium">🖥 {pod.machine.gpuDisplayName}</span>
              )}
              {pod?.runtime?.uptimeInSeconds > 0 && (
                <span className="text-sub0">⏱ {Math.floor(pod.runtime.uptimeInSeconds/3600)}h {Math.floor((pod.runtime.uptimeInSeconds%3600)/60)}m</span>
              )}
            </div>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-surface0 rounded-full h-1.5 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{ width: `${progress}%`, background: isRunning ? C.green : isStarting ? C.yellow : C.ov0 }}
            />
          </div>

          {/* Pod name */}
          {pod?.name && (
            <div className="text-xs text-sub0 truncate">{pod.name}</div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex gap-3">
          <button
            onClick={handleLaunch}
            disabled={launching || isRunning}
            className="flex-1 py-3 rounded-xl font-bold text-base transition-all"
            style={{
              background: (launching || isRunning) ? C.s0 : C.green,
              color: (launching || isRunning) ? C.ov0 : C.crust,
              cursor: (launching || isRunning) ? 'not-allowed' : 'pointer',
            }}
          >
            {launching ? '⏳  LAUNCHING...' : isRunning ? '✅  LIVE' : '▶  LAUNCH'}
          </button>
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleConnect}
            disabled={!podId}
            className="flex-1 py-2 rounded-xl font-semibold text-sm transition-all"
            style={{ background: podId ? C.blue : C.s0, color: podId ? C.crust : C.ov0 }}
          >🔗 Connect</button>
          <button
            onClick={handleRefresh}
            disabled={!podId || polling}
            className="flex-1 py-2 rounded-xl font-semibold text-sm bg-surface0 hover:bg-surface1 text-text transition-all"
          >{polling ? '↻ Polling...' : '🔄 Refresh'}</button>
          <button
            onClick={handleStop}
            disabled={!isRunning && !isStarting}
            className="flex-1 py-2 rounded-xl font-semibold text-sm transition-all"
            style={{ background: (isRunning||isStarting) ? C.red : C.s0, color: (isRunning||isStarting) ? C.crust : C.ov0 }}
          >⏹ Stop</button>
        </div>

        {/* Log panel */}
        <div className="flex-1 rounded-xl bg-crust border border-surface0 overflow-hidden flex flex-col min-h-0">
          <div className="px-4 py-2 border-b border-surface0 flex items-center justify-between">
            <span className="text-xs font-semibold text-overlay0 font-mono">LOG</span>
            <button onClick={() => setLogs([])} className="text-xs text-overlay0 hover:text-red">clear</button>
          </div>
          <div ref={logRef} className="flex-1 overflow-y-auto p-3 font-mono text-xs text-sub0 leading-relaxed">
            {logs.map((l, i) => (
              <div key={i} className={
                l.includes('❌') ? 'text-red' :
                l.includes('✅')||l.includes('LIVE') ? 'text-green' :
                l.includes('🚀')||l.includes('🎮') ? 'text-blue' :
                l.includes('⏹') ? 'text-peach' : ''
              }>{l}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
