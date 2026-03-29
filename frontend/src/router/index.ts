import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth-store'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { guest: true }
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { guest: true }
    },
    {
      path: '/documents/:id',
      name: 'document-detail',
      component: () => import('@/views/DocumentDetailView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/search',
      name: 'search',
      component: () => import('@/views/SearchView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('@/views/ChatView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/views/AdminView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    // Organization routes
    {
      path: '/organizations',
      name: 'organizations',
      component: () => import('@/views/organizations/OrganizationListView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/organizations/:id',
      name: 'organization-detail',
      component: () => import('@/views/organizations/OrganizationDetailView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/organizations/:id/members',
      name: 'organization-members',
      component: () => import('@/views/organizations/OrganizationMembersView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/organizations/:id/groups',
      name: 'organization-groups',
      component: () => import('@/views/organizations/OrganizationGroupsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/organizations/:id/settings',
      name: 'organization-settings',
      component: () => import('@/views/organizations/OrganizationSettingsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/invitations/accept/:token',
      name: 'accept-invitation',
      component: () => import('@/views/organizations/AcceptInvitationView.vue'),
      meta: { guest: true }
    },
    {
      path: '/invitations/info/:token',
      name: 'invitation-info',
      component: () => import('@/views/organizations/InvitationInfoView.vue'),
      meta: { guest: true }
    }
  ]
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // Initialize auth state if not already done
  if (authStore.accessToken && !authStore.user) {
    await authStore.fetchUser()
  }

  // Auth required but not authenticated
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'login', query: { redirect: to.fullPath } })
    return
  }

  // Guest only pages (login/register) but already authenticated
  if (to.meta.guest && authStore.isAuthenticated) {
    next({ name: 'dashboard' })
    return
  }

  // Admin required but not admin
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    next({ name: 'dashboard' })
    return
  }

  next()
})

export default router
