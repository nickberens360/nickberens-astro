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
              path: 'consistency',
              name: 'knowledge-consistency',
              component: () => import('@/views/knowledge/ConsistencyView.vue'),
              meta: {
                title: 'Consistency & Reconciliation'
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
          path: 'user-settings',
          name: 'user-settings',
          component: () => import('@/views/UserSettingsView.vue'),
          meta: {
            title: 'User Settings',
            icon: 'account'
          },
          children: [
            {
              path: '',
              name: 'user-settings-profile',
              component: () => import('@/views/user-settings/ProfileSettings.vue'),
              meta: {
                title: 'Profile Settings'
              }
            }
          ]
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
            // Phase 2: 5-Section Organization
            {
              path: 'core',
              name: 'settings-core',
              component: () => import('@/views/settings/CoreSettings.vue'),
              meta: {
                title: 'Core Settings',
                description: 'LLM models, API keys, and system mode'
              }
            },
            {
              path: 'search-retrieval',
              name: 'settings-search-retrieval',
              component: () => import('@/views/settings/SearchRetrievalSettings.vue'),
              meta: {
                title: 'Search & Retrieval',
                description: 'Query routing and RAG configuration'
              }
            },
            {
              path: 'taxonomy',
              name: 'settings-taxonomy',
              component: () => import('@/views/settings/TaxonomySettings.vue'),
              meta: {
                title: 'Search & Taxonomy',
                description: 'Manage categories, synonyms, and regex patterns'
              }
            },
            {
              path: 'response',
              name: 'settings-response',
              component: () => import('@/views/settings/ResponseSettings.vue'),
              meta: {
                title: 'Response Settings',
                description: 'Response formatting and caching'
              }
            },
            {
              path: 'security',
              name: 'settings-security',
              component: () => import('@/views/settings/SecuritySettings.vue'),
              meta: {
                title: 'Security & Monitoring',
                description: 'Security settings and analytics'
              }
            },
            {
              path: 'ux',
              name: 'settings-ux',
              component: () => import('@/views/settings/UXSettings.vue'),
              meta: {
                title: 'User Experience',
                description: 'Welcome messages and user-facing features'
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
