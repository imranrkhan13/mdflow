import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Layers, Loader2, RefreshCw } from 'lucide-react'
import { explainArchitecture } from '../lib/api.js'
import { renderMarkdown } from '../lib/renderMarkdown.js'

const PROSE_CSS = `
  .md-prose .md-h1{font-size:1rem;font-weight:700;color:#3d2b1f;margin:.75rem 0 .3rem;padding-bottom:.25rem;border-bottom:1px solid #ede2cd}
  .md-prose .md-h2{font-size:.875rem;font-weight:700;color:#3d2b1f;margin:.8rem 0 .25rem;display:flex;align-items:center;gap:.4rem}
  .md-prose .md-h2::before{content:'';display:inline-block;width:3px;height:1rem;background:#b5673f;border-radius:2px;flex-shrink:0}
  .md-prose .md-h3{font-size:.82rem;font-weight:600;color:#5e4534;margin:.5rem 0 .15rem}
  .md-prose .md-p{font-size:.84rem;line-height:1.75;color:#4d3829;margin:0 0 .45rem}
  .md-prose .md-ul{list-style:none;padding-left:0;margin:.2rem 0 .5rem}
  .md-prose .md-ul li{font-size:.84rem;line-height:1.65;color:#4d3829;margin-bottom:.3rem;padding:.4rem .65rem .4rem .9rem;border-left:2px solid #ddc9a3;background:#faf8f4;border-radius:0 6px 6px 0}
  .md-prose .md-ul li::marker{display:none}
  .md-prose .inline-code{font-family:'JetBrains Mono',monospace;font-size:.76rem;background:#ede2cd;color:#3d2b1f;border-radius:4px;padding:.1em .35em}
  .md-prose strong{font-weight:600;color:#3d2b1f}
  .md-prose em{font-style:italic;color:#5e4534}
`

const PROMPTS = [
  ['🏗️', 'Overall structure', 'What are the main parts and how do they fit together?'],
  ['🔄', 'Data flow', 'How does information travel through the system?'],
  ['💡', 'Design decisions', 'Why was it built this way?'],
  ['⚠️', 'Failure points', 'What could go wrong and why?'],
]

export default function ArchitecturePanel({ projectId }) {
  const [status, setStatus] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  async function generate() {
    setStatus('loading'); setResult(null); setError('')
    try {
      const r = await explainArchitecture(projectId)
      setResult(r); setStatus('done')
    } catch (e) {
      setError(e.message); setStatus('error')
    }
  }

  return (
    <div className="flex flex-col">
      <style>{PROSE_CSS}</style>

      {/* Header */}
      <div className="border-b border-umber-200 bg-umber-100/30 px-5 py-4">
        <div className="flex items-center gap-2 mb-1">
          <Layers className="h-4 w-4 text-clay" />
          <h2 className="font-sans text-base font-bold text-umber-900">Architecture</h2>
        </div>
        <p className="font-sans text-xs text-umber-500">
          A plain-English map of how this whole project is built — what each part does and how they talk to each other.
        </p>
      </div>

      <div className="px-5 py-4">
        <AnimatePresence mode="wait">
          {status === 'idle' && (
            <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <p className="font-sans text-sm font-semibold text-umber-900 mb-3">This will explain:</p>
              <div className="mb-4 flex flex-col gap-2">
                {PROMPTS.map(([icon, title, desc]) => (
                  <div key={title} className="flex items-start gap-3 rounded-xl border border-umber-200 bg-white p-3">
                    <span className="text-lg shrink-0">{icon}</span>
                    <div>
                      <p className="font-sans text-xs font-semibold text-umber-900">{title}</p>
                      <p className="font-sans text-[11px] text-umber-500 leading-snug mt-0.5">{desc}</p>
                    </div>
                  </div>
                ))}
              </div>
              <button onClick={generate}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-umber-900 py-3 font-sans text-sm font-semibold text-white hover:bg-umber-800 transition-colors">
                <Layers className="h-4 w-4" />
                Explain the architecture
              </button>
            </motion.div>
          )}

          {status === 'loading' && (
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center py-12 gap-3">
              <Loader2 className="h-6 w-6 animate-spin text-clay" />
              <p className="font-sans text-sm text-umber-600">Reading the whole project…</p>
              <p className="font-sans text-xs text-umber-400">Building a plain-English map</p>
            </motion.div>
          )}

          {status === 'error' && (
            <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="rounded-xl border border-clay/25 bg-clay/5 p-4">
              <p className="font-sans text-sm font-semibold text-clay-dim mb-1">Couldn't explain the architecture</p>
              <p className="font-sans text-xs text-clay-dim leading-relaxed">{error}</p>
              <button onClick={generate}
                className="mt-3 flex items-center gap-1.5 font-sans text-xs text-clay underline decoration-clay/40">
                <RefreshCw className="h-3 w-3" /> Try again
              </button>
            </motion.div>
          )}

          {status === 'done' && result && (
            <motion.div key="done" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}>
              <div className="mb-3 flex items-center justify-between">
                <p className="font-mono text-[10px] text-umber-400 uppercase tracking-wider">
                  by {result.provider}
                </p>
                <button onClick={generate}
                  className="flex items-center gap-1 font-sans text-[11px] text-umber-500 hover:text-umber-800">
                  <RefreshCw className="h-3 w-3" /> regenerate
                </button>
              </div>
              <div className="md-prose" dangerouslySetInnerHTML={{ __html: renderMarkdown(result.text) }} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
