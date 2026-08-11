'use client'

import { FormEvent, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { supabase } from '@/lib/supabase'

type Kpis = {
  episode_count: number
  series_count: number
  label_count: number
  franchise_count: number
  episodes_without_year: number
  episodes_without_duration: number
}

type YearCount = { year: number; episode_count: number }
type GenreTrend = YearCount & { genre_name: string }
type LabelStat = { label_name: string; series_count: number; episode_count: number }
type SpeakerStat = { speaker_name: string; episode_count: number; role_count: number; credit_count: number }
type DurationStat = { duration_bucket: string; bucket_order: number; episode_count: number }
type FranchiseStat = { franchise_name: string; series_count: number; episode_count: number }
type Range = { start: number | null; end: number | null }

type DashboardData = {
  kpis: Kpis | null
  years: YearCount[]
  genres: GenreTrend[]
  labels: LabelStat[]
  speakers: SpeakerStat[]
  durations: DurationStat[]
  franchises: FranchiseStat[]
}

const EMPTY_DATA: DashboardData = {
  kpis: null,
  years: [],
  genres: [],
  labels: [],
  speakers: [],
  durations: [],
  franchises: [],
}

const COLORS = ['#8b5cf6', '#06b6d4', '#f59e0b', '#ec4899', '#10b981']
const integer = new Intl.NumberFormat('de-DE')

function rows<T>(value: unknown): T[] {
  return Array.isArray(value) ? value as T[] : []
}

function numeric<T extends Record<string, unknown>>(items: T[], keys: (keyof T)[]): T[] {
  return items.map((item) => {
    const converted = { ...item }
    for (const key of keys) converted[key] = Number(item[key]) as T[keyof T]
    return converted
  })
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="min-w-0 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-950 sm:p-6">
      <h2 className="mb-5 text-lg font-semibold">{title}</h2>
      <div className="h-80 w-full">{children}</div>
    </section>
  )
}

