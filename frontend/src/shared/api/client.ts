import createClient from "openapi-fetch";

import type { paths } from "@/shared/api/schema";
import { authenticatedFetch } from "@/shared/transport/authenticated-fetch";

export const apiClient = createClient<paths>({
  baseUrl: "",
  fetch: authenticatedFetch,
});
