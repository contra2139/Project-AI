import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import axios from 'axios';

export async function GET() {
  const cookieStore = cookies();
  const token = cookieStore.get('access_token')?.value;

  if (!token) {
    return NextResponse.json({ authenticated: false }, { status: 401 });
  }

  try {
    // Optionally call backend to verify token and get user info
    // For now, we assume if token exists, it's valid (middleware already checked)
    // Or we decode it here.
    return NextResponse.json({ 
      authenticated: true, 
      user: { username: 'admin' } // Placeholder or decode from JWT
    });
  } catch (error) {
    return NextResponse.json({ authenticated: false }, { status: 401 });
  }
}
