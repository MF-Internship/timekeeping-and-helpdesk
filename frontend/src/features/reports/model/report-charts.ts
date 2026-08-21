export type ReportChartDatum = { key: string; label: string; value: number };
const STATUS_LABELS: Record<string, string> = {
  TODO: "Cần làm",
  IN_PROGRESS: "Đang thực hiện",
  BLOCKED: "Đang vướng",
  COMPLETED: "Đã hoàn thành",
  FIELD_EVIDENCE: "Minh chứng hiện trường",
  MANAGER_OVERRIDE: "Quản lý xác nhận",
  GOOD: "GPS tốt",
  LOW: "GPS thấp",
  POOR: "GPS không đạt",
};
export function chartData(
  values: Record<string, number>,
  order?: readonly string[],
): ReportChartDatum[] {
  const keys = order ?? Object.keys(values);
  const known = keys.map((key) => ({
    key,
    label: STATUS_LABELS[key] ?? humanize(key),
    value: safeValue(values[key]),
  }));
  const extras = Object.keys(values)
    .filter((key) => !keys.includes(key))
    .map((key) => ({
      key,
      label: STATUS_LABELS[key] ?? humanize(key),
      value: safeValue(values[key]),
    }));
  return [...known, ...extras];
}
export const taskStatusData = (values: Record<string, number>) =>
  chartData(values, ["TODO", "IN_PROGRESS", "BLOCKED", "COMPLETED"]);
function safeValue(value: number | undefined) {
  return Number.isFinite(value) && Number(value) >= 0 ? Number(value) : 0;
}
function humanize(key: string) {
  return key
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/^./, (value) => value.toUpperCase());
}
