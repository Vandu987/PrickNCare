import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/login", "/register"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get("access_token")?.value;

  // Also check Authorization header isn't available in middleware,
  // so we rely on a cookie OR a lightweight "logged_in" flag cookie
  // set by the client after login for SSR redirect purposes.
  const loggedIn = token || request.cookies.get("logged_in")?.value === "1";

  const isPublic = PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + "/")
  );

  // Authenticated user hitting login/register → redirect to dashboard
  if (isPublic && loggedIn) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  // Unauthenticated user hitting protected route → redirect to login
  if (!isPublic && !loggedIn && pathname !== "/") {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all paths except static files and API routes.
     */
    "/((?!_next/static|_next/image|favicon.ico|api).*)",
  ],
};
