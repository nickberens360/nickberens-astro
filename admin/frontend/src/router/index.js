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
      path: '/admin',
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
            icon: 'library_books'
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
          path: 'change-password',
          name: 'change-password',
          component: () => import('@/views/ChangePassword.vue'),
          meta: {
            title: 'Change Password',
            icon: 'lock'
          }
        }
      ]
    },
    {
      path: '/',
      redirect: '/admin'
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/admin'
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
    // Check authentication status
    const isAuthenticated = adminStore.isAuthenticated || await adminStore.checkAuth()
    
    if (!isAuthenticated) {
      // Redirect to login
      next({ name: 'login', query: { redirect: to.fullPath } })
      return
    }
  }
  
  // If going to login but already authenticated, redirect to dashboard
  if (to.name === 'login' && adminStore.isAuthenticated) {
    next({ name: 'dashboard' })
    return
  }
  
  next()
})

export default router