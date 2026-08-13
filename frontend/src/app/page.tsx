'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import Link from 'next/link'

interface CategorySummary {
  category_key: string
  category_label: string
  category_order: number
  episode_count: number
}

interface Series {
  id: number
  name: string
  label: string | null
  episode_count: number
  category_counts: CategorySummary[]
}

interface SeriesCatalogRpcRow {
  id: number | string
  name: string
  label: string | null
  episode_count: number | string
  category_counts: unknown
}

function normalizeCategoryCounts(value: unknown): CategorySummary[] {
  if (!Array.isArray(value)) return []

  return value.flatMap((item) => {
    if (!item || typeof item !== 'object') return []
    const category = item as Record<string, unknown>
    if (
      typeof category.category_key !== 'string' ||
      typeof category.category_label !== 'string'
    ) {
      return []
    }
    return [{
      category_key: category.category_key,
      category_label: category.category_label,
      category_order: Number(category.category_order),
      episode_count: Number(category.episode_count),
    }]
  })
}

export default function HomePage() {
  const [series, setSeries] = useState<Series[]>([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(false)

  useEffect(() => {
    async function load() {
      let allSeries: Series[] = []
      let from = 0
      const pageSize = 1000

      while (true) {
        const { data, error } = await supabase
          .rpc('get_series_catalog_overview')
          .range(from, from + pageSize - 1)

        if (error) {
          setLoadError(true)
          break
        }
        if (!data || data.length === 0) break

        const page = (data as SeriesCatalogRpcRow[]).map((item) => ({
          id: Number(item.id),
          name: item.name,
          label: item.label,
          episode_count: Number(item.episode_count),
          category_counts: normalizeCategoryCounts(item.category_counts),
        }))
        allSeries = [...allSeries, ...page]

        if (data.length < pageSize) break
        from += pageSize
      }

      setSeries(allSeries)
      setLoading(false)
    }
    load()
  }, [])

  const filtered = series.filter((item) =>
    item.name.toLowerCase().includes(query.toLowerCase())
  )

  return (
    <main className="max-w-5xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold mb-2">Hörspiel Explorer</h1>
      <p className="text-gray-500 mb-6">
        {series.length} Serien · {series.reduce((sum, item) => sum + item.episode_count, 0).toLocaleString('de')} Veröffentlichungen
      </p>

      <Link
        href="/chat"
        className="inline-block bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors mb-8"
      >
        🎧 Hörspiel-Empfehlungen
      </Link>

      <Link
        href="/stats"
        className="inline-block border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:border-gray-500 transition-colors mb-8 ml-2"
      >
        📊 Statistiken
      </Link>

      <input
        type="text"
        placeholder="Serie suchen..."
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        className="w-full border border-gray-300 rounded-lg px-4 py-2 mb-8 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />

      {loading ? (
        <p className="text-gray-400">Lade Serien...</p>
      ) : loadError ? (
        <p className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          Der Serienkatalog konnte nicht geladen werden.
        </p>
      ) : (
        <>
          {query && (
            <p className="text-sm text-gray-500 mb-4">{filtered.length} Ergebnisse</p>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((item) => {
              const regular = item.category_counts.find((category) => category.category_key === 'regular')
              const variants = item.category_counts.filter((category) => category.category_key !== 'regular')

              return (
                <Link href={`/series/${item.id}`} key={item.id}>
                  <div className="h-full border border-gray-200 rounded-lg p-4 hover:border-gray-400 transition-colors cursor-pointer">
                    <h2 className="font-semibold text-lg leading-tight">{item.name}</h2>
                    {item.label && item.label !== '?' && (
                      <p className="text-sm text-gray-500 mt-1">{item.label}</p>
                    )}
                    <p className="text-sm font-medium mt-3 text-blue-600">
                      {item.episode_count} Veröffentlichungen
                    </p>
                    {(regular || variants.length > 0) && (
                      <p className="mt-2 text-xs leading-5 text-gray-500">
                        {[
                          regular && `${regular.episode_count} regulär`,
                          ...variants.slice(0, 2).map((category) =>
                            `${category.episode_count} ${category.category_label.toLowerCase()}`
                          ),
                        ].filter(Boolean).join(' · ')}
                      </p>
                    )}
                  </div>
                </Link>
              )
            })}
          </div>
        </>
      )}
    </main>
  )
}
