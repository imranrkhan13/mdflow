import { useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Upload, ArrowRight, BookOpen, GraduationCap, Layers, Video } from 'lucide-react'
import AmbientGraph from '../components/AmbientGraph.jsx'

const FEATURES = [
  { icon: BookOpen,      label: 'Plain-English explanations', desc: 'Every concept explained like you\'re new to coding' },
  { icon: Layers,        label: 'Architecture map',           desc: 'See how all the pieces fit together visually' },
  { icon: GraduationCap, label: 'Interview prep',             desc: 'Practice questions generated from your actual project' },
  { icon: Video,         label: 'Narrated videos',            desc: 'AI reads and animates each concept for you' },
]

export default function Landing({ onFileReady, error }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  function handleFiles(files) {
    const file = files?.[0]
    if (file) onFileReady(file)
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-paper">
      <AmbientGraph />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-paper/30 via-paper/65 to-paper" />

      <div className="relative z-10 flex min-h-screen flex-col items-center justify-center px-5 py-12">

        {/* Badge */}
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }}
          className="mb-6 flex items-center gap-2 rounded-full border border-umber-200 bg-white/80 px-4 py-1.5 font-sans text-xs font-medium text-umber-600 shadow-card backdrop-blur">
          🧠 Upload a file. Understand everything in it.
        </motion.div>

        {/* Hero */}
        <motion.h1 initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, delay: 0.05 }}
          className="max-w-2xl text-balance text-center font-sans text-4xl font-bold tracking-tight text-umber-900 sm:text-5xl lg:text-6xl">
          Understand any codebase{' '}
          <span className="text-clay">without the headache.</span>
        </motion.h1>

        <motion.p initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, delay: 0.1 }}
          className="mt-4 max-w-lg text-center font-sans text-base text-umber-600">
          Drop your README, docs, or architecture file. MindFlow turns it into an interactive map with plain-English explanations — and even prepares you for interviews about it.
        </motion.p>

        {/* Upload box */}
        <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, delay: 0.15 }}
          className="mt-8 w-full max-w-md">
          <div
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={e => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files) }}
            onClick={() => inputRef.current?.click()}
            className={`group cursor-pointer rounded-2xl border-2 border-dashed px-8 py-10 text-center transition-all ${
              dragging
                ? 'border-clay bg-clay/5 scale-[1.01]'
                : 'border-umber-200 bg-white/70 hover:border-clay/50 hover:bg-white/90 hover:shadow-card'
            } backdrop-blur`}
          >
            <input ref={inputRef} type="file" accept=".md,.markdown,.txt"
              className="hidden" onChange={e => handleFiles(e.target.files)} />
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-umber-100 transition-colors group-hover:bg-clay/10">
              <Upload className="h-5 w-5 text-umber-400 group-hover:text-clay transition-colors" />
            </div>
            <p className="font-sans text-sm font-semibold text-umber-900">
              Drop your README or docs file here
            </p>
            <p className="mt-1 font-sans text-xs text-umber-500">
              or click to browse — accepts .md .markdown .txt
            </p>
          </div>

          {error && (
            <div className="mt-3 rounded-xl border border-clay/25 bg-clay/5 px-4 py-2.5 font-sans text-xs text-clay-dim">
              {error}
            </div>
          )}

          <p className="mt-3 flex items-center justify-center gap-1.5 font-sans text-xs text-umber-400">
            No signup needed
            <span className="text-umber-200">·</span>
            Runs on your machine
            <ArrowRight className="h-3 w-3" />
          </p>
        </motion.div>

        {/* Feature grid */}
        <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, delay: 0.25 }}
          className="mt-12 grid w-full max-w-2xl grid-cols-2 gap-3 sm:grid-cols-4">
          {FEATURES.map(({ icon: Icon, label, desc }) => (
            <div key={label} className="flex flex-col gap-2 rounded-2xl border border-umber-200 bg-white/70 p-4 backdrop-blur">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-clay/10">
                <Icon className="h-4 w-4 text-clay" />
              </div>
              <p className="font-sans text-xs font-semibold text-umber-900 leading-snug">{label}</p>
              <p className="font-sans text-[11px] text-umber-500 leading-snug">{desc}</p>
            </div>
          ))}
        </motion.div>

      </div>
    </div>
  )
}
