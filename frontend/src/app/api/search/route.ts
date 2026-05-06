import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8888'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const q = searchParams.get('q') || ''
  const limit = searchParams.get('limit') || '20'
  const offset = searchParams.get('offset') || '0'
  const year = searchParams.get('year')
  const table = searchParams.get('table')

  try {
    const params = new URLSearchParams({ q, limit, offset })
    if (year) params.set('year', year)
    if (table) params.set('table', table)

    const response = await fetch(`${API_URL}/search?${params}`, {
      next: { revalidate: 0 },
    })

    if (!response.ok) {
      throw new Error(`API responded with ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Search proxy error:', error)
    return NextResponse.json(
      { error: 'Failed to search', details: String(error) },
      { status: 500 }
    )
  }
}
