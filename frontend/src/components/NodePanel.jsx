import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BookOpen, Lightbulb, MessageCircleQuestion, AlertTriangle, Loader2, Cpu } from 'lucide-react'
import { explainSection } from '../lib/api.js'
import { renderMarkdown } from '../lib/renderMarkdown.js'

const MODES = [
  { id: 'explain',   label: 'Explain',   icon: BookOpen,
    hint: 'What is this thing and why does it exist?' },
  { id: 'analogy',   label: 'Analogy',   icon: Lightbulb,
    hint: 'Explain it like I\'ve never coded before' },
  { id: 'interview', label: 'Questions', icon: MessageCircleQuestion,
    hint: 'Practice questions about this concept' },
  { id: 'mistakes',  label: 'Mistakes',  icon: AlertTriangle,
    hint: 'Common beginner mistakes to avoid' },
]

const PROSE_CSS = `
  .md-prose .md-h1{font-size:1rem;font-weight:700;color:#3d2b1f;margin:.75rem 0 .3rem}
  .md-prose .md-h2{font-size:.9rem;font-weight:700;color:#3d2b1f;margin:.65rem 0 .25rem}
  .md-prose .md-h3{font-size:.84rem;font-weight:600;color:#4d3829;margin:.5rem 0 .2rem}
  .md-prose .md-p{font-size:.84rem;line-height:1.75;color:#4d3829;margin:0 0 .45rem}
  .md-prose .md-ul{list-style:disc;padding-left:1.2rem;margin:.2rem 0 .45rem}
  .md-prose .md-ol{list-style:decimal;padding-left:1.2rem;margin:.2rem 0 .45rem}
  .md-prose li{font-size:.84rem;line-height:1.7;color:#4d3829;margin-bottom:.18rem}
  .md-prose .inline-code{font-family:'JetBrains Mono',monospace;font-size:.76rem;background:#ede2cd;color:#3d2b1f;border-radius:4px;padding:.1em .35em}
  .md-prose strong{font-weight:600;color:#3d2b1f}
  .md-prose em{font-style:italic;color:#5e4534}
`

export default function NodePanel({ projectId, node }) {
  const [mode, setMode] = useState('explain')
  const [status, setStatus] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => { if (!node) return; setMode('explain') }, [node?.id])

  useEffect(() => {
    if (!node) return
    let cancelled = false
    setStatus('loading'); setResult(null); setError('')
    explainSection(projectId, node.id, mode)
      .then(r => { if (!cancelled) { setResult(r); setStatus('done') } })
      .catch(e => { if (!cancelled) { setError(e.message); setStatus('error') } })
    return () => { cancelled = true }
  }, [node?.id, mode, projectId])

  if (!node) {
    return (
      <div className="flex flex-col items-center justify-center px-6 py-12 text-center gap-3">
        <Cpu className="h-8 w-8 text-umber-300" />
        <p className="font-sans text-sm font-semibold text-umber-800">Pick any card on the graph</p>
        <p className="font-sans text-xs text-umber-500">Click a box in the graph to see a plain-English explanation of what it does and why it exists.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col">
      <style>{PROSE_CSS}</style>

      {/* Node header */}
      <div className="border-b border-umber-200 bg-umber-100/30 px-5 py-3">
        <span className="font-mono text-[10px] uppercase tracking-wider text-clay">
          {node.data.level <= 1 ? 'Root section' : `Section level ${node.data.level}`}
        </span>
        <h2 className="mt-0.5 font-sans text-base font-bold text-umber-900">{node.data.title}</h2>
        {node.data.concepts?.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            {node.data.concepts.slice(0, 5).map(c => (
              <span key={c} className="rounded-full bg-umber-100 px-2 py-0.5 font-mono text-[10px] text-umber-600">{c}</span>
            ))}
          </div>
        )}
      </div>

      {/* Mode tabs */}
      <div className="flex border-b border-umber-200 px-2 pt-2 gap-0.5 flex-wrap">
        {MODES.map(m => {
          const Icon = m.icon
          const active = mode === m.id
          return (
            <button key={m.id} onClick={() => setMode(m.id)}
              title={m.hint}
              className={`flex items-center gap-1 rounded-lg px-2.5 py-1.5 mb-1 font-sans text-xs font-medium transition-colors ${
                active ? 'bg-clay/10 text-clay' : 'text-umber-500 hover:bg-umber-100/60 hover:text-umber-800'
              }`}
            >
              <Icon className="h-3.5 w-3.5" />{m.label}
            </button>
          )
        })}
      </div>

      {/* Active mode hint */}
      <p className="px-5 pt-2 pb-0 font-sans text-[11px] text-umber-400 italic">
        {MODES.find(m => m.id === mode)?.hint}
      </p>

      {/* Content */}
      <div className="px-5 py-3">
        <AnimatePresence mode="wait">
          {status === 'loading' && (
            <motion.div key="load" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex items-center gap-2 py-4 font-mono text-xs text-umber-400">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-clay" />
              Getting your explanation…
            </motion.div>
          )}
          {status === 'error' && (
            <motion.div key="err" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="rounded-xl border border-clay/25 bg-clay/5 p-4 font-sans text-sm text-clay-dim">
              <p className="font-semibold mb-1">Couldn't get an explanation</p>
              <p className="text-xs leading-relaxed">{error}</p>
              <p className="mt-2 text-xs text-umber-400">Check that your API keys are in backend/.env</p>
            </motion.div>
          )}
          {status === 'done' && result && (
            <motion.div key={`${node.id}-${mode}`} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}>
              <div className="md-prose" dangerouslySetInnerHTML={{ __html: renderMarkdown(result.text) }} />
              <p className="mt-3 font-mono text-[10px] text-umber-300">answered by {result.provider}</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
