import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import App from '../App.vue'
import AppHeader from '../components/AppHeader.vue'
import { createRouter, createMemoryHistory } from 'vue-router'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    {
      path: '/',
      component: { template: '<div>Home View Stub</div>' }
    }
  ]
})

describe('App Root Component', () => {
  it('renders the header and main content wrapper', async () => {
    router.push('/')
    await router.isReady()

    const wrapper = mount(App, {
      global: {
        plugins: [router]
      }
    })

    expect(wrapper.findComponent(AppHeader).exists()).toBe(true)
    expect(wrapper.find('.main-content').exists()).toBe(true)
  })
})
