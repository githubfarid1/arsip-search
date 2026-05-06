import { NextResponse } from 'next/server'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8888'

export async function POST() {
  try {
    const res = await fetch(`${API_BASE}/sync`, { method: 'POST' })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
      return NextResponse.json(err, { status: res.status })
    }
    const data = await res.json()
    return NextResponse.json(data)
  } catch (err) {
    return NextResponse.json({ detail: 'Failed to connect to backend' }, { status: 500 })
  }
}
