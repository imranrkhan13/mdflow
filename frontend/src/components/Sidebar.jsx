import { useState } from 'react'
import { Search, FileText, GitBranch } from 'lucide-react'

export default function Sidebar({ filename, nodes, selectedId, onSelect }) {
  const [query, setQuery] = useState('')

  const filtered = nodes.filter((n) =>
    n.data.title.toLowerCase().includes(query.toLowerCase())
  )

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-umber-200 px-4 py-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-clay/10">
          <GitBranch className="h-3.5 w-3.5 text-clay" />
        </div>
        <div className="min-w-0">
          <p className="truncate font-sans text-sm font-semibold text-umber-900">
            {filename}
          </p>
          <p className="font-mono text-[10px] text-umber-400">
            {nodes.length} concepts mapped
          </p>
        </div>
      </div>

      <div className="px-3 pt-3">
        <div className="flex items-center gap-2 rounded-lg border border-umber-200 bg-white px-2.5 py-1.5">
          <Search className="h-3.5 w-3.5 text-umber-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search concepts…"
            className="w-full bg-transparent font-sans text-xs text-umber-900 placeholder:text-umber-400 focus:outline-none"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3">
        <p className="px-1 pb-1.5 font-mono text-[10px] uppercase tracking-wider text-umber-400">
          Sections
        </p>
        <div className="flex flex-col gap-0.5">
          {filtered.map((n) => (
            <button
              key={n.id}
              onClick={() => onSelect(n.id)}
              className={`flex items-center gap-2 rounded-lg px-2.5 py-2 text-left font-sans text-xs transition-colors ${
                selectedId === n.id
                  ? 'bg-clay/10 text-clay'
                  : 'text-umber-600 hover:bg-umber-100/60 hover:text-umber-900'
              }`}
            >
              <FileText className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">{n.data.title}</span>
            </button>
          ))}
          {filtered.length === 0 && (
            <p className="px-2.5 py-2 font-sans text-xs text-umber-400">
              No matches.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
