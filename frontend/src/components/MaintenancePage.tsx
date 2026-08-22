const milestones = [
  {
    title: 'Offizielle Katalog-APIs',
    text: 'Apple/iTunes, DNB und MusicBrainz werden auf Abdeckung, Nutzungsbedingungen und Datenqualität geprüft.',
  },
  {
    title: 'Kanonische Folgen',
    text: 'Folgen, Neuauflagen, Vinyl-Ausgaben und Boxen werden künftig als getrennte Ebenen modelliert.',
  },
  {
    title: 'Nachvollziehbare Quellen',
    text: 'Öffentliche Felder sollen ihre Herkunft und Nutzungsgrundlage transparent ausweisen.',
  },
]

export default function MaintenancePage() {
  return (
    <main className="min-h-screen bg-slate-950 px-5 py-12 text-slate-100 sm:py-20">
      <div className="mx-auto max-w-5xl">
        <div className="mb-14 inline-flex items-center gap-2 rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-sm text-cyan-200">
          <span className="h-2 w-2 rounded-full bg-cyan-300" />
          Datenbasis wird überarbeitet
        </div>

        <section className="max-w-3xl">
          <p className="mb-4 font-mono text-sm uppercase tracking-[0.22em] text-cyan-300">
            Hörspiel Explorer
          </p>
          <h1 className="text-4xl font-semibold leading-tight tracking-tight sm:text-6xl">
            Aus einem Scraping-Prototyp wird eine nachvollziehbare Discovery-Plattform.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
            Der öffentliche Katalog macht vorübergehend Pause. Im Hintergrund entsteht eine neue,
            quellenbasierte Datenarchitektur mit offiziellen APIs, Entity Resolution, dbt-Qualitätstests
            und klarer Trennung zwischen Geschichte, Produktion und Veröffentlichung.
          </p>
        </section>

        <section className="mt-14 grid gap-4 md:grid-cols-3">
          {milestones.map((milestone, index) => (
            <article key={milestone.title} className="rounded-2xl border border-white/10 bg-white/[0.04] p-6">
              <p className="font-mono text-xs text-cyan-300">0{index + 1}</p>
              <h2 className="mt-4 text-lg font-semibold">{milestone.title}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-400">{milestone.text}</p>
            </article>
          ))}
        </section>

        <section className="mt-12 rounded-2xl border border-white/10 bg-gradient-to-br from-indigo-500/10 to-cyan-400/5 p-7 sm:p-9">
          <h2 className="text-xl font-semibold">Was weiterhin gezeigt werden kann</h2>
          <p className="mt-3 max-w-3xl leading-7 text-slate-300">
            Das Projekt bleibt ein Portfolio für Python, Prefect, PostgreSQL/Supabase, dbt, Next.js
            und Datenmodellierung. Die aktuelle Überarbeitung ergänzt zwei besonders relevante Themen:
            Data Provenance und die zuverlässige Zusammenführung heterogener Medienkataloge.
          </p>
        </section>

        <footer className="mt-14 border-t border-white/10 pt-6 text-sm text-slate-500">
          Der Katalog kehrt als gekennzeichnete Beta zurück, sobald Abdeckung und Quellen geprüft sind.
        </footer>
      </div>
    </main>
  )
}
