import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8888'

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const { id } = params

  try {
    const url = `${API_URL}/thumbnail/${id}`

    const response = await fetch(url)

    if (!response.ok) {
      return new NextResponse(null, { status: response.status })
    }

    const data = await response.arrayBuffer()

    return new NextResponse(data, {
      status: 200,
      headers: {
        'Content-Type': 'image/png',
        'Content-Length': String(data.byteLength),
        'Cache-Control': 'public, max-age=86400',
      },
    })
  } catch (error) {
    console.error('Thumbnail proxy error:', error)
    return new NextResponse(null, { status: 500 })
  }
}
