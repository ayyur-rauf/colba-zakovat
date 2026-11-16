// API javoblari keshi: sahifalar orasida o'tganda oxirgi ma'lumot darhol ko'rsatiladi,
// yangisi fonda olinadi (stale-while-revalidate). Chiqish va kirishda tozalanadi.
export const apiCache = new Map<string, unknown>();
export const clearApiCache = () => apiCache.clear();
