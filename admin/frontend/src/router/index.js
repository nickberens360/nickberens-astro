import { createRouter, createWebHistory } from 'vue-router'
import AdminLayout from '@/components/AdminLayout.vue'
import { useAdminStore } from '@/stores/admin'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: {
        title: 'Login',
        public: true
      }
    },
    {
      path: '/',
      component: AdminLayout,
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
          meta: {
            title: 'Dashboard',
            icon: 'dashboard'
          }
        },
        {
          path: 'queries',
          name: 'queries',
          component: () => import('@/views/QueriesView.vue'),
          meta: {
            title: 'Queries',
            icon: 'search'
          }
        },
        {
          path: 'performance',
          name: 'performance',
          component: () => import('@/views/PerformanceView.vue'),
          meta: {
            title: 'Performance',
            icon: 'chart'
          }
        },
        {
          path: 'sessions',
          name: 'sessions',
          component: () => import('@/views/SessionsView.vue'),
          meta: {
            title: 'Sessions',
            icon: 'users'
          }
        },
        {
          path: 'knowledge',
          name: 'knowledge',
          component: () => import('@/views/KnowledgeView.vue'),
          meta: {
            title: 'Knowledge Base',
            icon: '$knowledge'
          },
          children: [
            {
              path: '',
              name: 'knowledge-overview',
              redirect: 'sources'
            },
            {
              path: 'documents',
              name: 'knowledge-documents',
              component: () => import('@/views/knowledge/DocumentsView.vue'),
              meta: {
                title: 'Indexed Documents'
              }
            },
            {
              path: 'sources',
              name: 'knowledge-sources',
              component: () => import('@/views/knowledge/SourcesView.vue'),
              meta: {
                title: 'Knowledge Sources'
              }
            },
            {
              path: 'gaps',
              name: 'knowledge-gaps',
              component: () => import('@/views/knowledge/GapsView.vue'),
              meta: {
                title: 'Content Gaps'
              }
            },
            {
              path: 'stats',
              name: 'knowledge-stats',
              component: () => import('@/views/knowledge/StatsView.vue'),
              meta: {
                title: 'Knowledge Statistics'
              }
            }
          ]
        },
        {
          path: 'users',
          name: 'users',
          component: () => import('@/views/UsersView.vue'),
          meta: {
            title: 'User Management',
            icon: '$users'
          }
        },
        {
          path: 'change-password',
          name: 'change-password',
          component: () => import('@/views/ChangePassword.vue'),
          meta: {
            title: 'Change Password',
            icon: 'lock'
          }
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/views/SettingsView.vue'),
          meta: {
            title: 'Settings',
            icon: 'settings'
          },
          children: [
            {
              path: '',
              name: 'settings-overview',
              redirect: 'followup'
            },
            {
              path: 'followup',
              name: 'settings-followup',
              component: () => import('@/views/settings/FollowupSettings.vue'),
              meta: {
                title: 'Follow-up Questions'
              }
            },
            {
              path: 'welcome',
              name: 'settings-welcome',
              component: () => import('@/views/settings/WelcomeSettings.vue'),
              meta: {
                title: 'Welcome Questions'
              }
            },
            {
              path: 'response',
              name: 'settings-response',
              component: () => import('@/views/settings/ResponseSettings.vue'),
              meta: {
                title: 'Response Settings'
              }
            },
            {
              path: 'routing',
              name: 'settings-routing',
              component: () => import('@/views/settings/RoutingSettings.vue'),
              meta: {
                title: 'Query Routing'
              }
            },
            {
              path: 'features',
              name: 'settings-features',
              component: () => import('@/views/settings/FeatureSettings.vue'),
              meta: {
                title: 'Feature Flags'
              }
            },
            {
              path: 'api-keys',
              name: 'settings-api-keys',
              component: () => import('@/views/settings/ApiKeysSettings.vue'),
              meta: {
                title: 'API Keys'
              }
            },
            {
              path: 'system',
              name: 'settings-system',
              component: () => import('@/views/settings/SystemSettings.vue'),
              meta: {
                title: 'System Config'
              }
            },
            {
              path: 'security',
              name: 'settings-security',
              component: () => import('@/views/settings/SecuritySettings.vue'),
              meta: {
                title: 'Security & Privacy'
              }
            }
          ]
        },
        // Development-only routes
        ...(import.meta.env.DEV ? [{
          path: 'typography-demo',
          name: 'typography-demo',
          component: () => import('@/components/TypographyDemo.vue'),
          meta: {
            title: 'Typography Demo',
            icon: 'article',
            hidden: true // Hide from main navigation
          }
        }, {
          path: 'accordion-test',
          name: 'accordion-test',
          component: () => import('@/components/FollowupAccordion.vue'),
          meta: {
            title: 'Accordion Test',
            icon: 'list',
            hidden: true
          }
        }] : [])
      ]
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ]
})

// Navigation guards
router.beforeEach(async (to, from, next) => {
  // Update document title
  document.title = to.meta.title ? `${to.meta.title} - RAG Admin` : 'RAG Admin Dashboard'

  const adminStore = useAdminStore()

  // Check if route requires authentication
  if (to.meta.requiresAuth) {
    // Only check auth if we haven't already verified it recently
    // This prevents unnecessary API calls on every navigation
    if (!adminStore.isAuthenticated) {
      try {
        await adminStore.checkAuth()
      } catch (error) {
        console.debug('Auth check failed, redirecting to login')
      }
    }

    if (!adminStore.isAuthenticated) {
      // Redirect to login with return path
      next({ name: 'login', query: { redirect: to.fullPath } })
      return
    }
  }

  // If going to login but already authenticated, redirect away
  if (to.name === 'login' && adminStore.isAuthenticated) {
    const raw = to.query.redirect
    // Prevent open redirect vulnerabilities by ensuring the redirect path:
    // 1. Is a string and starts with '/'
    // 2. Does not start with '//' (protocol-relative URLs)
    // 3. Contains only safe path characters
    const redirect =
      typeof raw === 'string' && 
      raw.startsWith('/') && 
      !raw.startsWith('//') &&
      !/[^a-zA-Z0-9\-._~:/?#[\]@!$&'()*+,;=]/.test(raw) 
        ? raw 
        : '/'
    next({ path: redirect })
    return
  }

  next()
})

export default router
