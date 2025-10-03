/**
 * Test utilities for Vue component testing
 */

import { mount, VueWrapper } from '@vue/test-utils'
import { createPinia, Pinia } from 'pinia'
import { createRouter, createWebHistory, Router } from 'vue-router'
import { vi } from 'vitest'
import type { Component } from 'vue'

// Mock data factories
export const createMockCase = (overrides = {}) => ({
  id: 'test-case-id',
  title: 'Test Arbeidsdeskundige Case',
  description: 'Test case for arbeidsdeskundige beoordeling',
  status: 'active',
  client_info: {
    name: 'Jan de Vries',
    bsn: '123456789',
    birth_date: '1980-03-15'
  },
  created_at: '2024-01-15T10:00:00Z',
  updated_at: '2024-01-15T10:00:00Z',
  ...overrides
})

export const createMockDocument = (overrides = {}) => ({
  id: 'test-doc-id',
  case_id: 'test-case-id',
  filename: 'test_document.txt',
  mimetype: 'text/plain',
  size: 1024,
  status: 'processed',
  created_at: '2024-01-15T10:00:00Z',
  metadata: {
    language: 'dutch',
    word_count: 150
  },
  ...overrides
})

export const createMockReport = (overrides = {}) => ({
  id: 'test-report-id',
  case_id: 'test-case-id',
  template_id: 'staatvandienst',
  status: 'generated',
  content: {
    sections: {
      persoonsgegevens: {
        title: 'Persoonsgegevens',
        content: 'Jan de Vries, geboren 15-03-1980'
      },
      medische_situatie: {
        title: 'Medische Situatie',
        content: 'Chronische rugklachten met uitstraling'
      }
    }
  },
  created_at: '2024-01-15T10:00:00Z',
  ...overrides
})

export const createMockAudioFile = (overrides = {}) => ({
  id: 'test-audio-id',
  case_id: 'test-case-id',
  filename: 'interview.wav',
  duration: 120.5,
  status: 'transcribed',
  transcription: 'Dit is een test transcriptie van het gesprek.',
  created_at: '2024-01-15T10:00:00Z',
  metadata: {
    sample_rate: 44100,
    channels: 1
  },
  ...overrides
})

// Mock API responses
export const mockApiResponse = <T>(data: T, status = 200) => ({
  data,
  status,
  statusText: status === 200 ? 'OK' : 'Error',
  headers: {},
  config: {}
})

// Mock router
export const createMockRouter = (routes = []) => {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div>Home</div>' } },
      { path: '/cases', component: { template: '<div>Cases</div>' } },
      { path: '/cases/:id', component: { template: '<div>Case Detail</div>' } },
      { path: '/reports/:id', component: { template: '<div>Report</div>' } },
      ...routes
    ]
  })
}

// Mock stores
export const createMockAuthStore = () => ({
  user: {
    id: 'test-user-id',
    email: 'test@example.com',
    profile: {
      name: 'Test User',
      organization: 'Test Organization'
    }
  },
  isAuthenticated: true,
  token: 'mock-jwt-token',
  login: vi.fn(),
  logout: vi.fn(),
  refreshToken: vi.fn()
})

export const createMockCaseStore = () => ({
  cases: [createMockCase()],
  currentCase: createMockCase(),
  loading: false,
  error: null,
  fetchCases: vi.fn(),
  createCase: vi.fn(),
  updateCase: vi.fn(),
  deleteCase: vi.fn(),
  setCurrentCase: vi.fn()
})

export const createMockDocumentStore = () => ({
  documents: [createMockDocument()],
  loading: false,
  error: null,
  uploadDocument: vi.fn(),
  fetchDocuments: vi.fn(),
  deleteDocument: vi.fn(),
  downloadDocument: vi.fn()
})

export const createMockReportStore = () => ({
  reports: [createMockReport()],
  currentReport: createMockReport(),
  templates: {
    staatvandienst: {
      id: 'staatvandienst',
      name: 'Staatvandienst Format',
      sections: {
        persoonsgegevens: { title: 'Persoonsgegevens' },
        medische_situatie: { title: 'Medische Situatie' }
      }
    }
  },
  loading: false,
  error: null,
  generateReport: vi.fn(),
  fetchReports: vi.fn(),
  updateReport: vi.fn(),
  deleteReport: vi.fn(),
  exportReport: vi.fn()
})

