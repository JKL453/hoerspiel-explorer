import { supabase } from '@/lib/supabase'
import Link from 'next/link'

interface Episode {
  id: number
  title: string | null
  episode_number: number | null
  description: string | null
  release_date: string | null
  duration_minutes: number | null
  cover_url: string | null
}

interface Series {
  id: number
  name: string
  label: string | null
}

async function getSeries(id: string): Promise<Series | null> {
  const { data, error } = await supabase
    .from('series')
    .select('id, name, label')
    .eq('id', id)
    .single()
  if (error) return null
  return data
}

async function getEpisodes(seriesId: string): Promise<Episode[]> {
  const { data, error } = await supabase
    .from('episodes')
    .select('id, title, episode_number, description, release_date, duration_minutes, cover_url')
    .eq('series_id', seriesId)
    .order('episode_number', { ascending: true })
  if (error) return []
  return data
}

export default async function SeriesPage({
  params,
}: {
  params: { id: string }
}) {
  const { id } = await params
  const [series, episodes] = await Promise.all([
    getSeries(id),
    getEpisodes(id),
  ])

  if (!series) {
    return <p className="p-10 text-gray-500">Serie nicht gefunden.</p>
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <Link href="/" className="text-sm text-blue-500 hover:underline mb-6 block">
        ← Zurück zur Übersicht
      </Link>

      <h1 className="text-3xl font-bold mb-1">{series.name}</h1>
      {series.label && series.label !== '?' && (
        <p className="text-gray-500 mb-6">{series.label}</p>
      )}
      <p className="text-sm text-gray-400 mb-8">{episodes.length} Folgen</p>

      <div className="flex flex-col gap-3">
        {episodes.map((ep) => (
        <Link href={`/episodes/${ep.id}`} key={ep.id}>
          <div className="border border-gray-200 rounded-lg p-4 hover:border-gray-400 transition-colors cursor-pointer flex gap-4"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  {ep.episode_number && (
                    <span className="text-xs font-mono text-gray-400">
                      #{ep.episode_number}
                    </span>
                  )}
                  <h2 className="font-semibold">{ep.title ?? '(Kein Titel)'}</h2>
                </div>
                {ep.description && (
                  <p className="text-sm text-gray-600 line-clamp-2">{ep.description}</p>
                )}
                <div className="flex gap-4 mt-2 text-xs text-gray-400">
                  {ep.release_date && (
                    <span>{new Date(ep.release_date).getFullYear()}</span>
                  )}
                  {ep.duration_minutes && (
                    <span>{Math.round(ep.duration_minutes)} Min.</span>
                  )}
                </div>
              </div>
              {ep.cover_url && (
                <img
                  src={ep.cover_url}
                  alt={ep.title ?? ''}
                  className="w-16 h-16 object-cover rounded"
                />
              )}
            </div>
          </div>
        </Link>
                    ))}
      </div>
    </main>
  )
}