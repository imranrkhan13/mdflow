import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Video, Play, Download, Loader2, AlertTriangle, Mic, RefreshCw } from 'lucide-react'
import { listVoices, startVideoGeneration, getVideoStatus, videoDownloadUrl } from '../lib/api.js'

const VOICE_LABELS = {
  narrator: 'Narrator — deep & clear',
  friendly: 'Friendly — warm & upbeat',
  calm:     'Calm — slow & measured',
}

export default function VideoPanel({ projectId, node, standalone }) {
  const [voices, setVoices]   = useState([])
  const [voice, setVoice]     = useState('narrator')
  const [status, setStatus]   = useState('idle')
  const [stage, setStage]     = useState('')
  const [progress, setProgress] = useState(0)
  const [jobId, setJobId]     = useState(null)
  const [error, setError]     = useState('')
  const pollRef = useRef(null)

  useEffect(() => {
    listVoices().then(r => setVoices(r.voices)).catch(() => setVoices(['narrator','friendly','calm']))
  }, [])

  useEffect(() => {
    setStatus('idle'); setProgress(0); setJobId(null); setError('')
    if (pollRef.current) clearInterval(pollRef.current)
  }, [node?.id])

  useEffect(() => () => pollRef.current && clearInterval(pollRef.current), [])

  async function handleGenerate() {
    setStatus('running'); setError(''); setProgress(0)
    try {
      const { job_id } = await startVideoGeneration(projectId, node.id, voice)
      setJobId(job_id)

      // Time out after 3 minutes — video should never take longer than that
      const timeoutId = setTimeout(() => {
        clearInterval(pollRef.current)
        setStatus('error')
        setError('Video generation timed out after 3 minutes. Try again — it may have been a network hiccup.')
      }, 3 * 60 * 1000)

      pollRef.current = setInterval(async () => {
        try {
          const s = await getVideoStatus(job_id)
          setStage(s.stage); setProgress(s.progress)
          if (s.status === 'done')  { clearInterval(pollRef.current); clearTimeout(timeoutId); setStatus('done') }
          if (s.status === 'error') { clearInterval(pollRef.current); clearTimeout(timeoutId); setStatus('error'); setError(s.error || 'Failed.') }
        } catch (e) { clearInterval(pollRef.current); clearTimeout(timeoutId); setStatus('error'); setError(e.message) }
      }, 2000)
    } catch (e) { setStatus('error'); setError(e.message) }
  }

  // Header varies: embedded (below NodePanel) vs standalone tab
  const header = standalone ? (
    <div className="border-b border-umber-200 bg-umber-100/30 px-5 py-4">
      <div className="flex items-center gap-2 mb-1">
        <Video className="h-4 w-4 text-clay" />
        <h2 className="font-sans text-base font-bold text-umber-900">Explainer Video</h2>
      </div>
      <p className="font-sans text-xs text-umber-500">
        AI writes the script → AI reads it out loud → animations sync to the voiceover.
        No quota needed — uses Microsoft's free neural voice.
      </p>
    </div>
  ) : (
    <div className="border-t border-umber-200 px-5 pt-4 pb-2">
      <div className="flex items-center gap-2">
        <Video className="h-3.5 w-3.5 text-clay" />
        <p className="font-sans text-xs font-bold text-umber-900">Explainer Video</p>
      </div>
    </div>
  )

  return (
    <div className="flex flex-col">
      {header}
      <div className={`px-5 ${standalone ? 'py-4' : 'pb-5'}`}>
        <AnimatePresence mode="wait">

          {status === 'idle' && (
            <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
              {/* Voice picker */}
              <div>
                <p className="font-sans text-xs font-medium text-umber-700 mb-1.5">Choose a voice</p>
                <div className="flex flex-col gap-1.5">
                  {(voices.length ? voices : ['narrator','friendly','calm']).map(v => (
                    <button key={v} onClick={() => setVoice(v)}
                      className={`flex items-center gap-2.5 rounded-xl border px-3 py-2.5 text-left transition-all ${
                        voice === v
                          ? 'border-clay bg-clay/5 shadow-glow-clay'
                          : 'border-umber-200 bg-white hover:border-umber-300'
                      }`}
                    >
                      <Mic className={`h-3.5 w-3.5 shrink-0 ${voice === v ? 'text-clay' : 'text-umber-400'}`} />
                      <div>
                        <p className={`font-sans text-xs font-semibold ${voice === v ? 'text-clay' : 'text-umber-800'}`}>
                          {VOICE_LABELS[v] || v}
                        </p>
                      </div>
                      {voice === v && (
                        <div className="ml-auto h-2 w-2 rounded-full bg-clay" />
                      )}
                    </button>
                  ))}
                </div>
              </div>

              <button onClick={handleGenerate}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-umber-900 py-3 font-sans text-sm font-semibold text-white hover:bg-umber-800 transition-colors">
                <Play className="h-4 w-4" />
                Generate video
              </button>

              <div className="rounded-xl bg-umber-100/50 p-3 font-sans text-[11px] text-umber-500 leading-relaxed">
                <p className="font-semibold text-umber-700 mb-1.5">How it works</p>
                <p className="mb-2">AI writes a short script → a voice reads it → animations play in sync → you get a downloadable MP4.</p>
                <div className="flex flex-col gap-1">
                  {[
                    ['🥇', 'Microsoft Edge voices', 'Best quality, no key needed'],
                    ['🥈', 'Google Translate TTS', 'Good quality, no key needed'],
                    ['🥉', 'Built-in Mac/Windows voice', 'Works offline, always available'],
                    ['🔑', 'Gemini TTS', 'Last resort (uses your API key)'],
                  ].map(([icon, name, desc]) => (
                    <div key={name} className="flex items-center gap-2">
                      <span className="text-sm">{icon}</span>
                      <div>
                        <span className="font-semibold text-umber-700">{name}</span>
                        <span className="text-umber-400 ml-1">— {desc}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {status === 'running' && (
            <motion.div key="running" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3 py-2">
              <div className="flex items-center gap-2 font-mono text-xs text-umber-700">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-clay shrink-0" />
                <span className="truncate">{stage || 'starting…'}</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-umber-100">
                <motion.div className="h-full rounded-full bg-clay"
                  animate={{ width: `${Math.round(progress * 100)}%` }}
                  transition={{ duration: 0.4 }} />
              </div>
              <p className="font-mono text-[10px] text-umber-400">
                {Math.round(progress * 100)}% — this takes about a minute
              </p>
            </motion.div>
          )}

          {status === 'error' && (
            <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-2">
              <div className="flex items-start gap-2 rounded-xl border border-clay/25 bg-clay/5 p-3">
                <AlertTriangle className="h-4 w-4 shrink-0 text-clay mt-0.5" />
                <div>
                  <p className="font-sans text-xs font-semibold text-clay-dim mb-1">Video generation failed</p>
                  <p className="font-sans text-[11px] leading-relaxed text-clay-dim whitespace-pre-line">{error}</p>
                  {error.includes('ffmpeg') && (
                    <div className="mt-2 rounded-lg bg-umber-100 px-3 py-2">
                      <p className="font-sans text-[11px] font-semibold text-umber-800 mb-1">📦 ffmpeg not installed</p>
                      <p className="font-mono text-[11px] text-umber-700">brew install ffmpeg</p>
                      <p className="font-sans text-[11px] text-umber-500 mt-1">Then restart the backend server.</p>
                    </div>
                  )}
                </div>
              </div>
              <button onClick={handleGenerate}
                className="flex items-center gap-1.5 font-sans text-xs text-umber-500 hover:text-umber-800 underline decoration-umber-300">
                <RefreshCw className="h-3 w-3" /> Try again
              </button>
            </motion.div>
          )}

          {status === 'done' && jobId && (
            <motion.div key="done" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
              <div className="rounded-xl overflow-hidden border border-umber-200 shadow-card">
                <video controls className="w-full" src={videoDownloadUrl(jobId)} />
              </div>
              <a href={videoDownloadUrl(jobId)} download={`mindflow-${node?.data?.title || 'video'}.mp4`}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-umber-200 bg-white py-2.5 font-sans text-sm font-medium text-umber-700 transition-colors hover:bg-umber-100/50">
                <Download className="h-4 w-4" />
                Download MP4
              </a>
              <button onClick={() => { setStatus('idle'); setJobId(null) }}
                className="flex items-center gap-1.5 text-center w-full justify-center font-sans text-xs text-umber-400 hover:text-umber-700 underline decoration-umber-200">
                <RefreshCw className="h-3 w-3" /> Make another video
              </button>
            </motion.div>
          )}

        </AnimatePresence>
      </div>
    </div>
  )
}
