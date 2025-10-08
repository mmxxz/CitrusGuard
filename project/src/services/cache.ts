// 轻量内存缓存（TTL + 并发去重）
import { getOrchardHealth, getOrchardAlerts } from './apiClient';

type Fetcher<T> = () => Promise<T>;

interface CacheEntry<T> {
  value: T;
  expiresAt: number;
}

const cacheStore = new Map<string, CacheEntry<any>>();
const inflightStore = new Map<string, Promise<any>>();

export async function cacheFetch<T>(key: string, fetcher: Fetcher<T>, ttlMs: number): Promise<T> {
  const now = Date.now();
  const cached = cacheStore.get(key);
  if (cached && cached.expiresAt > now) {
    return cached.value;
  }

  const inflight = inflightStore.get(key);
  if (inflight) {
    return inflight as Promise<T>;
  }

  const promise = (async () => {
    try {
      const value = await fetcher();
      cacheStore.set(key, { value, expiresAt: now + ttlMs });
      return value;
    } finally {
      inflightStore.delete(key);
    }
  })();

  inflightStore.set(key, promise);
  return promise;
}

export function invalidate(prefix?: string) {
  if (!prefix) {
    cacheStore.clear();
    return;
  }
  for (const k of cacheStore.keys()) {
    if (k.startsWith(prefix)) cacheStore.delete(k);
  }
}

// 具体业务缓存封装（默认 2 分钟 TTL）
const DEFAULT_TTL = 2 * 60 * 1000;

export function getCachedOrchardHealth(orchardId: string, ttlMs: number = DEFAULT_TTL) {
  return cacheFetch(`health:${orchardId}`, () => getOrchardHealth(orchardId), ttlMs);
}

export function getCachedOrchardAlerts(orchardId: string, ttlMs: number = DEFAULT_TTL) {
  return cacheFetch(`alerts:${orchardId}`, () => getOrchardAlerts(orchardId), ttlMs);
}


