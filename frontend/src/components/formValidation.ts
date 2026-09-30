export function firstValidationField(error: {
  body?: unknown;
}): string | undefined {
  const body = error.body as {
    detail?: { loc?: (string | number)[] }[];
  } | null;
  if (!Array.isArray(body?.detail)) return undefined;
  const fields = body.detail[0]?.loc
    ?.slice(1)
    .filter((part): part is string => typeof part === "string");
  return fields?.length ? fields.join("_") : undefined;
}
