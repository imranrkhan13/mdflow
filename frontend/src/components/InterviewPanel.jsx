import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { GraduationCap, Loader2, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'
import { generateInterviewPrep } from '../lib/api.js'
import { renderMarkdown } from '../lib/renderMarkdown.js'

const PROSE_CSS = `
  .md-prose .md-h1{font-size:1rem;font-weight:700;color:#3d2b1f;margin:.75rem 0 .3rem;padding-bottom:.25rem;border-bottom:1px solid #ede2cd}
  .md-prose .md-h2{font-size:.9rem;font-weight:700;color:#3d2b1f;margin:.85rem 0 .25rem;padding:.35rem .6rem;background:#faf8f4;border-left:3px solid #b5673f;border-radius:0 6px 6px 0}
  .md-prose .md-h3{font-size:.84rem;font-weight:600;color:#5e4534;margin:.5rem 0 .2rem}
  .md-prose .md-p{font-size:.84rem;line-height:1.75;color:#4d3829;margin:0 0 .45rem}
  .md-prose .md-ol{list-style:none;padding-left:0;margin:.2rem 0 .6rem;counter-reset:qnum}
  .md-prose .md-ol li{font-size:.84rem;line-height:1.7;color:#4d3829;margin-bottom:.7rem;padding:.6rem .75rem;background:#fdfcfa;border:1px solid #e8e1d4;border-radius:10px;counter-increment:qnum}
  .md-prose .md-ol li::before{content:counter(qnum)'. ';font-weight:700;color:#b5673f;font-family:'JetBrains Mono',monospace;font-size:.78rem}
  .md-prose .md-ul{list-style:disc;padding-left:1.2rem;margin:.2rem 0 .45rem}
  .md-prose li .md-p{margin:0}
  .md-prose .inline-code{font-family:'JetBrains Mono',monospace;font-size:.76rem;background:#ede2cd;color:#3d2b1f;border-radius:4px;padding:.1em .35em}
  .md-prose strong{font-weight:600;color:#3d2b1f}
  .md-prose em{font-style:italic;color:#5e4534;font-size:.82rem}
`

export default function InterviewPanel({ projectId }) {
  const [status, setStatus] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  async function generate() {
    setStatus('loading'); setResult(null); setError('')
    try {
      const r = await generateInterviewPrep(projectId)
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
          <GraduationCap className="h-4 w-4 text-clay" />
          <h2 className="font-sans text-base font-bold text-umber-900">Interview Prep</h2>
        </div>
        <p className="font-sans text-xs text-umber-500">
          Get a full guide: project summary, technical questions (easy → hard), architecture questions, and what to say out loud.
        </p>
      </div>

      <div className="px-5 py-4">
        <AnimatePresence mode="wait">
          {status === 'idle' && (
            <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              {/* What you'll get */}
              <div className="mb-4 grid grid-cols-2 gap-2">
                {[
                  ['📋', 'Project brief', 'Plain English summary of what you built'],
                  ['💬', 'Easy questions', 'What any interviewer might ask first'],
                  ['⚡', 'Hard questions', 'Senior-level deep dives'],
                  ['🏗️', 'Architecture', 'How you designed the system'],
                ].map(([icon, title, desc]) => (
                  <div key={title} className="rounded-xl border border-umber-200 bg-white p-3">
                    <div className="text-lg mb-1">{icon}</div>
                    <p className="font-sans text-xs font-semibold text-umber-900">{title}</p>
                    <p className="font-sans text-[11px] text-umber-500 leading-snug mt-0.5">{desc}</p>
                  </div>
                ))}
              </div>
              <button onClick={generate}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-umber-900 py-3 font-sans text-sm font-semibold text-white hover:bg-umber-800 transition-colors">
                <GraduationCap className="h-4 w-4" />
                Generate my interview prep
              </button>
              <p className="mt-2 text-center font-sans text-[11px] text-umber-400">
                Based on everything in this project file
              </p>
            </motion.div>
          )}

          {status === 'loading' && (
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center py-12 gap-3">
              <Loader2 className="h-6 w-6 animate-spin text-clay" />
              <p className="font-sans text-sm text-umber-600">Building your interview guide…</p>
              <p className="font-sans text-xs text-umber-400">Reading through the whole project</p>
            </motion.div>
          )}

          {status === 'error' && (
            <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="rounded-xl border border-clay/25 bg-clay/5 p-4 font-sans text-sm text-clay-dim">
              <p className="font-semibold mb-1">Couldn't generate interview prep</p>
              <p className="text-xs leading-relaxed">{error}</p>
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
                  generated by {result.provider}
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
