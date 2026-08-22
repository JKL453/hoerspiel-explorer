import { NextRequest, NextResponse } from 'next/server'
import OpenAI from 'openai'
import { createClient, SupabaseClient } from '@supabase/supabase-js'

interface EpisodeMatch {
  id: number
  title: string | null
  series_name: string | null
  episode_number: number | null
  description: string | null
  cover_url: string | null
  release_date: string | null
  duration_minutes: number | null
  similarity: number
}

function getOpenAIClient() {
  return new OpenAI({ apiKey: process.env.OPENAI_API_KEY })
}

function getSupabaseClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}

async function embedQuery(openai: OpenAI, query: string): Promise<number[]> {
  const response = await openai.embeddings.create({
    input: query,
    model: 'text-embedding-3-small',
  })
  return response.data[0].embedding
}

async function searchEpisodes(
  supabase: SupabaseClient,
  embedding: number[],
  matchCount = 10
): Promise<EpisodeMatch[]> {
  const { data, error } = await supabase.rpc('match_episodes', {
    query_embedding: embedding,
    match_count: matchCount,
    filter_genre: null,
  })
  if (error) throw error
  return (data ?? []) as EpisodeMatch[]
}

function buildPrompt(query: string, episodes: EpisodeMatch[]): string {
  const context = episodes
    .map((ep) => {
      const parts = [`**${ep.title}**`]
      if (ep.series_name) parts.push(`Serie: ${ep.series_name}`)
      if (ep.episode_number) parts.push(`Folge ${ep.episode_number}`)
      if (ep.release_date) parts.push(`(${ep.release_date.slice(0, 4)})`)
      const header = parts.join(' | ')
      const desc = ep.description ? `\n${ep.description}` : ''
      return header + desc
    })
    .join('\n\n')

  return `Du bist ein sachkundiger Hörspiel-Kenner. Empfiehl passende Hörspiele auf Basis der Anfrage.

Halte dich kurz und präzise. Erkläre in 1-2 Sätzen pro Empfehlung warum sie zur Anfrage passt.
Formatiere die Empfehlungen als Markdown-Liste. Wenn keines der Hörspiele wirklich passt, sag das direkt.
Antworte auf Deutsch.

Anfrage: ${query}

Gefundene Hörspiele:
${context}

Empfehlungen:`
}

export async function POST(req: NextRequest) {
  if ((process.env.NEXT_PUBLIC_CATALOG_MODE ?? 'maintenance') !== 'legacy') {
    return NextResponse.json(
      { error: 'Die Empfehlungssuche ist während der Überarbeitung deaktiviert.' },
      { status: 503 }
    )
  }
  try {
    const { query } = await req.json()
    if (!query) {
      return NextResponse.json({ error: 'query erforderlich' }, { status: 400 })
    }

    const openai = getOpenAIClient()
    const supabase = getSupabaseClient()

    // 1. Embed query
    const embedding = await embedQuery(openai, query)

    // 2. Vector search
    const episodes = await searchEpisodes(supabase, embedding)

    // 3. Build prompt
    const prompt = buildPrompt(query, episodes)

    // 4. Generate response with Gemini
    const { GoogleGenAI } = await import('@google/genai')
    const genai = new GoogleGenAI({ apiKey: process.env.GOOGLE_API_KEY! })
    const response = await genai.models.generateContent({
      model: 'gemini-2.5-flash-lite',
      contents: prompt,
    })

    return NextResponse.json({
      response: response.text,
      episodes,
    })
  } catch (error: unknown) {
    console.error('Chat error:', error)
    const message = error instanceof Error ? error.message : 'Unbekannter Fehler'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
