export type WebPushConfiguration =
  | { kind: "disabled" }
  | { kind: "invalid" }
  | { kind: "enabled"; applicationServerKey: Uint8Array<ArrayBuffer> };

const P256_UNCOMPRESSED_BYTES = 65;
const UNCOMPRESSED_POINT_PREFIX = 4;
const BASE64_QUANTUM = 4;

export function webPushConfiguration(
  value = process.env.NEXT_PUBLIC_WEB_PUSH_APPLICATION_SERVER_KEY,
): WebPushConfiguration {
  if (value === undefined || value.trim() === "") return { kind: "disabled" };
  const decoded = decodeUrlSafeBase64(value);
  if (
    !decoded ||
    decoded.byteLength !== P256_UNCOMPRESSED_BYTES ||
    decoded[0] !== UNCOMPRESSED_POINT_PREFIX
  )
    return { kind: "invalid" };
  return { kind: "enabled", applicationServerKey: decoded };
}

function decodeUrlSafeBase64(value: string): Uint8Array<ArrayBuffer> | undefined {
  if (!/^[A-Za-z0-9_-]+$/.test(value)) return undefined;
  try {
    const normalized = value.replaceAll("-", "+").replaceAll("_", "/");
    const padded = normalized.padEnd(
      Math.ceil(normalized.length / BASE64_QUANTUM) * BASE64_QUANTUM,
      "=",
    );
    const binary = atob(padded);
    const buffer = new ArrayBuffer(binary.length);
    const bytes = new Uint8Array(buffer);
    for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    return bytes;
  } catch {
    return undefined;
  }
}
