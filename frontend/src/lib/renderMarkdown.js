/**
 * Minimal markdown-to-HTML converter for LLM responses.
 * Handles: **bold**, *italic*, `code`, bullet lists (* / -), 
 * numbered lists, headings (#/##/###), blank-line paragraphs.
 * No external dependency needed — the output is simple enough
 * that a small regex chain is safer than shipping a full parser.
 */
export function renderMarkdown(md) {
  if (!md) return ''

  const lines = md.split('\n')
  const html = []
  let inList = false
  let inOrderedList = false

  const closeList = () => {
    if (inList)        { html.push('</ul>'); inList = false }
    if (inOrderedList) { html.push('</ol>'); inOrderedList = false }
  }

  const inline = (text) =>
    text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/_(.+?)_/g, '<em>$1</em>')
      .replace(/`(.+?)`/g, '<code class="inline-code">$1</code>')

  for (const raw of lines) {
    const line = raw.trimEnd()

    // Headings
    if (/^### /.test(line)) {
      closeList()
      html.push(`<h3 class="md-h3">${inline(line.slice(4))}</h3>`)
      continue
    }
    if (/^## /.test(line)) {
      closeList()
      html.push(`<h2 class="md-h2">${inline(line.slice(3))}</h2>`)
      continue
    }
    if (/^# /.test(line)) {
      closeList()
      html.push(`<h1 class="md-h1">${inline(line.slice(2))}</h1>`)
      continue
    }

    // Unordered bullets: * or -
    if (/^[\*\-] /.test(line)) {
      if (inOrderedList) { html.push('</ol>'); inOrderedList = false }
      if (!inList)       { html.push('<ul class="md-ul">'); inList = true }
      html.push(`<li>${inline(line.slice(2))}</li>`)
      continue
    }

    // Ordered list: 1. 2. etc
    if (/^\d+\. /.test(line)) {
      if (inList) { html.push('</ul>'); inList = false }
      if (!inOrderedList) { html.push('<ol class="md-ol">'); inOrderedList = true }
      html.push(`<li>${inline(line.replace(/^\d+\. /, ''))}</li>`)
      continue
    }

    // Blank line — close lists, paragraph break
    if (line.trim() === '') {
      closeList()
      html.push('<br/>')
      continue
    }

    // Normal paragraph line
    closeList()
    html.push(`<p class="md-p">${inline(line)}</p>`)
  }

  closeList()

  // Collapse consecutive <br/> into one
  return html.join('\n').replace(/(<br\/>[\n\s]*){2,}/g, '<br/>')
}
