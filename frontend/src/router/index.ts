/**
 * AdventureTogether Vue Router Configuration
 * Uses dynamic imports for heavy host components to optimize mobile bundle size.
 */

import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import EventMapView from '../views/EventMapView.vue'
import JoinTeamView from '../views/JoinTeamView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/events/:id/map',
      name: 'event-map',
      component: EventMapView
    },
    {
      path: '/events/:id/join',
      name: 'join-team',
      component: JoinTeamView
    },
    {
      path: '/events/:id/host/builder',
      name: 'host-builder',
      // Lazy-loaded to keep mobile client payload minimal
      component: () => import('../views/HostQuestBuilderView.vue')
    },
    {
      path: '/events/:id/host/verify',
      name: 'host-verify',
      // Lazy-loaded to keep mobile client payload minimal
      component: () => import('../views/HostVerificationView.vue')
    }
  ]
})

export default router
