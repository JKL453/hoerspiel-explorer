import { NextRequest, NextResponse } from 'next/server'

export function proxy(request: NextRequest) {
  const mode = process.env.NEXT_PUBLIC_CATALOG_MODE ?? 'maintenance'
  if (mode !== 'legacy' && request.nextUrl.pathname !== '/') {
    return NextResponse.redirect(new URL('/', request.url))
  }
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|api).*)'],
}
