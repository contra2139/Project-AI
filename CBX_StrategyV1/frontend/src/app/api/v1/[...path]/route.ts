import { NextRequest, NextResponse } from 'next/server';
import axios from 'axios';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

async function handler(req: NextRequest, { params }: { params: { path: string[] } }) {
  const path = params.path.join('/');
  const url = `${BACKEND_URL}/api/v1/${path}${req.nextUrl.search}`;
  
  const headers: Record<string, string> = {};
  const authHeader = req.headers.get('authorization');
  if (authHeader) {
    headers['authorization'] = authHeader;
  }

  // Also forward cookies if any (for session handling if needed)
  const cookieHeader = req.headers.get('cookie');
  if (cookieHeader) {
    headers['cookie'] = cookieHeader;
  }

  try {
    const body = ['POST', 'PUT', 'PATCH'].includes(req.method) 
      ? await req.json().catch(() => null) 
      : undefined;

    const response = await axios({
      method: req.method,
      url,
      data: body,
      headers,
      validateStatus: () => true, // Don't throw on error status codes
    });

    return NextResponse.json(response.data, { status: response.status });
  } catch (error: any) {
    console.error(`Proxy error for ${path}:`, error.message);
    return NextResponse.json(
      { success: false, message: 'Proxy error', error: error.message },
      { status: 502 }
    );
  }
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
