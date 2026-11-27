// Invalidate incident views; data always comes from FastAPI.
const listeners = new Set<(id: number) => void>();
export function subscribeIncidentUpdates(listener: (id: number) => void) {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}
export function notifyIncidentUpdate<T>(id: number, result: T): T {
  for (const listener of listeners) listener(id);
  return result;
}
