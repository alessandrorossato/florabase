import { useState } from "react";

/** Browser-local pagination of an already loaded, filtered directory. */
export function useDirectoryPagination<T>(records: T[], scope: string) {
  const [state, setState] = useState({ scope, page: 0, size: "20" });
  const current = state.scope === scope ? state : { ...state, scope, page: 0 };
  if (state.scope !== scope) setState(current);
  const size =
    current.size === "all" ? Math.max(1, records.length) : Number(current.size);
  const pages = Math.max(1, Math.ceil(records.length / size));
  const page = Math.min(current.page, pages - 1);
  return {
    visible: records.slice(page * size, (page + 1) * size),
    page,
    pages,
    size: current.size,
    from: records.length ? page * size + 1 : 0,
    to: Math.min((page + 1) * size, records.length),
    setPage: (value: number) => {
      setState({ ...current, page: Math.max(0, Math.min(value, pages - 1)) });
    },
    setSize: (value: string) => {
      setState({ ...current, size: value, page: 0 });
    },
  };
}
