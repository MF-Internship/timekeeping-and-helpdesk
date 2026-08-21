export function formatMinutes(value: string | number) {
  const minutes = Number(value);
  if (!Number.isFinite(minutes)) return String(value);
  return new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 1 }).format(minutes);
}