export default function StatsPage() {
  const [data, setData] = useState<DashboardData>(EMPTY_DATA)
  const [range, setRange] = useState<Range>({ start: null, end: null })
  const [draftStart, setDraftStart] = useState('')
  const [draftEnd, setDraftEnd] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    async function load() {
      setLoading(true)
      setError(null)
      const dateParams = { start_year: range.start, end_year: range.end }
      const rankingParams = { ...dateParams, limit_count: 10 }
      const [kpis, years, genres, labels, speakers, durations, franchises] = await Promise.all([
        supabase.rpc('get_analytics_kpis', dateParams),
        supabase.rpc('get_analytics_episodes_per_year', dateParams),
        supabase.rpc('get_analytics_genre_trends', { ...dateParams, limit_count: 5 }),
        supabase.rpc('get_analytics_top_labels', rankingParams),
        supabase.rpc('get_analytics_top_speakers', rankingParams),
        supabase.rpc('get_analytics_duration_distribution', dateParams),
        supabase.rpc('get_analytics_top_franchises', rankingParams),
      ])
      if (!active) return

      const firstError = [kpis, years, genres, labels, speakers, durations, franchises]
        .find((result) => result.error)?.error
      if (firstError) {
        setError(firstError.message)
        setData(EMPTY_DATA)
      } else {
        const kpiRows = numeric(rows<Record<string, unknown>>(kpis.data), [
          'episode_count', 'series_count', 'label_count', 'franchise_count',
          'episodes_without_year', 'episodes_without_duration',
        ])
        setData({
          kpis: (kpiRows[0] ?? null) as Kpis | null,
          years: numeric(rows<YearCount>(years.data), ['year', 'episode_count']),
          genres: numeric(rows<GenreTrend>(genres.data), ['year', 'episode_count']),
          labels: numeric(rows<LabelStat>(labels.data), ['series_count', 'episode_count']),
          speakers: numeric(rows<SpeakerStat>(speakers.data), ['episode_count', 'role_count', 'credit_count']),
          durations: numeric(rows<DurationStat>(durations.data), ['bucket_order', 'episode_count']),
          franchises: numeric(rows<FranchiseStat>(franchises.data), ['series_count', 'episode_count']),
        })
      }
      setLoading(false)
    }

    load()
    return () => { active = false }
  }, [range])

  const genreNames = useMemo(
    () => [...new Set(data.genres.map((item) => item.genre_name))],
    [data.genres],
  )
  const genreChart = useMemo(() => {
    const byYear = new Map<number, Record<string, number>>(
      data.years.map((item) => [
        item.year,
        Object.fromEntries([['year', item.year], ...genreNames.map((genre) => [genre, 0])]),
      ]),
    )
    for (const item of data.genres) {
      const current = byYear.get(item.year) ?? { year: item.year }
      current[item.genre_name] = item.episode_count
      byYear.set(item.year, current)
    }
    return [...byYear.values()].sort((a, b) => a.year - b.year)
  }, [data.genres, data.years, genreNames])

  function applyRange(event: FormEvent) {
    event.preventDefault()
    const start = draftStart ? Number(draftStart) : null
    const end = draftEnd ? Number(draftEnd) : null
    if (start !== null && end !== null && start > end) {
      setError('Das Startjahr darf nicht nach dem Endjahr liegen.')
      return
    }
    setRange({ start, end })
  }

  function resetRange() {
    setDraftStart('')
    setDraftEnd('')
    setRange({ start: null, end: null })
  }

  const kpiCards = data.kpis ? [
    ['Episoden', data.kpis.episode_count],
    ['Serien', data.kpis.series_count],
    ['Verlage', data.kpis.label_count],
    ['Franchises', data.kpis.franchise_count],
    ['Ohne Jahr', data.kpis.episodes_without_year],
    ['Ohne Laufzeit', data.kpis.episodes_without_duration],
  ] as const : []

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <Link href="/" className="mb-6 block text-sm text-blue-500 hover:underline">
        ← Zurück zur Übersicht
      </Link>

      <div className="mb-8 flex flex-col gap-2">
        <p className="text-sm font-medium uppercase tracking-wider text-violet-500">dbt Analytics Showcase</p>
        <h1 className="text-3xl font-bold sm:text-4xl">Hörspiel-Landschaft in Zahlen</h1>
        <p className="max-w-3xl text-gray-600 dark:text-gray-400">
          Getestete Analytics-Marts aus dem vollständigen Hörspiel-Datensatz.
          Der Zeitraumfilter wirkt auf alle Kennzahlen und Visualisierungen.
        </p>
      </div>

      <form onSubmit={applyRange} className="mb-8 flex flex-wrap items-end gap-3 rounded-2xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-800 dark:bg-gray-900">
        <label className="text-sm">
          <span className="mb-1 block text-gray-600 dark:text-gray-400">Von Jahr</span>
          <input type="number" value={draftStart} onChange={(event) => setDraftStart(event.target.value)} className="w-32 rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-700 dark:bg-gray-950" placeholder="Alle" />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-gray-600 dark:text-gray-400">Bis Jahr</span>
          <input type="number" value={draftEnd} onChange={(event) => setDraftEnd(event.target.value)} className="w-32 rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-700 dark:bg-gray-950" placeholder="Alle" />
        </label>
        <button type="submit" className="rounded-lg bg-violet-600 px-4 py-2 font-medium text-white hover:bg-violet-700">Anwenden</button>
        <button type="button" onClick={resetRange} className="rounded-lg border border-gray-300 px-4 py-2 font-medium hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800">Zurücksetzen</button>
        {(range.start !== null || range.end !== null) && (
          <span className="pb-2 text-sm text-gray-500">Aktiv: {range.start ?? 'Beginn'}–{range.end ?? 'heute'}</span>
        )}
      </form>

      {error && <div role="alert" className="mb-8 rounded-xl border border-red-300 bg-red-50 p-4 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">Analytics konnten nicht geladen werden: {error}</div>}
      {loading && <div className="py-20 text-center text-gray-500">Analytics werden geladen …</div>}

      {!loading && !error && !data.kpis && (
        <div className="rounded-xl border border-gray-200 p-8 text-center text-gray-500 dark:border-gray-800">Für diesen Zeitraum sind keine Daten vorhanden.</div>
      )}

      {!loading && !error && data.kpis && (
        <div className="space-y-8">
          <section className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
            {kpiCards.map(([label, value]) => (
              <div key={label} className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-950">
                <p className="text-sm text-gray-500">{label}</p>
                <p className="mt-1 text-2xl font-bold">{integer.format(value)}</p>
              </div>
            ))}
          </section>

          <div className="grid gap-8 xl:grid-cols-2">
            <ChartCard title="Episoden pro Jahr">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.years} margin={{ bottom: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#d1d5db" opacity={0.4} />
                  <XAxis dataKey="year" angle={-35} textAnchor="end" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value) => integer.format(Number(value))} />
                  <Bar dataKey="episode_count" fill="#3b82f6" name="Episoden" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Genre-Trends (Top 5)">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={genreChart} margin={{ bottom: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#d1d5db" opacity={0.4} />
                  <XAxis dataKey="year" angle={-35} textAnchor="end" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value) => integer.format(Number(value))} />
                  <Legend />
                  {genreNames.map((genre, index) => <Line key={genre} type="monotone" dataKey={genre} stroke={COLORS[index % COLORS.length]} connectNulls name={genre} dot={false} />)}
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Top 10 Verlage">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.labels} layout="vertical" margin={{ left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#d1d5db" opacity={0.4} />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis dataKey="label_name" type="category" width={125} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value) => integer.format(Number(value))} />
                  <Bar dataKey="episode_count" fill="#10b981" name="Episoden" radius={[0, 3, 3, 0]} />
                  <Bar dataKey="series_count" fill="#06b6d4" name="Serien" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Top 10 Sprecher:innen">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.speakers} layout="vertical" margin={{ left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#d1d5db" opacity={0.4} />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis dataKey="speaker_name" type="category" width={125} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value) => integer.format(Number(value))} />
                  <Bar dataKey="episode_count" fill="#f59e0b" name="Episoden" radius={[0, 3, 3, 0]} />
                  <Bar dataKey="role_count" fill="#ec4899" name="Rollen" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Laufzeitverteilung">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.durations}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#d1d5db" opacity={0.4} />
                  <XAxis dataKey="duration_bucket" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value) => integer.format(Number(value))} />
                  <Bar dataKey="episode_count" fill="#ec4899" name="Episoden" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Top 10 Franchises">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.franchises} layout="vertical" margin={{ left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#d1d5db" opacity={0.4} />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis dataKey="franchise_name" type="category" width={125} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value) => integer.format(Number(value))} />
                  <Bar dataKey="episode_count" fill="#8b5cf6" name="Episoden" radius={[0, 3, 3, 0]} />
                  <Bar dataKey="series_count" fill="#06b6d4" name="Serien" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </div>
      )}
    </main>
  )
}
