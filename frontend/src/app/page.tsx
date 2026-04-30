'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

interface Series {
  id: number
  name: string
  label: string | null
  episode_count: number
}

export default function HomePage() {
  const [series, setSeries] = useState<Series[]>([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      const { data, error } = await supabase.rpc('get_series_with_episode_count')
      if (!error) setSeries(data)
      setLoading(false)
    }
    load()
  }, [])

  const filtered = series.filter((s) =>
    s.name.toLowerCase().includes(query.toLowerCase())
  )

  return (
    <main className="max-w-5xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold mb-2">Hörspiel Explorer</h1>
      <p className="text-gray-500 mb-6">
        {series.length} Serien · {series.reduce((acc, s) => acc + s.episode_count, 0).toLocaleString('de')} Episoden
      </p>

      <input
        type="text"
        placeholder="Serie suchen..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full border border-gray-300 rounded-lg px-4 py-2 mb-8 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />

      {loading ? (
        <p className="text-gray-400">Lade Serien...</p>
      ) : (
        <>
          {query && (
            <p className="text-sm text-gray-500 mb-4">{filtered.length} Ergebnisse</p>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((s) => (
              <div
                key={s.id}
                className="border border-gray-200 rounded-lg p-4 hover:border-gray-400 transition-colors cursor-pointer"
              >
                <h2 className="font-semibold text-lg leading-tight">{s.name}</h2>
                {s.label && s.label !== '?' && (
                  <p className="text-sm text-gray-500 mt-1">{s.label}</p>
                )}
                <p className="text-sm font-medium mt-3 text-blue-600">
                  {s.episode_count} Folgen
                </p>
              </div>
            ))}
          </div>
        </>
      )}
    </main>
  )
}