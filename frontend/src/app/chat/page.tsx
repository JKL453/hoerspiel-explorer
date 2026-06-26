'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import ReactMarkdown from 'react-markdown'


interface Episode {
  id: number
  title: string
  series_name: string
  episode_number: number
  description: string
  release_date: string
  duration_minutes: number
  cover_url: string
  similarity: number
}

interface ChatResponse {
  response: string
  episodes: Episode[]
}

export default function ChatPage() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ChatResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Restore state from sessionStorage on mount
  useEffect(() => {
    const saved = sessionStorage.getItem('chat_result')
    const savedQuery = sessionStorage.getItem('chat_query')
    if (saved) setResult(JSON.parse(saved))
    if (savedQuery) setQuery(savedQuery)
  }, [])

  // Save state to sessionStorage whenever it changes
  useEffect(() => {
    if (result) {
      sessionStorage.setItem('chat_result', JSON.stringify(result))
    }
    if (query) {
      sessionStorage.setItem('chat_query', query)
    }
  }, [result, query])

  async function handleSubmit() {
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    // Clear old results when making new request
    sessionStorage.removeItem('chat_result')

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error)
      setResult(data)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="max-w-3xl mx-auto px-4 py-10">
      <Link href="/" className="text-sm text-blue-500 hover:underline mb-6 block">
        ← Zurück zur Übersicht
      </Link>

      <h1 className="text-3xl font-bold mb-2">Hörspiel-Empfehlungen</h1>
      <p className="text-gray-500 mb-8">
        Beschreibe was du hören möchtest — Stimmung, Thema, Genre, Zielgruppe.
      </p>

      <div className="flex gap-2 mb-8">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          placeholder="z.B. Gruselige Weihnachtsgeschichte für Erwachsene"
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="bg-blue-600 text-white px-5 py-2 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {loading ? '...' : 'Suchen'}
        </button>
      </div>

      {error && (
        <p className="text-red-500 text-sm mb-6">{error}</p>
      )}

      {loading && (
        <div className="text-gray-400 text-sm animate-pulse">
          Suche passende Hörspiele...
        </div>
      )}

      {result && (
        <div className="flex flex-col gap-8">
        {/* LLM Response */}
        <div className="bg-blue-50 border border-blue-100 rounded-lg p-5">
          <p className="text-sm font-semibold text-blue-700 mb-3">Empfehlung</p>
          <div className="text-gray-800 text-sm leading-relaxed [&>p]:mb-3 [&>ul]:list-disc [&>ul]:pl-5 [&>ul]:mb-3 [&>li]:mb-1 [&>strong]:font-semibold">
            <ReactMarkdown>{result.response}</ReactMarkdown>
          </div>
        </div>


          {/* Episodes */}
          <div>
            <p className="text-sm font-semibold text-gray-500 mb-3">
              Gefundene Hörspiele ({result.episodes.length})
            </p>
            <div className="flex flex-col gap-3">
              {result.episodes.map((ep) => (
                <Link
                  key={ep.id}
                  href={`/episodes/${ep.id}`}
                  className="border border-gray-200 rounded-lg p-4 flex gap-4"
                >
                  {ep.cover_url && (
                    <img
                      src={ep.cover_url}
                      alt={ep.title}
                      className="w-14 h-14 object-cover rounded flex-shrink-0"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {ep.episode_number && (
                        <span className="text-xs font-mono text-gray-400">
                          #{ep.episode_number}
                        </span>
                      )}
                      <h3 className="font-semibold truncate">{ep.title}</h3>
                    </div>
                    {ep.series_name && (
                      <p className="text-sm text-blue-600 mb-1">{ep.series_name}</p>
                    )}
                    {ep.description && (
                      <p className="text-sm text-gray-600 line-clamp-2">
                        {ep.description}
                      </p>
                    )}
                    <div className="flex gap-3 mt-2 text-xs text-gray-400">
                      {ep.release_date && (
                        <span>{new Date(ep.release_date).getFullYear()}</span>
                      )}
                      {ep.duration_minutes && (
                        <span>{Math.round(ep.duration_minutes)} Min.</span>
                      )}
                      <span className="text-green-600">
                        {Math.round(ep.similarity * 100)}% Match
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}
    </main>
  )
}