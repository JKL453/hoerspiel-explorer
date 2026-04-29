import { supabase } from '@/lib/supabase'

interface Series {
  id: number
  name: string
  label: string | null
  episode_count: number
}

async function getSeries(): Promise<Series[]> {
  const { data, error } = await supabase.rpc('get_series_with_episode_count')
  if (error) throw error
  return data
}

export default async function HomePage() {
  const series = await getSeries()

  return (
    <main className="max-w-5xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold mb-2">Hörspiel Explorer</h1>
      <p className="text-gray-500 mb-8">
        {series.length} Serien · {series.reduce((acc, s) => acc + s.episode_count, 0).toLocaleString('de')} Episoden
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {series.map((s) => (
          <div
            key={s.id}
            className="border border-gray-200 rounded-lg p-4 hover:border-gray-400 transition-colors"
          >
            <h2 className="font-semibold text-lg leading-tight">{s.name}</h2>
            {s.label && (
              <p className="text-sm text-gray-500 mt-1">{s.label}</p>
            )}
            <p className="text-sm font-medium mt-3 text-blue-600">
              {s.episode_count} Folgen
            </p>
          </div>
        ))}
      </div>
    </main>
  )
}