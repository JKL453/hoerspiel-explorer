import { NextRequest, NextResponse } from 'next/server'
import OpenAI from 'openai'
import { createClient } from '@supabase/supabase-js'

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

async function searchEpisodes(supabase: any, embedding: number[], matchCount = 10) {
  const { data, error } = await supabase.rpc('match_episodes', {
    query_embedding: embedding,
    match_count: matchCount,
    filter_genre: null,
  })
  if (error) throw error
  return data
}

function buildPrompt(query: string, episodes: any[]): string {
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

  return `Du bist ein Hörspiel-Experte und hilfst dabei, passende Hörspiele zu entdecken.
Dir werden Hörspiele aus einer Datenbank bereitgestellt die semantisch zur Anfrage passen.
Empfiehl die passendsten davon und erkläre kurz warum sie zur Anfrage passen.
Antworte auf Deutsch, freundlich und enthusiastisch.
Wenn keines der Hörspiele wirklich passt, sag das ehrlich.

Anfrage: ${query}

Gefundene Hörspiele:
${context}

Empfehlung:`
}

export async function POST(req: NextRequest) {
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
  } catch (error: any) {
    console.error('Chat error:', error)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}