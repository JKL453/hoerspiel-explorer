import { supabase } from '@/lib/supabase'
import Link from 'next/link'

async function getSpeaker(id: string) {
  const { data, error } = await supabase
    .from('speakers')
    .select('id, name')
    .eq('id', parseInt(id))
    .single()
  if (error) return null
  return data
}

async function getEpisodesBySpeaker(id: string) {
  const { data, error } = await supabase
    .rpc('get_episodes_by_speaker', { speaker_id_input: parseInt(id) })
  if (error) return []
  return data
}

export default async function SpeakerPage({
  params,
}: {
  params: { id: string }
}) {
  const { id } = await params
  const [speaker, episodes] = await Promise.all([
    getSpeaker(id),
    getEpisodesBySpeaker(id),
  ])

  if (!speaker) {
    return <p className="p-10 text-gray-500">Sprecher nicht gefunden.</p>
  }

  // Group episodes by series
  const bySeries = episodes.reduce((acc: any, ep: any) => {
    const key = ep.series_name ?? 'Ohne Serie'
    if (!acc[key]) acc[key] = { series_id: ep.series_id, episodes: [] }
    acc[key].episodes.push(ep)
    return acc
  }, {})

  return (
    <main className="max-w-3xl mx-auto px-4 py-10">
      <Link href="/" className="text-sm text-blue-500 hover:underline mb-6 block">
        ← Zurück zur Übersicht
      </Link>

      <h1 className="text-2xl font-bold mb-1">{speaker.name}</h1>
      <p className="text-gray-500 text-sm mb-8">
        {episodes.length} Episoden in {Object.keys(bySeries).length} Serien
      </p>

      <div className="flex flex-col gap-8">
        {Object.entries(bySeries).map(([seriesName, group]: [string, any]) => (
          <div key={seriesName}>
            <Link
              href={`/series/${group.series_id}`}
              className="text-base font-semibold text-blue-600 hover:underline mb-3 block"
            >
              {seriesName}
            </Link>
            <div className="flex flex-col">
              {group.episodes.map((ep: any) => (
                <Link
                  key={ep.episode_id}
                  href={`/episodes/${ep.episode_id}`}
                  className="flex items-center justify-between text-sm py-2 border-b border-gray-100 hover:bg-gray-50 px-1"
                >
                  <div className="flex items-center gap-2">
                    {ep.cover_url && (
                      <img
                        src={ep.cover_url}
                        alt={ep.title}
                        className="w-8 h-8 object-cover rounded"
                      />
                    )}
                    <div>
                      <span className="font-medium">{ep.title}</span>
                      {ep.role_name && (
                        <span className="text-gray-400 ml-2">als {ep.role_name}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-3 text-gray-400 text-xs flex-shrink-0">
                    {ep.episode_number && <span>#{ep.episode_number}</span>}
                    {ep.release_date && (
                      <span>{new Date(ep.release_date).getFullYear()}</span>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </main>
  )
}