import { createRouter, createWebHistory } from 'vue-router'
import AdminLayout from '@/components/AdminLayout.vue'
import { useAdminStore } from '@/stores/admin'

// API base URL configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

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
      path: '/test-password',
      name: 'test-password',
      component: () => import('@/views/ChangePasswordSimple.vue'),
      meta: {
        title: 'Test Change Password',
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
  
  // Check if route requires authentication
  if (to.meta.requiresAuth || to.path.startsWith('/admin')) {
    // Check for valid authentication token
    const token = localStorage.getItem('admin_token')
    let isAuthenticated = false
    
    if (token) {
      try {
        // Quick token validation
        const response = await fetch(`${API_BASE_URL}/admin/api/auth/me`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        isAuthenticated = response.ok
      } catch (err) {
        // Token invalid, clear it
        localStorage.removeItem('admin_token')
        isAuthenticated = false
      }
    }
    
    if (!isAuthenticated) {
      // Redirect to login with return path
      next({ name: 'login', query: { redirect: to.fullPath } })
      return
    }
  }
  
  // If going to login but already have valid token, check auth and redirect
  if (to.name === 'login') {
    const token = localStorage.getItem('admin_token')
    if (token) {
      try {
        const response = await fetch(`${API_BASE_URL}/admin/api/auth/me`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        if (response.ok) {
          // Already authenticated, redirect to intended destination or dashboard
          const redirect = to.query.redirect || '/admin'
          next(redirect)
          return
        }
      } catch (err) {
        // Token invalid, clear it and continue to login
        localStorage.removeItem('admin_token')
      }
    }
  }
  
  next()
})

export default router