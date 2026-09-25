/**
 * Lightweight Client-Side In-Memory SWR (Stale-While-Revalidate) Cache
 * Accelerates page transitions to 0ms by rendering cached data immediately
 * while revalidating fresh data in the background.
 */

interface CacheEntry<T> {
  data: T
  timestamp: number
  ttlMs: number
}

class ApiCache {
  private cache = new Map<string, CacheEntry<unknown>>()
  private inFlight = new Map<string, Promise<unknown>>()

  /**
   * Get cached data if available.
   * Returns { data, isStale } or null if not cached at all.
   */
  get<T>(key: string): { data: T; isStale: boolean } | null {
    const entry = this.cache.get(key) as CacheEntry<T> | undefined
    if (!entry) return null

    const now = Date.now()
    const isStale = now - entry.timestamp > entry.ttlMs
    return { data: entry.data, isStale }
  }

  /**
   * Store data in cache with TTL.
   */
  set<T>(key: string, data: T, ttlMs: number = 60000): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttlMs,
    })
  }

  /**
   * Stale-While-Revalidate fetcher:
   * 1. Returns cached data immediately if available.
   * 2. In deduplicated background task, executes fetcher, updates cache, and invokes onRevalidate.
   */
  async swr<T>(
    key: string,
    fetcher: () => Promise<T>,
    options?: {
      ttlMs?: number
      onRevalidate?: (freshData: T) => void
      forceFresh?: boolean
    }
  ): Promise<{ data: T; isFromCache: boolean }> {
    const ttl = options?.ttlMs ?? 60000
    const cached = this.get<T>(key)

    // Background revalidation runner (deduplicated)
    const runRevalidation = async (): Promise<T> => {
      if (this.inFlight.has(key)) {
        return this.inFlight.get(key) as Promise<T>
      }

      const promise = fetcher()
        .then((fresh) => {
          this.set(key, fresh, ttl)
          if (options?.onRevalidate) {
            options.onRevalidate(fresh)
          }
          return fresh
        })
        .finally(() => {
          this.inFlight.delete(key)
        })

      this.inFlight.set(key, promise as Promise<unknown>)
      return promise
    }

    if (cached && !options?.forceFresh) {
      if (cached.isStale) {
        // Run background revalidation silently
        runRevalidation().catch(() => {})
      }
      return { data: cached.data, isFromCache: true }
    }

    // No cache or forceFresh: must await fresh
    const fresh = await runRevalidation()
    return { data: fresh, isFromCache: false }
  }

  /**
   * Invalidate all keys matching a prefix or substring (e.g. "databases", "users", "roles")
   */
  invalidate(pattern: string): void {
    for (const key of this.cache.keys()) {
      if (key.includes(pattern)) {
        this.cache.delete(key)
      }
    }
  }

  /**
   * Clear all cache
   */
  clear(): void {
    this.cache.clear()
    this.inFlight.clear()
  }
}

export const apiCache = new ApiCache()
