export function scoreColor(verdict?: string, score?: number | null): string {
  if (verdict === "strong" || (score != null && score >= 71)) return "teal";
  if (verdict === "possible" || (score != null && score >= 41)) return "yellow";
  if (verdict === "error") return "gray";
  return "gray";
}
