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
  category_key: string
  category_label: string
  variant_category: string
  edition_markers: string
}

interface CatalogFacet {
  production_line_key: string
  production_line_label: string
  production_line_order: number
  category_key: string
  category_label: string
  category_order: number
  episode_count: number
}

interface EpisodeCategory {
  category_key: string
  category_label: string
  category_order: number
  episode_count: number
}

interface Series {
  id: number
  name: string
  label: string | null
}

interface CategoryRpcRow {
  production_line_key: string
  production_line_label: string
  production_line_order: number | string
  category_key: string
  category_label: string
  category_order: number | string
  episode_count: number | string
}

interface EpisodeRpcRow {
  id: number | string
  title: string | null
  episode_number: number | string | null
  description: string | null
  release_date: string | null
  duration_minutes: number | string | null
  cover_url: string | null
  category_key: string
  category_label: string
  variant_category: string
  edition_markers: string
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

async function getFacets(seriesId: number): Promise<CatalogFacet[] | null> {
  const { data, error } = await supabase.rpc('get_series_catalog_facets', {
    series_id_input: seriesId,
  })
  if (error || !data) return null
  return (data as CategoryRpcRow[]).map((category) => ({
    ...category,
    production_line_order: Number(category.production_line_order),
    category_order: Number(category.category_order),
    episode_count: Number(category.episode_count),
  }))
}

async function getEpisodes(
  seriesId: number,
  category: string | null,
  productionLine: string | null,
): Promise<Episode[] | null> {
  const { data, error } = await supabase.rpc('get_series_episode_catalog', {
    series_id_input: seriesId,
    category_key_input: category,
    production_line_key_input: productionLine,
  })
  if (error || !data) return null
  return (data as EpisodeRpcRow[]).map((episode) => ({
    ...episode,
    id: Number(episode.id),
    episode_number: episode.episode_number === null ? null : Number(episode.episode_number),
    duration_minutes: episode.duration_minutes === null ? null : Number(episode.duration_minutes),
  }))
}

export default async function SeriesPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>
  searchParams: Promise<{ category?: string; production?: string }>
}) {
  const { id } = await params
  const { category: requestedCategory, production: requestedProduction } = await searchParams
  const seriesId = Number(id)
  const [series, facets] = await Promise.all([
    getSeries(id),
    getFacets(seriesId),
  ])

  if (!series) {
    return <p className="p-10 text-gray-500">Serie nicht gefunden.</p>
  }

  if (facets === null) {
    return (
      <main className="max-w-5xl mx-auto px-4 py-10">
        <Link href="/" className="text-sm text-blue-500 hover:underline mb-6 block">
          ← Zurück zur Übersicht
        </Link>
        <h1 className="text-3xl font-bold mb-4">{series.name}</h1>
        <p className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          Der kategorisierte Serienkatalog konnte nicht geladen werden.
        </p>
      </main>
    )
  }

  const productionMap = new Map<string, { label: string; order: number; count: number }>()
  for (const facet of facets) {
    const production = productionMap.get(facet.production_line_key)
    productionMap.set(facet.production_line_key, {
      label: facet.production_line_label,
      order: facet.production_line_order,
      count: (production?.count ?? 0) + facet.episode_count,
    })
  }
  const productionLines = [...productionMap.entries()].sort(([, a], [, b]) => a.order - b.order)
  const selectedProduction = requestedProduction === 'all'
    ? 'all'
    : requestedProduction && productionMap.has(requestedProduction)
      ? requestedProduction
      : productionLines[0]?.[0] ?? 'all'

  const visibleFacetRows = selectedProduction === 'all'
    ? facets
    : facets.filter((facet) => facet.production_line_key === selectedProduction)
  const categoryMap = new Map<string, EpisodeCategory>()
  for (const facet of visibleFacetRows) {
    const category = categoryMap.get(facet.category_key)
    categoryMap.set(facet.category_key, {
      category_key: facet.category_key,
      category_label: facet.category_label,
      category_order: facet.category_order,
      episode_count: (category?.episode_count ?? 0) + facet.episode_count,
    })
  }
  const categories = [...categoryMap.values()].sort((a, b) => a.category_order - b.category_order)
  const categoryKeys = new Set(categories.map((category) => category.category_key))
  const selectedCategory = requestedCategory === 'all'
    ? 'all'
    : requestedCategory && categoryKeys.has(requestedCategory)
      ? requestedCategory
      : categoryKeys.has('regular')
        ? 'regular'
        : 'all'
  const episodes = await getEpisodes(
    seriesId,
    selectedCategory === 'all' ? null : selectedCategory,
    selectedProduction === 'all' ? null : selectedProduction,
  )
  const totalCount = facets.reduce((sum, facet) => sum + facet.episode_count, 0)
  const selectedProductionCount = categories.reduce((sum, category) => sum + category.episode_count, 0)

  if (episodes === null) {
    return (
      <main className="max-w-5xl mx-auto px-4 py-10">
        <Link href="/" className="text-sm text-blue-500 hover:underline mb-6 block">
          ← Zurück zur Übersicht
        </Link>
        <h1 className="text-3xl font-bold mb-4">{series.name}</h1>
        <p className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          Die Veröffentlichungen konnten nicht geladen werden.
        </p>
      </main>
    )
  }

  return (
    <main className="max-w-5xl mx-auto px-4 py-10">
      <Link href="/" className="text-sm text-blue-500 hover:underline mb-6 block">
        ← Zurück zur Übersicht
      </Link>

      <h1 className="text-3xl font-bold mb-1">{series.name}</h1>
      {series.label && series.label !== '?' && (
        <p className="text-gray-500 mb-2">{series.label}</p>
      )}
      <p className="text-sm text-gray-400 mb-6">{totalCount} Veröffentlichungen</p>

      {productionLines.length > 1 && (
        <section className="mb-6">
          <h2 className="text-sm font-medium text-gray-700 mb-2">Produktionsreihe</h2>
          <nav aria-label="Produktionsreihen" className="flex gap-2 overflow-x-auto pb-2">
            <CategoryLink
              href={`/series/${id}?production=all`}
              label="Alle Reihen"
              count={totalCount}
              active={selectedProduction === 'all'}
            />
            {productionLines.map(([key, production]) => (
              <CategoryLink
                key={key}
                href={`/series/${id}?production=${encodeURIComponent(key)}`}
                label={production.label}
                count={production.count}
                active={selectedProduction === key}
              />
            ))}
          </nav>
        </section>
      )}

      <h2 className="text-sm font-medium text-gray-700 mb-2">Kategorie</h2>
      <nav aria-label="Veröffentlichungskategorien" className="flex gap-2 overflow-x-auto pb-3 mb-6">
        <CategoryLink
          href={`/series/${id}?production=${encodeURIComponent(selectedProduction)}&category=all`}
          label="Alle"
          count={selectedProductionCount}
          active={selectedCategory === 'all'}
        />
        {categories.map((category) => (
          <CategoryLink
            key={category.category_key}
            href={`/series/${id}?production=${encodeURIComponent(selectedProduction)}&category=${encodeURIComponent(category.category_key)}`}
            label={category.category_label}
            count={category.episode_count}
            active={selectedCategory === category.category_key}
          />
        ))}
      </nav>

      <p className="text-sm text-gray-500 mb-4">
        {episodes.length} {episodes.length === 1 ? 'Eintrag' : 'Einträge'}
      </p>

      {episodes.length === 0 ? (
        <p className="rounded-lg border border-gray-200 p-5 text-gray-500">
          In dieser Kategorie wurden keine Veröffentlichungen gefunden.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {episodes.map((episode) => (
            <Link href={`/episodes/${episode.id}`} key={episode.id}>
              <article className="border border-gray-200 rounded-lg p-4 hover:border-gray-400 transition-colors flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2 mb-1">
                    {episode.episode_number !== null && (
                      <span className="shrink-0 text-xs font-mono text-gray-400">
                        #{episode.episode_number}
                      </span>
                    )}
                    <h2 className="font-semibold">{episode.title ?? '(Kein Titel)'}</h2>
                  </div>
                  {selectedCategory === 'all' && (
                    <span className="inline-flex rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 mb-2">
                      {episode.category_label}
                    </span>
                  )}
                  {episode.description && (
                    <p className="text-sm text-gray-600 line-clamp-2">{episode.description}</p>
                  )}
                  <div className="flex gap-4 mt-2 text-xs text-gray-400">
                    {episode.release_date && (
                      <span>{new Date(episode.release_date).getFullYear()}</span>
                    )}
                    {episode.duration_minutes !== null && (
                      <span>{Math.round(episode.duration_minutes)} Min.</span>
                    )}
                  </div>
                </div>
                {episode.cover_url && (
                  // The source covers are remote and come from multiple legacy hosts.
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={episode.cover_url}
                    alt={episode.title ?? ''}
                    className="w-16 h-16 shrink-0 object-cover rounded"
                  />
                )}
              </article>
            </Link>
          ))}
        </div>
      )}
    </main>
  )
}

function CategoryLink({
  href,
  label,
  count,
  active,
}: {
  href: string
  label: string
  count: number
  active: boolean
}) {
  return (
    <Link
      href={href}
      aria-current={active ? 'page' : undefined}
      className={`shrink-0 rounded-full border px-3 py-1.5 text-sm transition-colors ${
        active
          ? 'border-blue-600 bg-blue-600 text-white'
          : 'border-gray-200 text-gray-600 hover:border-gray-400'
      }`}
    >
      {label} <span className={active ? 'text-blue-100' : 'text-gray-400'}>{count}</span>
    </Link>
  )
}
