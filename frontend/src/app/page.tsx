'use client'

import { useState, useEffect, useCallback, useRef } from 'react'

interface SearchResult {
  id: string
  source_table: string
  code: string
  description: string | null
  year_bundle: number | null
  yeardate: number | null
  box_number: string
  bundle_number: number | null
  title: string
  item_number: number | null
  name: string
  organization: string
  creator: string
  bundle_code: string
  filesize: number | null
  page_count: number | null
  has_pdf: boolean
}

interface SearchResponse {
  query: string
  total: number
  processing_time_ms: number
  results: SearchResult[]
}

const TABLE_LABELS: Record<string, string> = {
  arsip_tata_year: 'Tahun',
  arsip_tata_box: 'Box',
  arsip_tata_bundle: 'Bundle',
  arsip_tata_item: 'Item',
}

export default function Home() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [total, setTotal] = useState(0)
  const [processingTime, setProcessingTime] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(0)
  const [reindexing, setReindexing] = useState(false)
  const [reindexMsg, setReindexMsg] = useState<string | null>(null)
  const [dark, setDark] = useState(true)
  const [pdfModal, setPdfModal] = useState<{result: SearchResult | null; watermark: boolean}>({result: null, watermark: false})
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfError, setPdfError] = useState<string | null>(null)
  const [thumbnailModal, setThumbnailModal] = useState<{result: SearchResult | null}>({result: null})
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const LIMIT = 20

  useEffect(() => {
    const stored = localStorage.getItem('theme')
    if (stored === 'light') setDark(false)
    else if (stored === 'dark') setDark(true)
    else setDark(window.matchMedia('(prefers-color-scheme: dark)').matches)
  }, [])

  const openPdfModal = (result: SearchResult, watermark: boolean) => {
    setPdfModal({result, watermark})
    setPdfError(null)
  }

  const closePdfModal = () => {
    setPdfModal({result: null, watermark: false})
    setPdfError(null)
    setPdfLoading(false)
  }

  const closeThumbnailModal = () => {
    setThumbnailModal({result: null})
  }

  const toggleTheme = () => {
    setDark(d => {
      const next = !d
      localStorage.setItem('theme', next ? 'dark' : 'light')
      if (next) {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
      return next
    })
  }

  const search = useCallback(async (q: string, offset: number = 0) => {
    if (!q.trim()) {
      setResults([])
      setTotal(0)
      return
    }

    setLoading(true)
    try {
      const params = new URLSearchParams({
        q,
        limit: String(LIMIT),
        offset: String(offset),
      })

      const res = await fetch(`/api/search?${params}`)
      const data: SearchResponse = await res.json()
      setResults(data.results)
      setTotal(data.total)
      setProcessingTime(data.processing_time_ms)
    } catch (err) {
      console.error('Search error:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const debounce = setTimeout(() => {
      search(query, page * LIMIT)
    }, 300)
    return () => clearTimeout(debounce)
  }, [query, page, search])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(0)
    search(query, 0)
  }

  const handleReindex = async () => {
    if (reindexing) return
    setReindexing(true)
    setReindexMsg(null)
    try {
      const res = await fetch('/api/sync', { method: 'POST' })
      const data = await res.json()
      if (res.ok) {
        setReindexMsg(`Berhasil! ${data.total_documents?.toLocaleString() || 0} dokumen diindex dari MySQL.`)
      } else {
        setReindexMsg(`Gagal: ${data.detail || 'Unknown error'}`)
      }
    } catch {
      setReindexMsg('Gagal: Tidak dapat terhubung ke server.')
    } finally {
      setReindexing(false)
      setTimeout(() => setReindexMsg(null), 5000)
    }
  }

  const totalPages = Math.ceil(total / LIMIT)

  const getTableLabel = (t: string) => TABLE_LABELS[t] || t

  const highlight = (text: string, q: string): React.ReactNode => {
    if (!q.trim() || !text) return text
    const words = q.trim().split(/\s+/).filter(Boolean)
    if (words.length === 0) return text
    const regex = new RegExp(`(${words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi')
    const parts = text.split(regex)
    return parts.map((part, i) =>
      regex.test(part) ? (
        <mark key={i} className="dark:bg-yellow-500/30 dark:text-yellow-200 bg-yellow-200 text-yellow-800 rounded px-0.5">{part}</mark>
      ) : part
    )
  }

  const pdfUrl = pdfModal.result
    ? `/api/pdf/${pdfModal.result.id}?watermark=${pdfModal.watermark}`
    : null

  return (
    <div className="min-h-screen flex flex-col dark:bg-slate-900 bg-slate-50">
      {/* PDF Viewer Modal */}
      {pdfModal.result && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={closePdfModal}>
          <div
            className="relative w-[95vw] h-[95vh] flex flex-col rounded-2xl overflow-hidden shadow-2xl bg-white dark:bg-slate-800"
            onClick={e => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 shrink-0">
              <div className="flex items-center gap-3 min-w-0">
                <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded ${
                  pdfModal.result.source_table === 'arsip_tata_item'
                    ? (dark ? 'bg-blue-900 text-blue-300' : 'bg-blue-100 text-blue-800')
                    : (dark ? 'bg-purple-900 text-purple-300' : 'bg-purple-100 text-purple-800')
                }`}>
                  {getTableLabel(pdfModal.result.source_table)}
                </span>
                <span className="text-sm font-mono font-medium dark:text-white text-slate-900 truncate">
                  {pdfModal.result.code || pdfModal.result.id}
                </span>
                {pdfModal.watermark && (
                  <span className="px-2 py-0.5 text-xs bg-red-100 dark:bg-red-900 text-red-600 dark:text-red-300 rounded">
                    WATERMARKED
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => openPdfModal(pdfModal.result!, !pdfModal.watermark)}
                  className={`px-3 py-1.5 text-xs rounded-lg font-medium transition ${
                    pdfModal.watermark
                      ? 'bg-slate-100 dark:bg-slate-700 dark:text-slate-300 text-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600'
                      : 'bg-red-600 hover:bg-red-500 text-white'
                  }`}
                  title={pdfModal.watermark ? 'Tampilkan tanpa watermark' : 'Tampilkan dengan watermark COPY'}
                >
                  {pdfModal.watermark ? 'Tanpa Watermark' : 'Watermark COPY'}
                </button>
                <a
                  href={pdfUrl || '#'}
                  download={`${pdfModal.result.code || pdfModal.result.id}.pdf`}
                  className="px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition flex items-center gap-1.5"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download
                </a>
                <button
                  onClick={closePdfModal}
                  className="p-1.5 rounded-lg dark:bg-slate-700 dark:hover:bg-slate-600 bg-slate-100 hover:bg-slate-200 transition"
                >
                  <svg className="w-4 h-4 dark:text-slate-300 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* PDF Content */}
            <div className="flex-1 overflow-hidden bg-slate-100 dark:bg-slate-900 relative">
              {pdfError ? (
                <div className="flex flex-col items-center justify-center h-full gap-3">
                  <svg className="w-12 h-12 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  <p className="text-slate-500 dark:text-slate-400">{pdfError}</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500">
                    PDF tidak ditemukan untuk record ini. Pastikan path PDF benar dan PDF_BASE_PATH di server sudah diset.
                  </p>
                </div>
              ) : (
                <iframe
                  ref={iframeRef}
                  src={pdfUrl || ''}
                  className="w-full h-full border-0"
                  title="PDF Viewer"
                  onLoad={() => setPdfLoading(false)}
                  onError={() => { setPdfLoading(false); setPdfError('Gagal memuat PDF') }}
                />
              )}
              {pdfLoading && (
                <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-slate-900/80">
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    <p className="text-sm text-slate-500 dark:text-slate-400">Memuat PDF...</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Thumbnail Lightbox Modal */}
      {thumbnailModal.result && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm cursor-zoom-out"
          onClick={closeThumbnailModal}
        >
          <img
            src={`/api/thumbnail/${thumbnailModal.result.id}`}
            alt="Full size preview"
            className="max-w-[95vw] max-h-[95vh] object-contain shadow-2xl rounded-lg"
            onClick={e => e.stopPropagation()}
          />
          <button
            onClick={closeThumbnailModal}
            className="absolute top-4 right-4 p-2 rounded-full bg-white/10 hover:bg-white/20 transition"
          >
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Header */}
      <header className="dark:border-slate-700 dark:bg-slate-900/80 bg-white/80 backdrop-blur sticky top-0 z-10 border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img src="/logo.png" alt="Logo" className="h-10 w-10 object-contain" />
              <div>
                <h1 className="text-xl font-bold dark:text-white text-slate-900">Arsip Finder</h1>
                <p className="text-sm dark:text-slate-400 text-slate-500">BWS Maluku Utara</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right text-xs dark:text-slate-500 text-slate-400">
                {total > 0 && (
                  <span>{total.toLocaleString()} hasil</span>
                )}
              </div>
              <button
                onClick={toggleTheme}
                className="p-2 rounded-lg transition dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 bg-slate-100 hover:bg-slate-200 text-slate-700"
                title="Toggle theme"
              >
                {dark ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                  </svg>
                )}
              </button>
              <button
                onClick={handleReindex}
                disabled={reindexing}
                className="px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:cursor-not-allowed text-white rounded-lg transition flex items-center gap-1.5"
                title="Reindex dari MySQL ke Meilisearch"
              >
                {reindexing ? (
                  <>
                    <div className="w-3 h-3 border-1.5 border-white border-t-transparent rounded-full animate-spin" />
                    Mengindex...
                  </>
                ) : (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Reindex
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Reindex notification */}
      {reindexMsg && (
        <div className="max-w-5xl mx-auto w-full px-4 mt-4">
          <div className={`px-4 py-3 rounded-lg text-sm ${reindexMsg.startsWith('Berhasil')
            ? (dark ? 'bg-green-900/60 text-green-300 border border-green-700' : 'bg-green-100 text-green-800 border border-green-300')
            : (dark ? 'bg-red-900/60 text-red-300 border border-red-700' : 'bg-red-100 text-red-800 border border-red-300')
          }`}>
            {reindexMsg}
          </div>
        </div>
      )}

      {/* Search Area */}
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-8">
        <form onSubmit={handleSearch} className="mb-6">
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => { setQuery(e.target.value); setPage(0) }}
              placeholder="Cari arsip... (contoh: irigasi, AMDAL, pembangunan bendung)"
              className="w-full px-5 py-4 pl-12 text-lg rounded-xl focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition
                dark:bg-slate-800 dark:border-slate-600 dark:text-white dark:placeholder-slate-500
                bg-white border-slate-300 text-slate-900 placeholder-slate-400"
              autoFocus
            />
            <svg
              className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 dark:text-slate-500 text-slate-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            {loading && (
              <div className="absolute right-4 top-1/2 -translate-y-1/2">
                <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
              </div>
            )}
          </div>
        </form>

        {/* Stats */}
        {total > 0 && (
          <div className="mb-4 text-sm dark:text-slate-500 text-slate-500 flex gap-4">
            <span>Ditemukan <strong className="dark:text-slate-300 text-slate-700">{total.toLocaleString()}</strong> hasil</span>
            <span>Waktu: <strong className="dark:text-slate-300 text-slate-700">{processingTime}ms</strong></span>
          </div>
        )}

        {/* Results */}
        {results.length > 0 ? (
          <div className="space-y-3">
            {results.map((result) => (
              <div
                key={result.id}
                className="rounded-xl p-4 transition cursor-pointer
                  dark:bg-slate-800 dark:border-slate-700 dark:hover:border-slate-500
                  bg-white border border-slate-200 hover:border-slate-400 shadow-sm"
              >
                {/* Thumbnail - float left, text wraps around */}
                <div
                  className="float-left mr-4 mb-2 cursor-zoom-in"
                  onClick={(e) => { e.stopPropagation(); setThumbnailModal({result}) }}
                >
                  <img
                    src={`/api/thumbnail/${result.id}`}
                    alt="Thumbnail"
                    className="w-24 h-32 object-cover rounded-lg bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                  />
                </div>

                {/* Content - flows around thumbnail, no flex */}
                <div className="min-w-0">
                  <div className="flex flex-wrap gap-2 mb-1">
                    <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded ${
                      result.source_table === 'arsip_tata_year'
                        ? (dark ? 'bg-slate-700 text-slate-300' : 'bg-slate-200 text-slate-700')
                        : result.source_table === 'arsip_tata_box'
                        ? (dark ? 'bg-amber-900 text-amber-300' : 'bg-amber-100 text-amber-800')
                        : result.source_table === 'arsip_tata_bundle'
                        ? (dark ? 'bg-purple-900 text-purple-300' : 'bg-purple-100 text-purple-800')
                        : (dark ? 'bg-blue-900 text-blue-300' : 'bg-blue-100 text-blue-800')
                    }`}>
                      {getTableLabel(result.source_table)}
                    </span>
                    {result.code && (
                      <span className="inline-block px-2 py-0.5 text-xs font-mono rounded dark:bg-slate-700 dark:text-slate-300 bg-slate-100 text-slate-700">
                        {result.code}
                      </span>
                    )}
                    {result.bundle_code && (
                      <span className="inline-block px-2 py-0.5 text-xs font-mono rounded dark:bg-slate-700 dark:text-slate-300 bg-slate-100 text-slate-700">
                        Bundle: {result.bundle_code}
                      </span>
                    )}
                    {result.item_number && (
                      <span className="inline-block px-2 py-0.5 text-xs font-mono rounded dark:bg-slate-700 dark:text-slate-300 bg-slate-100 text-slate-700">
                        Item #{result.item_number}
                      </span>
                    )}
                  </div>
                  <div className={`flex gap-2 text-xs shrink-0 dark:text-slate-500 text-slate-400`}>
                    {result.box_number && <span>Box: {result.box_number}</span>}
                    {result.yeardate && <span>Thn: {result.yeardate}</span>}
                  </div>

                  <p className="text-sm leading-relaxed whitespace-pre-line dark:text-slate-200 text-slate-800 mt-1">
                    {highlight(result.description || '-', query)}
                  </p>

                  {(result.title || result.name || result.organization || result.creator || result.page_count) && (
                    <div className={`mt-1 pt-1 grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 text-xs dark:text-slate-400 text-slate-500 ${dark ? 'border-t border-slate-700' : 'border-t border-slate-200'}`}>
                      {result.title && <span>Title: <span className="dark:text-slate-300 text-slate-700">{result.title}</span></span>}
                      {result.name && <span>Nama: <span className="dark:text-slate-300 text-slate-700">{result.name}</span></span>}
                      {result.organization && <span>Org: <span className="dark:text-slate-300 text-slate-700">{result.organization}</span></span>}
                      {result.creator && <span>Creator: <span className="dark:text-slate-300 text-slate-700">{result.creator}</span></span>}
                      {result.page_count && <span>Halaman: <span className="dark:text-slate-300 text-slate-700">{result.page_count}</span></span>}
                    </div>
                  )}

                  {/* PDF Buttons - always hidden, show red message if PDF exists */}
                  <div className="mt-2 pt-2 flex gap-2 border-t border-slate-200 dark:border-slate-700">
                    {result.has_pdf && (
                      <span className="text-xs text-red-600 dark:text-red-400 font-medium">
                        Hubungi bagian arsip untuk mendapatkan file PDF
                      </span>
                    )}
                  </div>
                </div>
                {/* Clear float */}
                <div className="clear-both" />
              </div>
            ))}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex justify-center gap-2 mt-6">
                <button
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="px-4 py-2 text-sm rounded-lg disabled:opacity-40 transition
                    dark:bg-slate-800 dark:border-slate-600 dark:hover:bg-slate-700
                    bg-white border border-slate-300 hover:bg-slate-50"
                >
                  Prev
                </button>
                <span className="px-4 py-2 text-sm dark:text-slate-400 text-slate-500">
                  Halaman {page + 1} dari {totalPages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                  className="px-4 py-2 text-sm rounded-lg disabled:opacity-40 transition
                    dark:bg-slate-800 dark:border-slate-600 dark:hover:bg-slate-700
                    bg-white border border-slate-300 hover:bg-slate-50"
                >
                  Next
                </button>
              </div>
            )}
          </div>
        ) : query && !loading ? (
          <div className="text-center py-16 dark:text-slate-500 text-slate-400">
            <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>Tidak ada hasil untuk <strong>&quot;{query}&quot;</strong></p>
          </div>
        ) : !query ? (
          <div className="text-center py-16 dark:text-slate-600 text-slate-400">
            <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <p>Mulai mengetik untuk mencari arsip</p>
            <p className="text-sm mt-1 dark:text-slate-700 text-slate-500">Contoh: irigasi, AMDAL, pembangunan bendung</p>
          </div>
        ) : null}
      </main>

      {/* Footer */}
      <footer className="dark:border-slate-800 dark:text-slate-600 border-t border-slate-200 text-xs text-center py-4 dark:bg-slate-900 bg-white">
        Arsip Finder — BWS Maluku Utara
      </footer>
    </div>
  )
}
