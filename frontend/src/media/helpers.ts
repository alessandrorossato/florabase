import { ApiError } from "../auth/api";

export function mediaError(error: unknown): string {
  if (error instanceof ApiError) {
    const body = error.body as { detail?: { message?: string } } | undefined;
    if (typeof body?.detail?.message === "string") return body.detail.message;
    if (error.status === 422)
      return "Check the media details, image format and required HTTPS URLs.";
    if (error.status === 403)
      return "This change is not permitted. Refresh and try again.";
  }
  return "Florabase could not complete this media change. Refresh and try again.";
}

export function formText(form: FormData, key: string): string {
  const value = form.get(key);
  return typeof value === "string" ? value.trim() : "";
}
