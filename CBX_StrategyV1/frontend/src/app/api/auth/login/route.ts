import { NextResponse } from 'next/server';
import axios from 'axios';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

    const response = await axios.post(`${backendUrl}/auth/login`, body);
    const { access_token } = response.data.data;
    const user = response.data.data.user || { id: 'admin', username: 'admin', role: 'admin' };

    const res = NextResponse.json({ success: true, user });

    // Set HTTP-only cookie for API
    res.cookies.set({
      name: 'access_token',
      value: access_token,
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 3600, // 1 hour
      path: '/',
    });

    // Set non-HTTP-only cookie for WebSocket
    res.cookies.set({
      name: 'ws_token',
      value: access_token, // reuse same token
      httpOnly: false,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 3600,
      path: '/',
    });

    return res;
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Login failed';
    return NextResponse.json({ success: false, message }, { status });
  }
}
