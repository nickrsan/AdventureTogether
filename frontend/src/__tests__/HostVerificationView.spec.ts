import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import HostVerificationView from '../views/HostVerificationView.vue'
import { createRouter, createMemoryHistory } from 'vue-router'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    {
      path: '/events/:id/host/verify',
      name: 'host-verify',
      component: HostVerificationView
    }
  ]
})

describe('HostVerificationView Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the verification portal header and filter controls', async () => {
    router.push('/events/1/host/verify')
    await router.isReady()

    const wrapper = mount(HostVerificationView, {
      global: {
        plugins: [router]
      }
    })

    expect(wrapper.text()).toContain('Host Verification Portal')
    expect(wrapper.text()).toContain('Verification Status:')
    expect(wrapper.text()).toContain('Source Platform:')
  })
})
