/**
 * True when every word in the query appears in the given fields (case-insensitive, any order).
 * A one-letter word (as in "lager a") must start a word, so it does not match every "a" that
 * happens to sit inside other words.
 */
export function matchesSearch(fields: string[], query: string): boolean {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  const text = fields.join(' ').toLowerCase()
  return words.every((word) =>
    word.length > 1 ? text.includes(word) : text.startsWith(word) || text.includes(` ${word}`),
  )
}
