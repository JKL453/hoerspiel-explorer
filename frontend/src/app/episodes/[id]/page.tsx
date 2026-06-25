import { supabase } from '@/lib/supabase'
import Link from 'next/link'
import BackButton from '@/components/BackButton'

async function getEpisode(id: string) {
  console.log('Fetching episode with id:', id)
  const { data, error } = await supabase
    .from('episodes')
    .select(`
      id,
      title,
      episode_number,
      description,
      duration_minutes,
      release_date,
      cover_url,
      source_url,
      series:series_id (
        id,
        name,
        label
      )
    `)
    .eq('id', parseInt(id))
    .single()
console.log('Result:', data, 'Error:', error)
  if (error) return null
  return data
}

async function getSpeakers(episodeId: string) {
  const { data, error } = await supabase
    .from('episode_speakers')
    .select(`
      speakers (id, name),
      roles (name)
    `)
    .eq('episode_id', parseInt(episodeId))
  if (error) return []
  return data
}

async function getGenres(episodeId: string) {
  const { data, error } = await supabase
    .from('episode_genres')
    .select('genres (name)')
    .eq('episode_id', parseInt(episodeId))
  if (error) return []
  return data
}

export default async function EpisodePage({
  params,
}: {
  params: { id: string }
  searchParams: { from?: string }
}) {
  const { id } = await params
  const [episode, speakers, genres] = await Promise.all([
    getEpisode(id),
    getSpeakers(id),
    getGenres(id),
  ])

  if (!episode) {
    return <p className="p-10 text-gray-500">Episode nicht gefunden.</p>
  }

  const series = episode.series as any


  return (
    <main className="max-w-3xl mx-auto px-4 py-10">
      <BackButton label={series ? `← ${series.name}` : '← Zurück'} />

      <div className="flex gap-6 mb-8">
        {episode.cover_url ? (
          <img
            src={episode.cover_url}
            alt={episode.title ?? ''}
            className="w-32 h-32 object-cover rounded-lg flex-shrink-0 shadow"
          />
        ) : (
          <div className="w-32 h-32 bg-gray-100 rounded-lg flex-shrink-0 flex items-center justify-center text-gray-400 text-sm">
            Kein Cover
          </div>
        )}

        <div>
          <div className="flex items-center gap-2 mb-1">
            {episode.episode_number && (
              <span className="text-sm font-mono text-gray-400">
                #{episode.episode_number}
              </span>
            )}
            {series && (
              <Link
                href={`/series/${series.id}`}
                className="text-sm text-blue-500 hover:underline"
              >
                {series.name}
              </Link>
            )}
          </div>
          <h1 className="text-2xl font-bold mb-3">{episode.title}</h1>

          <div className="flex flex-wrap gap-3 text-sm text-gray-500">
            {episode.release_date && (
              <span>{new Date(episode.release_date).getFullYear()}</span>
            )}
            {episode.duration_minutes && (
              <span>{Math.round(episode.duration_minutes)} Min.</span>
            )}
            {series?.label && series.label !== '?' && (
              <span>{series.label}</span>
            )}
          </div>

          {genres.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {genres.map((g: any) => (
                <span
                  key={g.genres.name}
                  className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full"
                >
                  {g.genres.name}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {episode.description && (
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Beschreibung
          </h2>
          <p className="text-gray-700 leading-relaxed">{episode.description}</p>
        </div>
      )}

      {speakers.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Sprecher
          </h2>
          <div className="flex flex-col">
            {speakers.map((s: any, i: number) => (
              <div key={i} className="flex justify-between text-sm py-2 border-b border-gray-100">
                <span className="text-gray-500">{s.roles.name}</span>
                <Link
                  href={`/speakers/${s.speakers.id}`}
                  className="font-medium text-blue-600 hover:underline text-right"
                >
                  {s.speakers.name}
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {episode.source_url && (
        <div className="mt-6">
          <a
            href={episode.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-500 hover:underline"
          >
            Auf hoerspiele.de ansehen →
          </a>
        </div>
      )}
    </main>
  )
}