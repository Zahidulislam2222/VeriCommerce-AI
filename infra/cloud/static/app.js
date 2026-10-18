/* Immutable synthetic browser reference. No dynamic HTML or external requests. */
/* global document, window, fetch, crypto, TextDecoder */
const form = document.querySelector('form')
const query = document.querySelector('#query')
const status = document.querySelector('#status')
const results = document.querySelector('#results')
const button = document.querySelector('button')

async function start() {
  const configResponse = await fetch(document.querySelector('main').dataset.config)
  if (!configResponse.ok) throw new Error('configuration unavailable')
  const config = await configResponse.json()
  const snapshotResponse = await fetch(config.snapshot_file)
  const hashResponse = await fetch(config.snapshot_sha256_file)
  if (!snapshotResponse.ok || !hashResponse.ok) throw new Error('snapshot unavailable')
  const snapshotBytes = await snapshotResponse.arrayBuffer()
  const calculated = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', snapshotBytes)),
    value => value.toString(16).padStart(2, '0')).join('')
  if (calculated !== (await hashResponse.text()).trim()) throw new Error('snapshot integrity failure')
  const snapshot = JSON.parse(new TextDecoder().decode(snapshotBytes))
  if (snapshot.classification !== config.fixture_label || !Array.isArray(snapshot.documents) ||
      snapshot.documents.length > config.max_documents) throw new Error('invalid synthetic snapshot')
  query.maxLength = config.max_query_chars
  query.disabled = false
  button.disabled = false
  status.textContent = 'Public synthetic snapshot ready.'
  form.addEventListener('submit', event => {
    event.preventDefault()
    results.replaceChildren()
    const tokens = new Set(query.value.toLocaleLowerCase('en').match(/\w+/g) || [])
    const matches = snapshot.documents.map(document => ({ ...document,
      score: [...new Set(document.text.toLocaleLowerCase('en').match(/\w+/g) || [])]
        .filter(token => tokens.has(token)).length,
    })).filter(document => document.score > 0)
      .sort((left, right) => right.score - left.score || left.id.localeCompare(right.id, 'en'))
      .slice(0, config.max_results)
    for (const document of matches) {
      const item = window.document.createElement('li')
      const label = window.document.createElement('strong')
      label.textContent = document.id
      item.append(label, window.document.createTextNode(document.text))
      results.append(item)
    }
    status.textContent = matches.length ? `${matches.length} source quotation(s).` : 'No matching evidence.'
  })
}

start().catch(() => { status.textContent = 'The public snapshot could not be verified. Search is unavailable.' })
