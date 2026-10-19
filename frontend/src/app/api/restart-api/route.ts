import { NextResponse } from 'next/server'

const RESTART_API_URL = process.env.RESTART_API_URL || 'http://restart-api:9999'

export async function POST() {
  try {
    const res = await fetch(RESTART_API_URL, { method: 'POST' })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (err) {
    return NextResponse.json(
      { status: 'error', message: 'Tidak dapat terhubung ke restart service.' },
      { status: 500 }
    )
  }
}