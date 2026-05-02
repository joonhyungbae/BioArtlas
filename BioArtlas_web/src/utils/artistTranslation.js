function normalizeKey(name) {
  return String(name || '')
    .trim()
    .replace(/\s+/g, ' ')
}

function resolveArtistLabel(artistName, artistLabelMap) {
  if (!artistName || !artistLabelMap) return ''
  const key = normalizeKey(artistName)
  if (artistLabelMap instanceof Map) {
    return artistLabelMap.get(key) || artistLabelMap.get(artistName) || ''
  }
  return artistLabelMap[key] || artistLabelMap[artistName] || ''
}

export function getLocalizedArtistName(artistName, artistLabelMap, localeCode) {
  if (!artistName) return artistName
  const isKo = typeof localeCode === 'string' && localeCode.toLowerCase().startsWith('ko')
  if (!isKo) {
    return artistName
  }

  const direct = resolveArtistLabel(artistName, artistLabelMap)
  if (direct) {
    return direct
  }

  const separators = [' & ', ', ']
  const separator = separators.find(sep => artistName.includes(sep))
  if (separator) {
    return artistName
      .split(separator)
      .map(name => resolveArtistLabel(name.trim(), artistLabelMap) || name.trim())
      .join(separator)
  }

  return artistName
}