// Component mounting helper
export interface MountOptions {
  props?: Record<string, any>
  slots?: Record<string, any>
  global?: {
    plugins?: any[]
    mocks?: Record<string, any>
    stubs?: Record<string, any>
  }
  router?: Router
  pinia?: Pinia
}

export const mountComponent = (component: Component, options: MountOptions = {}) => {
  const pinia = options.pinia || createPinia()
  const router = options.router || createMockRouter()
  
  const defaultGlobal = {
    plugins: [pinia, router],
    mocks: {
      $t: (key: string) => key, // Mock i18n
    },
    stubs: {
      'router-link': true,
      'router-view': true
    }
  }

  return mount(component, {
    ...options,
    global: {
      ...defaultGlobal,
      ...options.global,
      plugins: [
        ...(defaultGlobal.plugins || []),
        ...(options.global?.plugins || [])
      ],
      mocks: {
        ...defaultGlobal.mocks,
        ...options.global?.mocks
      }
    }
  })
}

// Async testing helpers
export const flushPromises = () => new Promise(resolve => setTimeout(resolve, 0))

export const waitForNextTick = async (wrapper: VueWrapper<any>) => {
  await wrapper.vm.$nextTick()
  await flushPromises()
}

// Event simulation helpers
export const simulateFileUpload = (input: any, file: File) => {
  const event = new Event('change', { bubbles: true })
  Object.defineProperty(input.element, 'files', {
    value: [file],
    writable: false,
  })
  input.element.dispatchEvent(event)
}

export const createMockFile = (name = 'test.txt', content = 'test content', type = 'text/plain') => {
  return new File([content], name, { type })
}

// Form interaction helpers
export const fillForm = async (wrapper: VueWrapper<any>, formData: Record<string, any>) => {
  for (const [field, value] of Object.entries(formData)) {
    const input = wrapper.find(`[data-testid="${field}"], [name="${field}"], #${field}`)
    if (input.exists()) {
      if (input.element.type === 'checkbox') {
        await input.setChecked(value)
      } else {
        await input.setValue(value)
      }
    }
  }
  await waitForNextTick(wrapper)
}

// Mock fetch responses
export const mockFetch = (response: any, status = 200) => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(response),
    text: () => Promise.resolve(JSON.stringify(response))
  })
}

// DOM query helpers
export const findByTestId = (wrapper: VueWrapper<any>, testId: string) => {
  return wrapper.find(`[data-testid="${testId}"]`)
}

export const findAllByTestId = (wrapper: VueWrapper<any>, testId: string) => {
  return wrapper.findAll(`[data-testid="${testId}"]`)
}

// Assertion helpers
export const expectElementToExist = (wrapper: VueWrapper<any>, selector: string) => {
  expect(wrapper.find(selector).exists()).toBe(true)
}

export const expectElementNotToExist = (wrapper: VueWrapper<any>, selector: string) => {
  expect(wrapper.find(selector).exists()).toBe(false)
}

export const expectTextContent = (wrapper: VueWrapper<any>, selector: string, text: string) => {
  const element = wrapper.find(selector)
  expect(element.exists()).toBe(true)
  expect(element.text()).toContain(text)
}

// Mock MediaRecorder for audio testing
export const mockMediaRecorder = () => {
  const mockMediaRecorder = vi.fn().mockImplementation(() => ({
    start: vi.fn(),
    stop: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
    ondataavailable: null,
    onstop: null,
    state: 'inactive'
  }))
  
  vi.stubGlobal('MediaRecorder', mockMediaRecorder)
  
  return mockMediaRecorder
}

// Mock getUserMedia for audio recording
export const mockGetUserMedia = () => {
  const mockGetUserMedia = vi.fn().mockResolvedValue({
    getTracks: () => [{
      stop: vi.fn(),
      kind: 'audio'
    }]
  })
  
  Object.defineProperty(navigator, 'mediaDevices', {
    value: {
      getUserMedia: mockGetUserMedia
    },
    writable: true
  })
  
  return mockGetUserMedia
}