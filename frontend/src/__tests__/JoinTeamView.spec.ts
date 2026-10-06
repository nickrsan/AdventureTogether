import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import JoinTeamView from '../views/JoinTeamView.vue'
import { createRouter, createMemoryHistory } from 'vue-router'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    {
      path: '/events/:id/join',
      name: 'join-team',
      component: JoinTeamView
    },
    {
      path: '/events/:id/map',
      name: 'event-map',
      component: { template: '<div>Event Map</div>' }
    }
  ]
})

describe('JoinTeamView Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('renders tab controls for joining and creating teams', async () => {
    router.push('/events/1/join')
    await router.isReady()

    const wrapper = mount(JoinTeamView, {
      global: {
        plugins: [router]
      }
    })

    expect(wrapper.text()).toContain('Team Management')
    expect(wrapper.text()).toContain('Join Existing Team')
    expect(wrapper.text()).toContain('Create New Team')
  })

  it('switches between join code tab and create team tab', async () => {
    router.push('/events/1/join')
    await router.isReady()

    const wrapper = mount(JoinTeamView, {
      global: {
        plugins: [router]
      }
    })

    // Initially in join tab
    expect(wrapper.find('#joinCode').exists()).toBe(true)
    expect(wrapper.find('#teamName').exists()).toBe(false)

    // Switch to create tab
    const buttons = wrapper.findAll('.tab-controls button')
    await buttons[1].trigger('click')

    expect(wrapper.find('#teamName').exists()).toBe(true)
    expect(wrapper.find('#joinCode').exists()).toBe(false)
  })
})
