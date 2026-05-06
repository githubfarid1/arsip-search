import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8888'

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const { id } = params
  const { searchParams } = new URL(request.url)
  const watermark = searchParams.get('watermark') === 'true'

  try {
    const url = watermark
      ? `${API_URL}/pdf/${id}?watermark=true`
      : `${API_URL}/pdf/${id}`

    const response = await fetch(url)

    if (!response.ok) {
      if (response.status === 404) {
        return new NextResponse('PDF not found', { status: 404 })
      }
      return new NextResponse('Failed to fetch PDF', { status: response.status })
    }

    const data = await response.arrayBuffer()

    return new NextResponse(data, {
      status: 200,
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'inline',
        'Content-Length': String(data.byteLength),
      },
    })
  } catch (error) {
    console.error('PDF proxy error:', error)
    return new NextResponse('Failed to fetch PDF', { status: 500 })
  }
}
