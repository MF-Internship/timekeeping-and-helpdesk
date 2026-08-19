import { apiClient } from "@/shared/api/client";
import type { components } from "@/shared/api/schema";
import { parseApiResultFailure } from "@/shared/errors/api-error";

export type JobHealth = components["schemas"]["JobHealth"];

export async function getJobHealth(): Promise<JobHealth> {
  const result = await apiClient.GET("/api/v1/operations/job-health");
  if (result.data === undefined) throw await parseApiResultFailure(result);
  return result.data;
}
