import { createRouter, createWebHistory } from 'vue-router'
import AdminLayout from '@/components/AdminLayout.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/admin',
      component: AdminLayout,
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
          path: 'content',
          name: 'content',
          component: () => import('@/views/ContentView.vue'),
          meta: {
            title: 'Content',
            icon: 'document'
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
router.beforeEach((to, from, next) => {
  // Update document title
  document.title = to.meta.title ? `${to.meta.title} - RAG Admin` : 'RAG Admin Dashboard'
  next()
})

export default router