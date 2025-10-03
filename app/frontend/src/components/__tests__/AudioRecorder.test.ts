/**
 * Unit tests for AudioRecorder component
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { nextTick } from 'vue'
import AudioRecorder from '../audio/AudioRecorder.vue'
import {
  mountComponent,
  waitForNextTick,
  mockMediaRecorder,
  mockGetUserMedia,
  createMockCase,
  findByTestId
} from '../../test/utils'

describe('AudioRecorder', () => {
  let mockMediaRecorderInstance: any
  let mockGetUserMediaInstance: any

  beforeEach(() => {
    mockMediaRecorderInstance = mockMediaRecorder()
    mockGetUserMediaInstance = mockGetUserMedia()
    
    // Mock URL.createObjectURL
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:mock-audio-url'),
      revokeObjectURL: vi.fn()
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
    vi.unstubAllGlobals()
  })

  it('renders initial state correctly', () => {
    const wrapper = mountComponent(AudioRecorder, {
      props: {
        caseId: 'test-case-id'
      }
    })

    expect(wrapper.find('.audio-recorder').exists()).toBe(true)
    expect(wrapper.find('.status-indicator').text()).toContain('Klaar om op te nemen')
    expect(wrapper.find('button').text()).toContain('Start Opname')
    expect(wrapper.find('.fa-microphone').exists()).toBe(true)
  })

  it('starts recording when start button is clicked', async () => {
    const wrapper = mountComponent(AudioRecorder, {
      props: {
        caseId: 'test-case-id'
      }
    })

    const startButton = wrapper.find('button')
    await startButton.trigger('click')

    expect(mockGetUserMediaInstance).toHaveBeenCalledWith({ audio: true })
    expect(wrapper.vm.isRecording).toBe(true)
    expect(wrapper.find('.status-indicator').text()).toContain('Opname:')
    expect(wrapper.find('button').text()).toContain('Stop Opname')
    expect(wrapper.find('.fa-stop').exists()).toBe(true)
  })

  it('stops recording when stop button is clicked', async () => {
    const wrapper = mountComponent(AudioRecorder, {
      props: {
        caseId: 'test-case-id'
      }
    })

    // Start recording first
    await wrapper.find('button').trigger('click')
    expect(wrapper.vm.isRecording).toBe(true)

    // Stop recording
    await wrapper.find('button').trigger('click')
    expect(wrapper.vm.isRecording).toBe(false)
    expect(wrapper.find('button').text()).toContain('Start Opname')
  })

  it('displays recording duration while recording', async () => {
    const wrapper = mountComponent(AudioRecorder, {
      props: {
        caseId: 'test-case-id'
      }
    })

    // Mock timer behavior
    vi.useFakeTimers()
    
    await wrapper.find('button').trigger('click')
    expect(wrapper.vm.isRecording).toBe(true)

    // Advance timer
    vi.advanceTimersByTime(5000) // 5 seconds
    await nextTick()

    expect(wrapper.vm.duration).toBe(5)
    expect(wrapper.vm.formattedDuration).toBe('00:05')

    vi.useRealTimers()
  })

  it('shows audio preview after recording', async () => {
    const wrapper = mountComponent(AudioRecorder, {
      props: {
        caseId: 'test-case-id'
      }
    })

    // Start and stop recording to create audio blob
    await wrapper.find('button').trigger('click')
    await wrapper.find('button').trigger('click')

    // Simulate audio data available
    wrapper.vm.audioUrl = 'blob:mock-audio-url'
    await nextTick()

    expect(wrapper.find('.audio-preview').exists()).toBe(true)
    expect(wrapper.find('.audio-player').exists()).toBe(true)
    expect(wrapper.find('button').text()).toContain('Afspelen')
  })

  it('allows playback of recorded audio', async () => {
    const wrapper = mountComponent(AudioRecorder, {
      props: {
        caseId: 'test-case-id'
      }
    })

    // Set up recorded audio
    wrapper.vm.audioUrl = 'blob:mock-audio-url'
    await nextTick()

    const playButton = wrapper.findAll('button').find(btn => 
      btn.text().includes('Afspelen')
    )
    expect(playButton).toBeDefined()

    // Mock audio element
    const mockAudio = {
      play: vi.fn().mockResolvedValue(undefined),
      pause: vi.fn(),
      currentTime: 0,
      duration: 10
    }
    wrapper.vm.$refs.audioPlayer = mockAudio

    await playButton!.trigger('click')
    expect(mockAudio.play).toHaveBeenCalled()
    expect(wrapper.vm.isPlaying).toBe(true)
  })

  it('allows saving of recorded audio', async () => {
    const mockApiCall = vi.fn().mockResolvedValue({
      data: { id: 'audio-123', status: 'uploaded' }
    })

    const wrapper = mountComponent(AudioRecorder, {
      props: {
        caseId: 'test-case-id'
      },
      global: {
        mocks: {
          $api: {
            post: mockApiCall
          }
        }
      }
    })

    // Set up recorded audio
    wrapper.vm.audioUrl = 'blob:mock-audio-url'
    wrapper.vm.audioBlob = new Blob(['fake audio data'], { type: 'audio/wav' })
    wrapper.vm.title = 'Test Recording'
    wrapper.vm.description = 'Test Description'
    await nextTick()

    const saveButton = wrapper.findAll('button').find(btn => 
      btn.text().includes('Opname Opslaan')
    )
    expect(saveButton).toBeDefined()

    await saveButton!.trigger('click')

    expect(mockApiCall).toHaveBeenCalledWith(
      '/api/v1/audio/upload',
      expect.any(FormData)
    )
    expect(wrapper.vm.isProcessing).toBe(true)
  })

  it('handles recording errors gracefully', async () => {
    const mockError = new Error('Microphone access denied')
    mockGetUserMediaInstance.mockRejectedValue(mockError)

    const wrapper = mountComponent(AudioRecorder, {
      props: {
        caseId: 'test-case-id'
      }
    })

    const startButton = wrapper.find('button')
    await startButton.trigger('click')

    await nextTick()

    expect(wrapper.vm.error).toBeTruthy()
    expect(wrapper.vm.isRecording).toBe(false)
    expect(wrapper.find('.error-message').exists()).toBe(true)
  })

  it('displays waveform visualization during recording', async () => {
    const wrapper = mountComponent(AudioRecorder, {
      props: {
        caseId: 'test-case-id'
      }
    })

    await wrapper.find('button').trigger('click')
    expect(wrapper.vm.isRecording).toBe(true)

    // Mock canvas context for waveform
    const mockCanvas = {
      getContext: vi.fn().mockReturnValue({
        clearRect: vi.fn(),
        beginPath: vi.fn(),
        moveTo: vi.fn(),
        lineTo: vi.fn(),
        stroke: vi.fn(),
        strokeStyle: '',
        lineWidth: 1
      }),
      width: 400,
      height: 100
    }

    wrapper.vm.$refs.waveformCanvas = mockCanvas
    wrapper.vm.updateWaveform([0.1, 0.3, 0.5, 0.2, 0.4])

    expect(mockCanvas.getContext).toHaveBeenCalledWith('2d')
  })

  it('validates recording title and description', async () => {
    const wrapper = mountComponent(AudioRecorder, {
      props: {
        caseId: 'test-case-id'
      }
    })

    // Set up recorded audio without title
    wrapper.vm.audioUrl = 'blob:mock-audio-url'
    wrapper.vm.audioBlob = new Blob(['fake audio data'], { type: 'audio/wav' })
    wrapper.vm.title = '' // Empty title
    await nextTick()

    const saveButton = wrapper.findAll('button').find(btn => 
      btn.text().includes('Opname Opslaan')
    )

    await saveButton!.trigger('click')

    expect(wrapper.vm.error).toContain('Titel is verplicht')
    expect(wrapper.find('.error-message').exists()).toBe(true)
  })

  it('emits events when recording is saved', async () => {
    const mockApiCall = vi.fn().mockResolvedValue({
      data: { id: 'audio-123', status: 'uploaded' }
    })

    const wrapper = mountComponent(AudioRecorder, {
      props: {
        caseId: 'test-case-id'
      },
      global: {
        mocks: {
          $api: {
            post: mockApiCall
          }
        }
      }
    })

    // Set up recorded audio
    wrapper.vm.audioUrl = 'blob:mock-audio-url'
    wrapper.vm.audioBlob = new Blob(['fake audio data'], { type: 'audio/wav' })
    wrapper.vm.title = 'Test Recording'
    await nextTick()

    const saveButton = wrapper.findAll('button').find(btn => 
      btn.text().includes('Opname Opslaan')
    )

    await saveButton!.trigger('click')
    await waitForNextTick(wrapper)

    expect(wrapper.emitted().audioSaved).toBeTruthy()
    expect(wrapper.emitted().audioSaved[0]).toEqual([{
      id: 'audio-123',
      status: 'uploaded'
    }])
  })

  it('cleans up resources when component is unmounted', () => {
    const wrapper = mountComponent(AudioRecorder, {
      props: {
        caseId: 'test-case-id'
      }
    })

    const mockStream = {
      getTracks: vi.fn().mockReturnValue([
        { stop: vi.fn() }
      ])
    }
    wrapper.vm.mediaStream = mockStream

    wrapper.unmount()
    
    expect(mockStream.getTracks()[0].stop).toHaveBeenCalled()
  })

  it('shows appropriate UI states during processing', async () => {
    const wrapper = mountComponent(AudioRecorder, {
      props: {
        caseId: 'test-case-id'
      }
    })

    // Test processing state
    wrapper.vm.isProcessing = true
    await nextTick()

    const buttons = wrapper.findAll('button')
    buttons.forEach(button => {
      if (button.text().includes('Bezig met verwerken')) {
        expect(button.attributes('disabled')).toBeDefined()
        expect(button.find('.fa-spinner').exists()).toBe(true)
      }
    })
  })

  it('formats duration correctly', () => {
    const wrapper = mountComponent(AudioRecorder, {
      props: {
        caseId: 'test-case-id'
      }
    })

    expect(wrapper.vm.formatDuration(0)).toBe('00:00')
    expect(wrapper.vm.formatDuration(65)).toBe('01:05')
    expect(wrapper.vm.formatDuration(3661)).toBe('61:01') // Over 1 hour
  })

  it('handles microphone permissions correctly', async () => {
    // Test permission denied
    mockGetUserMediaInstance.mockRejectedValue(
      new DOMException('Permission denied', 'NotAllowedError')
    )

    const wrapper = mountComponent(AudioRecorder, {
      props: {
        caseId: 'test-case-id'
      }
    })

    await wrapper.find('button').trigger('click')
    await nextTick()

    expect(wrapper.vm.error).toContain('Microphone toegang geweigerd')
    expect(wrapper.find('.error-message').exists()).toBe(true)
  })

  it('supports keyboard navigation', async () => {
    const wrapper = mountComponent(AudioRecorder, {
      props: {
        caseId: 'test-case-id'
      }
    })

    const startButton = wrapper.find('button')
    
    // Test Space key to start recording
    await startButton.trigger('keydown.space')
    expect(wrapper.vm.isRecording).toBe(true)

    // Test Escape key to stop recording
    await wrapper.trigger('keydown.escape')
    expect(wrapper.vm.isRecording).toBe(false)
  })
})