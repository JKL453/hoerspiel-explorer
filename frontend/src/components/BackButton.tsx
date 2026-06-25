'use client'

import { useRouter } from 'next/navigation'

export default function BackButton({ label }: { label: string }) {
  const router = useRouter()
  return (
    <button
      onClick={() => router.back()}
      className="text-sm text-blue-500 hover:underline mb-6 block"
    >
      {label}
    </button>
  )
}