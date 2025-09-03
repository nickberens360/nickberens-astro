import adminAPI from '@/services/api'

export class CacheSettingsService {
  async getCacheStatus() {
    return await adminAPI.getSettingsCacheStatus()
  }

  async invalidateCache() {
    return await adminAPI.invalidateSettingsCache()
  }
}

export const cacheSettingsService = new CacheSettingsService()