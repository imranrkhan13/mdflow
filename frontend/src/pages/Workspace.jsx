import { useCallback, useEffect, useRef, useMemo, useState } from 'react'
import ReactFlow, {
  Background, Controls, MiniMap,
  useNodesState, useEdgesState,
  useReactFlow, ReactFlowProvider,
  BackgroundVariant,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft, BookOpen, Layers, GraduationCap,
  Video, ChevronRight, Menu, X, Map,
} from 'lucide-react'
import ConceptNode from '../components/ConceptNode.jsx'
import NodePanel from '../components/NodePanel.jsx'
import InterviewPanel from '../components/InterviewPanel.jsx'
import ArchitecturePanel from '../components/ArchitecturePanel.jsx'
import VideoPanel from '../components/VideoPanel.jsx'

const nodeTypes = { conceptNode: ConceptNode }

function styledEdges(rawEdges) {
  return rawEdges.map((e) => ({
    ...e,
    style: {
      stroke: e.data?.kind === 'concept' ? '#b5673f' : '#ddc9a3',
      strokeWidth: 1.5,
      strokeDasharray: e.data?.kind === 'concept' ? '5 4' : undefined,
    },
    label: e.data?.kind === 'concept' ? e.data.via : undefined,
    labelStyle: { fill: '#8b5a3c', fontSize: 10, fontFamily: 'JetBrains Mono' },
    labelBgStyle: { fill: '#fdfcfa', fillOpacity: 0.9 },
  }))
}

const TABS = [
  { id: 'node',         label: 'Explain',      icon: BookOpen },
  { id: 'architecture', label: 'Architecture', icon: Layers },
  { id: 'interview',    label: 'Interview',    icon: GraduationCap },
  { id: 'video',        label: 'Video',        icon: Video },
]

/* ── Auto-fit + center-on-select graph ──────────────────────────────────── */
function GraphCanvas({ nodes, edges, selectedId, onSelect, onNodesChange, onEdgesChange }) {
  const { fitView, setCenter } = useReactFlow()
  const didFit = useRef(false)

  useEffect(() => {
    if (!didFit.current && nodes.length > 0) {
      setTimeout(() => { fitView({ padding: 0.25, duration: 600 }); didFit.current = true }, 120)
    }
  }, [nodes.length, fitView])

  useEffect(() => {
    if (!selectedId) return
    const node = nodes.find(n => n.id === selectedId)
    if (!node) return
    setCenter(node.position.x + 128, node.position.y + 55, { zoom: 1.1, duration: 500 })
  }, [selectedId, nodes, setCenter])

  const styledNodes = nodes.map(n => ({ ...n, selected: n.id === selectedId }))

  return (
    <ReactFlow
      nodes={styledNodes} edges={edges}
      onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
      onNodeClick={(_, node) => onSelect(node.id)}
      nodeTypes={nodeTypes}
      fitView fitViewOptions={{ padding: 0.25 }}
      minZoom={0.2} maxZoom={2}
      proOptions={{ hideAttribution: true }}
    >
      <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#e8e1d4" />
      <Controls showInteractive={false} />
      <MiniMap
        nodeColor={n => n.selected ? '#b5673f' : '#ddc9a3'}
        maskColor="rgba(253,252,250,0.75)"
        style={{ background: '#fff', border: '1px solid #e8e1d4', borderRadius: 10 }}
      />
    </ReactFlow>
  )
}

