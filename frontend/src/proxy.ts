import { type NextRequest, NextResponse } from "next/server";

const MINIMUM_ORIGIN_CREDENTIAL_LENGTH = 32;

export function buildOriginHeaders(
  incoming: Headers,
  headerName: string,
  credential: string | undefined,
): Headers {
  const headers = new Headers(incoming);
  headers.delete(headerName);
  if (credential !== undefined) headers.set(headerName, credential);
  return headers;
}

export function proxy(request: NextRequest) {
  const headerName = process.env.ORIGIN_CREDENTIAL_HEADER ?? "X-Origin-Credential";
  const credential = process.env.ORIGIN_CREDENTIAL;
  if (credential === undefined || credential.length < MINIMUM_ORIGIN_CREDENTIAL_LENGTH) {
    throw new Error("Invalid ORIGIN_CREDENTIAL");
  }
  const requestHeaders = buildOriginHeaders(request.headers, headerName, credential);
  return NextResponse.next({ request: { headers: requestHeaders } });
}

export const config = {
  matcher: ["/api/v1/:path*"],
};
