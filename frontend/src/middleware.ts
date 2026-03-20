import { NextResponse, type NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token')?.value;
  const { pathname } = request.nextUrl;

  // 1. If no token and trying to access protected route -> redirect to login
  const protectedRoutes = ['/dashboard', '/signals', '/trades', '/symbols', '/backtest', '/settings'];
  const isProtectedRoute = protectedRoutes.some(route => pathname.startsWith(route));

  if (!token && isProtectedRoute) {
    const url = request.nextUrl.clone();
    url.pathname = '/login';
    return NextResponse.redirect(url);
  }

  // 2. If has token and trying to access login -> redirect to dashboard
  if (token && pathname === '/login') {
    const url = request.nextUrl.clone();
    url.pathname = '/dashboard';
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/signals/:path*',
    '/trades/:path*',
    '/symbols/:path*',
    '/backtest/:path*',
    '/settings/:path*',
    '/login'
  ]
};