/* ── Sidebar list ────────────────────────────────────────────────────────── */
function SidebarContent({ nodes, selectedId, onSelect }) {
  const [query, setQuery] = useState('')
  const filtered = nodes.filter(n =>
    n.data.title.toLowerCase().includes(query.toLowerCase())
  )

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="px-3 pt-3 pb-2">
        <input value={query} onChange={e => setQuery(e.target.value)}
          placeholder="Search sections…"
          className="w-full rounded-lg border border-umber-200 bg-white px-3 py-1.5 font-sans text-xs text-umber-900 placeholder:text-umber-400 focus:border-clay focus:outline-none"
        />
      </div>
      <div className="flex-1 overflow-y-auto px-2 pb-3">
        <p className="px-2 pb-1 pt-1 font-mono text-[9px] uppercase tracking-wider text-umber-400">
          {filtered.length} sections
        </p>
        {filtered.map(n => (
          <button key={n.id} onClick={() => onSelect(n.id)}
            className={`mb-0.5 flex w-full items-start gap-2 rounded-lg px-2.5 py-2 text-left transition-colors ${
              selectedId === n.id
                ? 'bg-clay/10 text-clay'
                : 'text-umber-600 hover:bg-umber-100/60 hover:text-umber-900'
            }`}
          >
            <span className={`mt-0.5 shrink-0 rounded px-1 py-0.5 font-mono text-[9px] uppercase ${
              selectedId === n.id ? 'bg-clay/20 text-clay' : 'bg-umber-100 text-umber-400'
            }`}>
              {n.data.level <= 1 ? 'root' : `h${n.data.level}`}
            </span>
            <span className="truncate font-sans text-xs leading-snug">{n.data.title}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

/* ── Right panel tab content ─────────────────────────────────────────────── */
function RightPanel({ project, node, activeTab, onTabChange }) {
  return (
    <div className="flex h-full flex-col">
      {/* Tab bar */}
      <div className="flex shrink-0 border-b border-umber-200 bg-white/80">
        {TABS.map(t => {
          const Icon = t.icon
          const active = activeTab === t.id
          const disabled = t.id === 'node' && !node
          return (
            <button key={t.id}
              onClick={() => !disabled && onTabChange(t.id)}
              disabled={disabled}
              className={`flex flex-1 flex-col items-center gap-0.5 py-2.5 transition-colors ${
                active   ? 'border-b-2 border-clay text-clay' :
                disabled ? 'cursor-not-allowed text-umber-200' :
                           'border-b-2 border-transparent text-umber-400 hover:text-umber-700'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span className="font-sans text-[10px] font-medium">{t.label}</span>
            </button>
          )
        })}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <AnimatePresence mode="wait">
          {activeTab === 'node' && (
            <motion.div key="node"
              initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <NodePanel projectId={project.project_id} node={node} />
            </motion.div>
          )}
          {activeTab === 'architecture' && (
            <motion.div key="arch"
              initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <ArchitecturePanel projectId={project.project_id} />
            </motion.div>
          )}
          {activeTab === 'interview' && (
            <motion.div key="interview"
              initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <InterviewPanel projectId={project.project_id} />
            </motion.div>
          )}
          {activeTab === 'video' && (
            <motion.div key="video"
              initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              {node
                ? <VideoPanel projectId={project.project_id} node={node} standalone />
                : (
                  <div className="flex flex-col items-center justify-center gap-3 px-6 py-12 text-center">
                    <Video className="h-8 w-8 text-umber-300" />
                    <p className="font-sans text-sm font-semibold text-umber-700">Select a concept first</p>
                    <p className="font-sans text-xs text-umber-500">
                      Click any card on the graph, then come back here to generate a narrated video for it.
                    </p>
                  </div>
                )
              }
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

/* ── Main Workspace ──────────────────────────────────────────────────────── */
export default function Workspace({ project, onReset }) {
  const initialNodes = useMemo(() => project.graph.nodes, [project])
  const initialEdges = useMemo(() => styledEdges(project.graph.edges), [project])

  const [nodes, , onNodesChange] = useNodesState(initialNodes)
  const [edges, , onEdgesChange] = useEdgesState(initialEdges)
  const [selectedId, setSelectedId] = useState(null)
  const [activeTab, setActiveTab]   = useState('node')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [panelOpen, setPanelOpen]     = useState(false)

  const selectedNode = nodes.find(n => n.id === selectedId) || null

  const handleSelect = useCallback((id) => {
    setSelectedId(id)
    setActiveTab('node')
    setPanelOpen(true)
  }, [])

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-paper">

      {/* ── Top bar ─────────────────────────────────────────────── */}
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-umber-200 bg-white/80 px-4 backdrop-blur">
        <button onClick={onReset}
          className="flex items-center gap-1.5 font-mono text-xs text-umber-500 transition-colors hover:text-umber-900">
          <ArrowLeft className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">new upload</span>
        </button>

        <div className="flex items-center gap-2">
          <div className="flex h-5 w-5 items-center justify-center rounded bg-clay/10">
            <Map className="h-3 w-3 text-clay" />
          </div>
          <span className="max-w-[160px] truncate font-sans text-sm font-semibold text-umber-900 sm:max-w-xs">
            {project.filename}
          </span>
          <span className="rounded-full bg-umber-100 px-2 py-0.5 font-mono text-[10px] text-umber-500">
            {nodes.length} concepts
          </span>
        </div>

        <button onClick={() => setSidebarOpen(v => !v)}
          className="flex items-center gap-1.5 rounded-lg border border-umber-200 bg-white px-2.5 py-1.5 font-mono text-xs text-umber-600 lg:hidden">
          <Menu className="h-3.5 w-3.5" />
          <span className="hidden xs:inline">Sections</span>
        </button>
      </header>

      {/* ── Body ────────────────────────────────────────────────── */}
      <div className="relative flex flex-1 overflow-hidden">

        {/* Desktop sidebar */}
        <aside className="hidden w-56 shrink-0 flex-col border-r border-umber-200 bg-white/60 lg:flex">
          <SidebarContent nodes={nodes} selectedId={selectedId} onSelect={handleSelect} />
        </aside>

        {/* Mobile sidebar overlay */}
        <AnimatePresence>
          {sidebarOpen && (
            <>
              <motion.div key="overlay"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="absolute inset-0 z-30 bg-umber-900/20 lg:hidden"
                onClick={() => setSidebarOpen(false)} />
              <motion.aside key="drawer"
                initial={{ x: -240 }} animate={{ x: 0 }} exit={{ x: -240 }}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                className="absolute left-0 top-0 z-40 h-full w-56 border-r border-umber-200 bg-white shadow-glow lg:hidden">
                <div className="flex items-center justify-between border-b border-umber-200 px-4 py-3">
                  <p className="font-sans text-sm font-semibold text-umber-900">Sections</p>
                  <button onClick={() => setSidebarOpen(false)}>
                    <X className="h-4 w-4 text-umber-400" />
                  </button>
                </div>
                <div className="h-[calc(100%-52px)]">
                  <SidebarContent nodes={nodes} selectedId={selectedId}
                    onSelect={id => { handleSelect(id); setSidebarOpen(false) }} />
                </div>
              </motion.aside>
            </>
          )}
        </AnimatePresence>

        {/* Graph canvas */}
        <main className="relative flex-1 overflow-hidden">
          {!selectedNode && (
            <div className="pointer-events-none absolute left-1/2 top-4 z-10 -translate-x-1/2 whitespace-nowrap">
              <div className="flex items-center gap-2 rounded-full border border-umber-200 bg-white/90 px-4 py-2 shadow-card backdrop-blur">
                <ChevronRight className="h-3.5 w-3.5 text-clay" />
                <p className="font-sans text-xs text-umber-600">Tap any card to explore it</p>
              </div>
            </div>
          )}

          <ReactFlowProvider>
            <GraphCanvas
              nodes={nodes} edges={edges}
              selectedId={selectedId} onSelect={handleSelect}
              onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
            />
          </ReactFlowProvider>

          {/* Mobile: open panel button */}
          {selectedNode && (
            <button onClick={() => setPanelOpen(true)}
              className="absolute bottom-6 left-1/2 z-10 -translate-x-1/2 flex items-center gap-2 rounded-full border border-umber-200 bg-white px-5 py-2.5 font-sans text-sm font-medium text-umber-900 shadow-glow lg:hidden">
              <BookOpen className="h-4 w-4 text-clay" />
              Learn: "{selectedNode.data.title}"
            </button>
          )}
        </main>

        {/* Desktop right panel */}
        <aside className="hidden w-[26rem] shrink-0 flex-col border-l border-umber-200 bg-white/60 lg:flex">
          <RightPanel project={project} node={selectedNode}
            activeTab={activeTab} onTabChange={setActiveTab} />
        </aside>

        {/* Mobile bottom sheet */}
        <AnimatePresence>
          {panelOpen && selectedNode && (
            <>
              <motion.div key="sheet-overlay"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="absolute inset-0 z-30 bg-umber-900/20 lg:hidden"
                onClick={() => setPanelOpen(false)} />
              <motion.div key="sheet"
                initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }}
                transition={{ type: 'spring', stiffness: 300, damping: 32 }}
                className="absolute bottom-0 left-0 right-0 z-40 max-h-[85vh] flex flex-col rounded-t-2xl border-t border-umber-200 bg-white shadow-glow lg:hidden">
                <div className="flex shrink-0 items-center justify-between border-b border-umber-200 px-5 py-3">
                  <p className="font-sans text-sm font-semibold text-umber-900 truncate pr-4">
                    {selectedNode.data.title}
                  </p>
                  <button onClick={() => setPanelOpen(false)}>
                    <X className="h-4 w-4 text-umber-400" />
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto">
                  <RightPanel project={project} node={selectedNode}
                    activeTab={activeTab} onTabChange={setActiveTab} />
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
