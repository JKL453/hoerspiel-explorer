'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import Link from 'next/link'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from 'recharts'

export default function StatsPage() {
  const [episodesPerYear, setEpisodesPerYear] = useState<any[]>([])
  const [topGenres, setTopGenres] = useState<any[]>([])
  const [topLabels, setTopLabels] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
        const [yearsRes, genresRes, labelsRes] = await Promise.all([
        supabase.rpc('get_episodes_per_year'),
        supabase.rpc('get_top_genres', { limit_count: 10 }),
        supabase.rpc('get_top_labels', { limit_count: 10 }),
        ])

        if (!yearsRes.error) setEpisodesPerYear(
        yearsRes.data.map((d: any) => ({
            ...d,
            episode_count: Number(d.episode_count)
        }))
        )

        if (!genresRes.error) {
        const converted = genresRes.data.map((d: any) => ({
            ...d,
            episode_count: Number(d.episode_count)
        }))
        console.log('Genres data:', converted)
        setTopGenres(converted)
        }

        if (!labelsRes.error) setTopLabels(
        labelsRes.data.map((d: any) => ({
            ...d,
            series_count: Number(d.series_count)
        }))
        )

        setLoading(false)
    }
    load()
    }, [])

  if (loading) return <p className="p-10 text-gray-400">Lade Statistiken...</p>

    return (
        <main className="max-w-7xl mx-auto px-4 py-10">
            <Link href="/" className="text-sm text-blue-500 hover:underline mb-6 block">
            ← Zurück zur Übersicht
            </Link>

            <h1 className="text-3xl font-bold mb-8">Statistiken</h1>

            {/* Episoden pro Jahr — volle Breite */}
            <div className="mb-12">
            <h2 className="text-lg font-semibold mb-4">Episoden pro Jahr</h2>
            <BarChart width={900} height={300} data={episodesPerYear} margin={{ bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                dataKey="year"
                tick={{ fontSize: 11, angle: -45, textAnchor: 'end' }}
                interval={4}
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="episode_count" fill="#3b82f6" name="Episoden" radius={[3, 3, 0, 0]} />
            </BarChart>
            </div>

            {/* Genres + Verlage nebeneinander */}
            <div className="grid grid-cols-2 gap-8">
            <div>
                <h2 className="text-lg font-semibold mb-4">Top 10 Genres</h2>
                <BarChart width={500} height={350} data={topGenres} layout="vertical" margin={{ left: 10, right: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis dataKey="genre_name" type="category" tick={{ fontSize: 12 }} width={160} />
                <Tooltip />
                <Bar dataKey="episode_count" fill="#8b5cf6" name="Episoden" radius={[0, 3, 3, 0]} />
                </BarChart>
            </div>

            <div>
                <h2 className="text-lg font-semibold mb-4">Top 10 Verlage</h2>
                <BarChart width={500} height={350} data={topLabels} layout="vertical" margin={{ left: 10, right: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis dataKey="label_name" type="category" tick={{ fontSize: 12 }} width={150} />
                <Tooltip />
                <Bar dataKey="series_count" fill="#10b981" name="Serien" radius={[0, 3, 3, 0]} />
                </BarChart>
            </div>
            </div>
        </main>
        )
}