import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Loads one page from a Mobile Admin list endpoint.
 *
 * `fetcher(params)` must return `{ items, page, ... }`. Filters are passed in
 * from the caller; changing them resets the offset, so a filter change never
 * lands on a page number that no longer exists.
 *
 * A filter key prefixed with `_` takes part in the cache key but is NOT sent to
 * the API — it lets a page re-fetch when something the endpoint does not know
 * about changes (a tab, say).
 */
function requestParams(filters) {
  return Object.fromEntries(
    Object.entries(filters).filter(([key]) => !key.startsWith("_"))
  );
}

export default function useMobileList(fetcher, filters, { limit = 25 } = {}) {
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  const filterKey = JSON.stringify(filters ?? {});
  const previousFilterKey = useRef(filterKey);

  if (previousFilterKey.current !== filterKey) {
    previousFilterKey.current = filterKey;
    if (offset !== 0) setOffset(0);
  }

  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetcherRef
      .current({ ...requestParams(JSON.parse(filterKey)), limit, offset })
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) {
          setData(null);
          setError(err);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filterKey, limit, offset, reloadKey]);

  const reload = useCallback(() => setReloadKey((k) => k + 1), []);

  return {
    items: data?.items ?? [],
    page: data?.page ?? { total: 0, limit, offset },
    data,
    loading,
    error,
    offset,
    setOffset,
    reload,
  };
}
