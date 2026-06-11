/**
 * Markdown 渲染工具
 * 将 Markdown 文本渲染为安全的 HTML 字符串
 */

const ESC_MAP = { '&': '&amp;', '<': '&lt;', '>': '&gt;' }

function escapeHtml(text) {
  return text.replace(/[&<>]/g, ch => ESC_MAP[ch])
}

// ---- 行级内联处理 ----

const INLINE_RULES = [
  // 图片（先于链接处理）
  [/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" class="ds-md-img">'],
  // 链接
  [/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>'],
  // 行内代码
  [/`([^`]+)`/g, '<code>$1</code>'],
  // 加粗 + 斜体 ***
  [/\*\*\*([^*]+)\*\*\*/g, '<strong><em>$1</em></strong>'],
  // 加粗 **
  [/\*\*([^*]+)\*\*/g, '<strong>$1</strong>'],
  // 斜体 *
  [/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>'],
  // 删除线 ~~
  [/~~([^~]+)~~/g, '<del>$1</del>'],
]

function inlineMd(text) {
  if (!text) return ''
  let html = text
  for (const [pattern, replacement] of INLINE_RULES) {
    html = html.replace(pattern, replacement)
  }
  return html
}

// ---- 块级解析 ----

/**
 * @param {string} content 原始 Markdown 文本
 * @returns {string} 安全 HTML
 */
export function renderMessage(content) {
  if (!content) return ''

  // ----- 1. 提取代码块 -----
  const codeBlocks = []
  const PLACEHOLDER = '\x00CB\x00'
  // 先匹配 ```lang\ncode``` 再匹配 ```\ncode```
  const textWithoutCode = content.replace(
    /```(\w+)?\s*\n?([\s\S]*?)```/g,
    (_, lang, code) => {
      const idx = codeBlocks.length
      const langTag = lang
        ? `<span class="ds-code-lang">${escapeHtml(lang)}</span>`
        : ''
      // 仅对内容做 HTML 转义（一次即可），保留空白
      const escaped = escapeHtml(code)
      codeBlocks.push(
        `<div class="ds-code-block">${langTag}<pre><code>${escaped}</code></pre></div>`
      )
      return `${PLACEHOLDER}${idx}`
    }
  )

  // ----- 2. 转义非代码块部分 -----
  // 先把占位符保护起来
  const protectedLines = textWithoutCode
    .split('\n')
    .map(line => {
      // 如果行包含占位符，先转义占位符外的部分
      if (line.includes(PLACEHOLDER)) {
        const parts = line.split(new RegExp(`(${PLACEHOLDER}\\d+)`))
        return parts.map(p =>
          p.startsWith(PLACEHOLDER) ? p : escapeHtml(p)
        ).join('')
      }
      return escapeHtml(line)
    })

  // ----- 3. 逐行块级解析 -----
  const out = []
  let inTable = false
  let tableRows = []
  let listStack = [] // [{type: 'ul', indent, items:[]}]

  function flushTable() {
    if (!inTable) return
    out.push('<table>')
    for (const row of tableRows) {
      out.push('<tr>' + row.map(c => `<td>${c.trim() || '&nbsp;'}</td>`).join('') + '</tr>')
    }
    out.push('</table>')
    tableRows = []
    inTable = false
  }

  function flushList() {
    if (!listStack.length) return
    for (const list of listStack) {
      out.push(`<${list.type}>`)
      for (const item of list.items) {
        out.push(`<li>${item}</li>`)
      }
      out.push(`</${list.type}>`)
    }
    listStack = []
  }

  for (let rawLine of protectedLines) {
    const trimmed = rawLine.trim()

    // 恢复代码块占位符
    const placeholderMatch = trimmed.match(new RegExp(`^${PLACEHOLDER}(\\d+)$`))
    if (placeholderMatch) {
      flushTable()
      flushList()
      out.push(codeBlocks[parseInt(placeholderMatch[1])])
      continue
    }

    // 空行
    if (!trimmed) {
      flushTable()
      flushList()
      continue
    }

    // 表格分隔行（支持多列，如 | --- | :---: | ---: |）
    if (/^\|[\s\-:]+(\|[\s\-:]+)*\|$/.test(trimmed)) continue

    // 表格行
    if (/^\|.*\|$/.test(trimmed) && trimmed.startsWith('|') && trimmed.endsWith('|')) {
      flushList()
      if (!inTable) {
        inTable = true
        tableRows = []
      }
      const cells = rawLine.split('|').slice(1, -1)
      if (cells.length >= 1) {
        tableRows.push(cells.map(c => inlineMd(c.trim())))
      }
      continue
    }

    flushTable()

    // 水平线
    if (/^(-{3,}|\*{3,})$/.test(trimmed)) {
      flushList()
      out.push('<hr>')
      continue
    }

    // 标题
    const hMatch = rawLine.match(/^(#{1,6})\s+(.+)$/)
    if (hMatch) {
      flushList()
      out.push(`<h${hMatch[1].length}>${inlineMd(hMatch[2])}</h${hMatch[1].length}>`)
      continue
    }

    // 引用（支持多层 > ）
    if (/^>+\s/.test(trimmed)) {
      flushList()
      const depth = trimmed.match(/^>+/)[0].length
      const content = inlineMd(trimmed.replace(/^>+\s*/, ''))
      out.push(`${'<blockquote>'.repeat(depth)}<p>${content}</p>${'</blockquote>'.repeat(depth)}`)
      continue
    }

    // 列表
    const ulM = rawLine.match(/^(\s*)[*\-+]\s+(.+)$/)
    const olM = rawLine.match(/^(\s*)\d+\.\s+(.+)$/)
    if (ulM || olM) {
      const indent = ulM ? ulM[1].length : olM[1].length
      const content = inlineMd(ulM ? ulM[2] : olM[2])
      const type = ulM ? 'ul' : 'ol'

      // 找到对应的列表层级
      while (listStack.length > 0 && listStack[listStack.length - 1].indent >= indent) {
        const list = listStack.pop()
        out.push(`<${list.type}>`)
        for (const item of list.items) {
          out.push(`<li>${item}</li>`)
        }
        out.push(`</${list.type}>`)
      }

      if (listStack.length === 0 || listStack[listStack.length - 1].indent < indent) {
        listStack.push({ type, indent, items: [content] })
      } else {
        listStack[listStack.length - 1].items.push(content)
      }
      continue
    }

    flushList()

    // 普通段落（包含已含内联标记的行）
    const parsed = inlineMd(rawLine)
    if (parsed) {
      out.push(`<p>${parsed}</p>`)
    }
  }

  // 收尾
  flushTable()
  flushList()

  return out.join('\n')
}
