export class WorkspaceChunkLoadError extends Error {
  constructor(cause: unknown) {
    super("A workspace module failed to load.", { cause });
    this.name = "WorkspaceChunkLoadError";
  }
}

function isWorkspaceChunkFetchFailure(cause: unknown): boolean {
  if (!(cause instanceof TypeError)) return false;
  return /(?:failed to fetch dynamically imported module|error loading dynamically imported module|importing a module script failed|failed to load module script|module script.*(?:mime|content type))/i.test(
    cause.message,
  );
}

export async function loadWorkspaceChunk<T>(
  loader: () => Promise<T>,
): Promise<T> {
  try {
    return await loader();
  } catch (cause) {
    if (!isWorkspaceChunkFetchFailure(cause)) throw cause;
    throw new WorkspaceChunkLoadError(cause);
  }
}
