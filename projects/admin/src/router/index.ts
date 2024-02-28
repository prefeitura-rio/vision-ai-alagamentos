import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  linkActiveClass: 'active',
  routes: [
    { path: '/', component: () => import('../views/HomeView.vue') },
    { path: '/login', component: () => import('../views/LoginView.vue') },
    { path: '/agents', component: () => import('../views/AgentsList.vue') },
    { path: '/agents/:id', component: () => import('../views/AgentDetails.vue') },
    { path: '/cameras', component: () => import('../views/CamerasList.vue') },
    { path: '/cameras/new', component: () => import('../views/CameraNew.vue') },
    { path: '/cameras/:id', component: () => import('../views/CameraDetails.vue') },
    { path: '/cameras/:id/snapshots', component: () => import('../views/CameraSnapshots.vue') },
    { path: '/objects', component: () => import('../views/ObjectsList.vue') },
    { path: '/objects/new', component: () => import('../views/ObjectNew.vue') },
    { path: '/objects/:id', component: () => import('../views/ObjectDetails.vue') },
    { path: '/prompts', component: () => import('../views/PromptsList.vue') },
    { path: '/prompts/new', component: () => import('../views/PromptNew.vue') },
    { path: '/prompts/:id', component: () => import('../views/PromptDetails.vue') },
    { path: '/404', component: () => import('../views/NotFoundView.vue') },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('../views/NotFoundView.vue')
    }
  ]
})

router.resolve({
  name: 'not-found',
  params: { pathMatch: ['not', 'found'] }
}).href // '/not/found'

router.beforeEach(async (to) => {
  // redirect to login page if not logged in and trying to access a restricted page
  const publicPages = ['/', '/404', '/login']
  const authRequired = !publicPages.includes(to.path)
  const auth = useAuthStore()

  if (authRequired && !auth.user) {
    auth.returnUrl = to.fullPath
    return '/404'
  }
})

export default router
