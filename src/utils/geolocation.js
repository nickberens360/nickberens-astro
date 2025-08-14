// EEA countries (EU + Iceland, Liechtenstein, Norway)
const EEA_COUNTRIES = [
  'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 
  'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE', 'IS', 'LI', 'NO'
];

class GeolocationService {
  constructor() {
    this.cache = new Map();
    this.cacheExpiry = 24 * 60 * 60 * 1000; // 24 hours
  }

  async getUserLocation() {
    // Check localStorage cache first
    const cached = this.getCachedLocation();
    if (cached) {
      return cached;
    }

    try {
      // Try multiple geolocation services for reliability
      const location = await this.detectLocationWithFallback();
      this.cacheLocation(location);
      return location;
    } catch (error) {
      console.warn('Geolocation detection failed:', error);
      // Default to requiring consent if we can't determine location
      return { countryCode: 'UNKNOWN', isEEA: true, source: 'fallback' };
    }
  }

  async detectLocationWithFallback() {
    const services = [
      () => this.detectViaIpApi(),
      () => this.detectViaCloudflare(),
      () => this.detectViaTimezone()
    ];

    for (const service of services) {
      try {
        const result = await service();
        if (result && result.countryCode) {
          return result;
        }
      } catch (error) {
        console.warn('Geolocation service failed, trying next:', error);
        continue;
      }
    }

    throw new Error('All geolocation services failed');
  }

  async detectViaIpApi() {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);

    try {
      const response = await fetch('https://ipapi.co/json/', {
        signal: controller.signal,
        headers: {
          'Accept': 'application/json'
        }
      });
      clearTimeout(timeout);

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const data = await response.json();
      if (data.error) throw new Error(data.reason || 'API error');

      return {
        countryCode: data.country_code,
        country: data.country_name,
        isEEA: EEA_COUNTRIES.includes(data.country_code),
        source: 'ipapi.co'
      };
    } catch (error) {
      clearTimeout(timeout);
      throw error;
    }
  }

  async detectViaCloudflare() {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);

    try {
      const response = await fetch('https://cloudflare.com/cdn-cgi/trace', {
        signal: controller.signal
      });
      clearTimeout(timeout);

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const text = await response.text();
      const lines = text.split('\n');
      const locLine = lines.find(line => line.startsWith('loc='));
      
      if (!locLine) throw new Error('No location data');
      
      const countryCode = locLine.split('=')[1];
      
      return {
        countryCode: countryCode,
        isEEA: EEA_COUNTRIES.includes(countryCode),
        source: 'cloudflare'
      };
    } catch (error) {
      clearTimeout(timeout);
      throw error;
    }
  }

  async detectViaTimezone() {
    // Fallback: rough estimation based on timezone
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    
    // Common European timezones that might indicate EEA location
    const europeanTimezones = [
      'Europe/', 'Atlantic/Reykjavik', 'Atlantic/Faroe'
    ];
    
    const isLikelyEurope = europeanTimezones.some(tz => timezone.startsWith(tz));
    
    return {
      countryCode: 'ESTIMATED',
      timezone: timezone,
      isEEA: isLikelyEurope,
      source: 'timezone-estimation'
    };
  }

  getCachedLocation() {
    try {
      const cached = localStorage.getItem('user-location');
      if (!cached) return null;

      const { data, timestamp } = JSON.parse(cached);
      
      // Check if cache is expired
      if (Date.now() - timestamp > this.cacheExpiry) {
        localStorage.removeItem('user-location');
        return null;
      }

      return data;
    } catch (error) {
      console.warn('Error reading location cache:', error);
      return null;
    }
  }

  cacheLocation(location) {
    try {
      const cacheData = {
        data: location,
        timestamp: Date.now()
      };
      localStorage.setItem('user-location', JSON.stringify(cacheData));
    } catch (error) {
      console.warn('Error caching location:', error);
    }
  }

  isEEACountry(countryCode) {
    return EEA_COUNTRIES.includes(countryCode);
  }

  // Clear cache (useful for testing)
  clearCache() {
    localStorage.removeItem('user-location');
    this.cache.clear();
  }
}

// Export singleton instance
export const geolocationService = new GeolocationService();

// Export helper functions
export const isEEACountry = (countryCode) => EEA_COUNTRIES.includes(countryCode);
export const EEA_COUNTRY_LIST = EEA_COUNTRIES;