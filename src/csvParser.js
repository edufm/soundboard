// Hand-rolled CSV parsing. Assumption: fields never contain commas or quotes
// (fine for name/tab/path values in this toy project's data).

export function parseTimeToSeconds(str) {
  const match = /^(\d+):(\d{2}):(\d{2})(?:\.(\d+))?$/.exec(str.trim())
  if (!match) {
    console.warn(`Invalid time "${str}", expected hh:mm:ss.mmm`)
    return NaN
  }
  const [, h, m, s, frac] = match
  const fraction = frac ? Number(`0.${frac}`) : 0
  return Number(h) * 3600 + Number(m) * 60 + Number(s) + fraction
}

export function parseCSV(text) {
  const lines = text
    .split(/\r\n|\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !line.startsWith('#'))

  if (lines.length === 0) return []

  const header = lines[0].split(',').map((h) => h.trim())
  const colIndex = Object.fromEntries(header.map((name, i) => [name, i]))

  const required = ['name', 'tab', 'start_time', 'end_time', 'path_to_file']
  for (const col of required) {
    if (!(col in colIndex)) {
      console.warn(`sounds.csv is missing required column "${col}"`)
      return []
    }
  }

  const rows = []
  for (const line of lines.slice(1)) {
    const cells = line.split(',').map((c) => c.trim())
    const startTime = parseTimeToSeconds(cells[colIndex.start_time])
    const endTime = parseTimeToSeconds(cells[colIndex.end_time])
    if (Number.isNaN(startTime) || Number.isNaN(endTime)) {
      console.warn(`Skipping row with invalid time: ${line}`)
      continue
    }
    rows.push({
      name: cells[colIndex.name],
      tab: cells[colIndex.tab],
      startTime,
      endTime,
      path: cells[colIndex.path_to_file],
      // "parent" is optional: blank/absent means a top-level button, otherwise
      // it's the `name` of the button this row is a variation of.
      parent: colIndex.parent !== undefined ? cells[colIndex.parent] || '' : '',
      // "gain_db" is optional: a per-clip volume adjustment (in dB) applied at
      // playback, e.g. to level out clips that were measured louder/quieter
      // than a target loudness. Blank/absent means no adjustment (0dB).
      gainDb: colIndex.gain_db !== undefined ? Number(cells[colIndex.gain_db]) || 0 : 0,
    })
  }
  return rows
}

// Builds one level of nesting: top-level rows (parent === '') become buttons,
// each carrying a `variations` array of the rows that named it as their parent.
// A variation whose own parent is itself a variation is not supported (and is
// skipped with a warning) — the UI only expands one level of bubbles.
export function groupByTab(rows) {
  const parentRows = rows.filter((row) => !row.parent)
  const childRows = rows.filter((row) => row.parent)

  const tabOrder = []
  const tabsMap = {}
  for (const row of parentRows) {
    if (!(row.tab in tabsMap)) {
      tabOrder.push(row.tab)
      tabsMap[row.tab] = []
    }
    tabsMap[row.tab].push({ ...row, variations: [] })
  }

  for (const child of childRows) {
    const siblings = tabsMap[child.tab]
    const parent = siblings?.find((row) => row.name === child.parent)
    if (!parent) {
      console.warn(
        `Variation "${child.name}" references unknown parent "${child.parent}" in tab "${child.tab}"`,
      )
      continue
    }
    parent.variations.push(child)
  }

  return { tabOrder, tabsMap }
}

export async function loadSounds(csvUrl = '/sounds.csv') {
  const response = await fetch(csvUrl)
  if (!response.ok) {
    throw new Error(`Failed to load ${csvUrl}: ${response.status}`)
  }
  const text = await response.text()
  return groupByTab(parseCSV(text))
}
