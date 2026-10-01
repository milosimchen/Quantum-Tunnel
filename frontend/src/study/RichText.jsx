import katex from 'katex'
import 'katex/dist/katex.min.css'

export function Tex({ tex, display = false }) {
  const html = katex.renderToString(tex, { displayMode: display, throwOnError: false })
  return <span className={display ? 'tex-display' : 'tex-inline'} dangerouslySetInnerHTML={{ __html: html }} />
}

// Splits text on $...$ (inline math), **...** (bold) and `...` (code).
// Content comes from lessons.js, which is ours, never from users.
const TOKEN = /(\$[^$]+\$|\*\*[^*]+\*\*|`[^`]+`)/g

export function RichText({ text }) {
  return text.split(TOKEN).map((part, i) => {
    if (part.startsWith('$') && part.endsWith('$') && part.length > 1) return <Tex key={i} tex={part.slice(1, -1)} />
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={i}>{part.slice(2, -2)}</strong>
    if (part.startsWith('`') && part.endsWith('`')) return <code key={i}>{part.slice(1, -1)}</code>
    return part
  })
}
