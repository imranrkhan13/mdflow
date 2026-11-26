import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import Landing from './pages/Landing.jsx'
import Workspace from './pages/Workspace.jsx'
import { uploadDocument, importRepo } from './lib/api.js'

export default function App() {
  const [project, setProject]   = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError]       = useState('')
  const [loadingMsg, setLoadingMsg] = useState('')
  const [loadingSub, setLoadingSub] = useState('Turning your file into an interactive map')

  // Stagger loading messages so the user knows something is happening
  const FILE_MSGS = [
    [800,  'Finding all the sections…'],
    [1600, 'Spotting technical concepts…'],
    [2600, 'Drawing the connections…'],
    [3600, 'Almost there…'],
  ]
  const REPO_MSGS = [
    [900,  'Fetching the file tree…'],
    [2200, 'Reading every source file…'],
    [4200, 'Resolving imports…'],
    [6500, 'Drawing the dependency graph…'],
    [9000, 'Almost there…'],
  ]

  async function run(job, msgs, sub) {
    setError('')
    setUploading(true)
    setLoadingMsg(msgs[0][1])
    setLoadingSub(sub)
    const timers = msgs.map(([delay, msg]) => setTimeout(() => setLoadingMsg(msg), delay))
    try {
      const result = await job()
      setProject(result)
    } catch (err) {
      setError(err.message)
    } finally {
      timers.forEach(clearTimeout)
      setUploading(false)
      setLoadingMsg('')
    }
  }

  function handleFileReady(file) {
    run(() => uploadDocument(file), FILE_MSGS, 'Turning your file into an interactive map')
  }

  function handleRepoReady(url) {
    run(() => importRepo(url), REPO_MSGS, 'Cloning the repo into a file-level dependency graph')
  }

  function handleReset() {
    setProject(null)
    setError('')
  }

  if (project) {
    return <Workspace project={project} onReset={handleReset} />
  }

  return (
    <>
      <Landing onFileReady={handleFileReady} onRepoReady={handleRepoReady} error={error} busy={uploading} />
      <AnimatePresence>
        {uploading && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-paper/92 backdrop-blur-sm"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-clay/10">
              <Loader2 className="h-6 w-6 animate-spin text-clay" />
            </div>
            <div className="text-center">
              <p className="font-sans text-sm font-semibold text-umber-900">{loadingMsg}</p>
              <p className="mt-1 font-sans text-xs text-umber-500">{loadingSub}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
