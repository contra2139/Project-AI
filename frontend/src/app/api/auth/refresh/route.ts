import { NextResponse } from 'next/server';
import axios from 'axios';
import { cookies } from 'next/headers';

export async function POST() {
  const cookieStore = cookies();
  const accessToken = cookieStore.get('access_token')?.value;

  if (!accessToken) {
    return NextResponse.json({ success: false, message: 'No token found' }, { status: 401 });
  }

  try {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

    const response = await axios.post(
      `${backendUrl}/auth/refresh`,
      {},
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      }
    );

    const { access_token } = response.data;
    const res = NextResponse.json({ success: true });

    // Update HTTP-only cookie
    res.cookies.set({
      name: 'access_token',
      value: access_token,
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 3600,
      path: '/',
    });

    return res;
  } catch (error: any) {
    const status = error.response?.status || 500;
    return NextResponse.json({ success: false, message: 'Refresh failed' }, { status });
  }
}
