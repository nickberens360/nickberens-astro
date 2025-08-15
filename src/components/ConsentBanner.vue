<template>
  <!-- Loading indicator while checking location -->
  <div 
    v-if="isCheckingLocation"
    class="consent-banner loading"
    role="banner"
    aria-label="Checking location for privacy compliance"
  >
    <div class="consent-content">
      <div class="consent-text">
        <h3>🌍 Checking your location...</h3>
        <p>Determining privacy requirements based on your location.</p>
      </div>
    </div>
  </div>

  <!-- Consent banner for EEA users -->
  <div
    v-if="showBanner && !isCheckingLocation"
    class="consent-banner"
    role="banner"
    aria-label="Cookie consent banner"
  >
    <div class="consent-content">
      <div class="consent-text">
        <h3>I ❤️ you and value your privacy</h3>
        <p>
          This website uses Google Analytics to understand how visitors
          interact with my site.
          I only collect anonymous usage data to improve your experience.
        </p>
        <small v-if="locationData" class="location-info">
          📍 Location: {{ locationData.country || locationData.countryCode }}
          ({{ locationData.source }})
        </small>
      </div>
      <div class="consent-actions">
        <button
          @click="acceptCookies"
          class="btn btn-accept"
          aria-label="Accept cookies and enable analytics"
        >
          Accept Analytics
        </button>
        <button
          @click="declineCookies"
          class="btn btn-decline"
          aria-label="Decline cookies and disable analytics"
        >
          Decline
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { geolocationService } from '../utils/geolocation.js'

// Constants for localStorage keys and consent statuses
const CONSENT_KEY = 'analytics-consent'
const CONSENT_STATUS = {
  ACCEPTED: 'accepted',
  DECLINED: 'declined',
  AUTO_ACCEPTED: 'auto-accepted'
}

export default {
  name: 'ConsentBanner',
  data() {
    return {
      showBanner: false,
      isCheckingLocation: true,
      locationData: null
    }
  },
  async mounted() {
    await this.checkLocationAndConsent()
  },
  methods: {
    async checkLocationAndConsent() {
      try {
        this.locationData = await geolocationService.getUserLocation()
        if (this.locationData.isEEA) {
          this.handleExistingConsent()
        } else {
          // Non-EEA user - automatically load GA unless they've previously declined
          const consent = localStorage.getItem(CONSENT_KEY)
          if (consent !== CONSENT_STATUS.DECLINED) {
            this.loadGoogleAnalytics()
            if (!consent) {
              localStorage.setItem(CONSENT_KEY, CONSENT_STATUS.AUTO_ACCEPTED)
            }
          }
        }
      } catch (error) {
        console.warn('Location detection failed, using fallback to require consent:', error)
        this.handleExistingConsent()
      } finally {
        this.isCheckingLocation = false
      }
    },
    handleExistingConsent() {
      const consent = localStorage.getItem(CONSENT_KEY)
      if (consent === CONSENT_STATUS.ACCEPTED) {
        this.loadGoogleAnalytics()
      } else if (consent !== CONSENT_STATUS.DECLINED) {
        this.showBanner = true
      }
    },
    acceptCookies() {
      localStorage.setItem(CONSENT_KEY, CONSENT_STATUS.ACCEPTED)
      this.showBanner = false
      this.loadGoogleAnalytics()
    },
    declineCookies() {
      localStorage.setItem(CONSENT_KEY, CONSENT_STATUS.DECLINED)
      this.showBanner = false
    },
    loadGoogleAnalytics() {
      const gaTrackingId = import.meta.env.PUBLIC_GA_TRACKING_ID
      if (!gaTrackingId) return

      // Check if GA is already loaded or script tag exists
      const gaScriptSrc = `https://www.googletagmanager.com/gtag/js?id=${gaTrackingId}`
      if (window.gtag || document.querySelector(`script[src="${gaScriptSrc}"]`)) return

      // Load Google Analytics script
      const script = document.createElement('script')
      script.async = true
      script.src = gaScriptSrc
      document.head.appendChild(script)

      // Initialize GA when script loads
      script.onload = () => {
        window.dataLayer = window.dataLayer || []
        window.gtag = function() {
          window.dataLayer.push(arguments)
        }
        window.gtag('js', new Date())
        window.gtag('config', gaTrackingId)
      }
    }
  }
}
</script>

<style scoped>
.consent-banner {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.95);
  backdrop-filter: blur(10px);
  color: white;
  padding: 1rem;
  z-index: 9999;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
}

.consent-banner.loading {
  background: rgba(0, 100, 200, 0.9);
}

.location-info {
  display: block;
  margin-top: 0.5rem;
  opacity: 0.7;
  font-size: 0.8rem;
}

.consent-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.consent-text h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.consent-text p {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.4;
  opacity: 0.9;
}

.consent-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s ease;
  font-weight: 500;
}

.btn-accept {
  background: #4CAF50;
  color: white;
}

.btn-accept:hover {
  background: #45a049;
  transform: translateY(-1px);
}

.btn-decline {
  background: transparent;
  color: #ccc;
  border: 1px solid #666;
}

.btn-decline:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
  border-color: #999;
}

@media (min-width: 768px) {
  .consent-content {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }

  .consent-actions {
    flex-shrink: 0;
  }
}
</style>