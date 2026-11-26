import { memo } from 'react'
import { Handle, Position } from 'reactflow'
import { FileCode2, Layers, File } from 'lucide-react'

function ConceptNode({ data, selected }) {
  const { title, level, preview, hasCode, concepts, kind, lang, path } = data
  const isFile = kind === 'file'

  return (
    <div
      className={`w-64 rounded-xl border bg-white px-4 py-3 transition-all ${
        selected
          ? 'border-clay shadow-glow-clay'
          : 'border-umber-200 shadow-card hover:border-umber-300'
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!h-2 !w-2 !border-none !bg-umber-300"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!h-2 !w-2 !border-none !bg-umber-300"
      />

      <div className="flex items-center justify-between gap-2">
        <span
          className={`font-mono text-[10px] uppercase tracking-wider ${
            isFile || level <= 1 ? 'text-clay' : 'text-umber-400'
          }`}
        >
          {isFile ? (lang || 'file') : (level <= 1 ? 'root' : `h${level}`)}
        </span>
        {isFile
          ? <File className="h-3 w-3 text-umber-300" />
          : hasCode && <FileCode2 className="h-3 w-3 text-sage" />}
      </div>

      <h3 className="mt-1.5 truncate font-sans text-sm font-semibold leading-snug text-umber-900">
        {title}
      </h3>

      {isFile && path && (
        <p className="mt-0.5 truncate font-mono text-[10px] text-umber-400" title={path}>
          {path}
        </p>
      )}

      {preview && (
        <p className="mt-1 line-clamp-2 font-sans text-xs leading-relaxed text-umber-500">
          {preview}
        </p>
      )}

      {concepts?.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1">
          {concepts.slice(0, 3).map((c) => (
            <span
              key={c}
              className="flex items-center gap-1 rounded-full border border-umber-200 bg-umber-100/60 px-2 py-0.5 font-mono text-[10px] text-umber-600"
            >
              <Layers className="h-2.5 w-2.5" />
              {c}
            </span>
          ))}
          {concepts.length > 3 && (
            <span className="px-1 font-mono text-[10px] text-umber-400">
              +{concepts.length - 3}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

export default memo(ConceptNode)
