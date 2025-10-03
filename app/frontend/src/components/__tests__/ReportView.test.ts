import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ReportView from '@/views/ReportView.vue'
import { useReportStore } from '@/stores/report'
import { useProfileStore } from '@/stores/profile'

// Mock data for testing
const mockReport = {
  id: 'test-report-id',
  title: 'Test Rapport',
  content: {
    samenvatting: `# Samenvatting\n\nDit is een test samenvatting met een header.\n\n## Subheader\n\nMeer inhoud met verschillende headers.\n\n### Kleinere header\n\nNog meer inhoud.`,
    belastbaarheid: `# Belastbaarheid\n\n<h1>HTML Header</h1>\n\n**Fysieke belastbaarheid:** Goed\n\n<h2>Mentale belastbaarheid</h2>\n\nUitstekend voor complexe taken.`,
    visie_ad: `# Arbeidsdeskundige Visie\n\n### Professionele beoordeling\n\nDe cliënt toont goede mogelijkheden voor werkhervatting.\n\n**Aanbevelingen:**\n- Geleidelijke werkhervatting\n- Begeleiding bij aanpassing`,
    matching: `## Matching Criteria\n\n<h3>Fysieke eisen</h3>\n\nLicht fysiek werk mogelijk.\n\n<h1>Sociale vaardigheden</h1>\n\nUitstekende communicatie.`
  },
  case_id: 'test-case-id',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
}

const mockProfile = {
  id: 'test-profile-id',
  name: 'Test Arbeidsdeskundige',
  title: 'Arbeidsdeskundige',
  company: 'Test Company',
  email: 'test@example.com',
  phone: '+31 6 12345678',
  address: 'Test Straat 123, 1234 AB Test Stad',
  logo_url: null
}

describe('ReportView - processContentForTemplate', () => {
  let wrapper: any
  let reportStore: any
  let profileStore: any

  beforeEach(() => {
    setActivePinia(createPinia())
    reportStore = useReportStore()
    profileStore = useProfileStore()
    
    // Set up mock data
    reportStore.currentReport = mockReport
    profileStore.currentProfile = mockProfile
    
    wrapper = mount(ReportView, {
      global: {
        plugins: [createPinia()]
      }
    })
  })

  describe('Header Removal Tests', () => {
    it('should remove all markdown headers (H1-H6)', () => {
      const testContent = `# Header 1\n\nSome content\n\n## Header 2\n\nMore content\n\n### Header 3\n\nEven more content\n\n#### Header 4\n\n##### Header 5\n\n###### Header 6\n\nFinal content`
      
      const result = wrapper.vm.processContentForTemplate(testContent, 'standaard')
      
      // Should not contain any markdown headers
      expect(result).not.toMatch(/^#{1,6}\s+/m)
      expect(result).toContain('Some content')
      expect(result).toContain('More content')
      expect(result).toContain('Even more content')
      expect(result).toContain('Final content')
      expect(result).not.toContain('# Header 1')
      expect(result).not.toContain('## Header 2')
      expect(result).not.toContain('### Header 3')
    })

    it('should remove HTML headers (H1-H6)', () => {
      const testContent = `<h1>HTML Header 1</h1>\n\nContent after H1\n\n<h2>HTML Header 2</h2>\n\nContent after H2\n\n<h3 class=\"some-class\">Header with class</h3>\n\nFinal content`
      
      const result = wrapper.vm.processContentForTemplate(testContent, 'modern')
      
      // Should not contain any HTML headers
      expect(result).not.toMatch(/<h[1-6][^>]*>.*?<\/h[1-6]>/i)
      expect(result).toContain('Content after H1')
      expect(result).toContain('Content after H2')
      expect(result).toContain('Final content')
      expect(result).not.toContain('<h1>HTML Header 1</h1>')
      expect(result).not.toContain('<h2>HTML Header 2</h2>')
      expect(result).not.toContain('<h3 class=\"some-class\">Header with class</h3>')
    })

    it('should remove bold headers that look like titles', () => {
      const testContent = `**Dit is een titel:**\n\nEen paragraaf met inhoud.\n\n**Nog een titel:**\n\nMeer inhoud hier.\n\n**Laatste titel:**\n\nFinale paragraaf.`
      
      const result = wrapper.vm.processContentForTemplate(testContent, 'professioneel')
      
      // Should not contain bold headers that end with colon
      expect(result).not.toMatch(/\*\*[^*]+:\*\*/)
      expect(result).toContain('Een paragraaf met inhoud.')
      expect(result).toContain('Meer inhoud hier.')
      expect(result).toContain('Finale paragraaf.')
    })

    it('should handle mixed header types in single content', () => {
      const testContent = `# Markdown Header\n\n<h2>HTML Header</h2>\n\n**Bold Title:**\n\nActual content that should remain.\n\n### Another Markdown\n\n<h4>Another HTML</h4>\n\n**Another Bold:**\n\nMore content to keep.`
      
      const result = wrapper.vm.processContentForTemplate(testContent, 'compact')
      
      // Should remove all header types but keep content
      expect(result).not.toMatch(/^#{1,6}\s+/m)
      expect(result).not.toMatch(/<h[1-6][^>]*>.*?<\/h[1-6]>/i)
      expect(result).not.toMatch(/\*\*[^*]+:\*\*/)
      expect(result).toContain('Actual content that should remain.')
      expect(result).toContain('More content to keep.')
    })
  })

  describe('Content Preservation Tests', () => {
    it('should preserve regular bold text that is not a header', () => {
      const testContent = `Some text with **emphasized content** in the middle.\n\nAnother paragraph with **important information** here.`
      
      const result = wrapper.vm.processContentForTemplate(testContent, 'standaard')
      
      expect(result).toContain('**emphasized content**')
      expect(result).toContain('**important information**')
    })

    it('should preserve line breaks and paragraph structure', () => {
      const testContent = `First paragraph.\n\nSecond paragraph.\n\nThird paragraph.`
      
      const result = wrapper.vm.processContentForTemplate(testContent, 'modern')
      
      expect(result).toContain('First paragraph.')
      expect(result).toContain('Second paragraph.')
      expect(result).toContain('Third paragraph.')
      // Should maintain paragraph breaks
      expect(result.split('\n\n')).toHaveLength(3)
    })

    it('should preserve lists and other markdown formatting', () => {
      const testContent = `# Header to Remove\n\n- First item\n- Second item\n- Third item\n\n1. Numbered item\n2. Another numbered item\n\n*Italic text* and **bold text** should remain.`
      
      const result = wrapper.vm.processContentForTemplate(testContent, 'professioneel')
      
      expect(result).not.toContain('# Header to Remove')
      expect(result).toContain('- First item')
      expect(result).toContain('- Second item')
      expect(result).toContain('1. Numbered item')
      expect(result).toContain('*Italic text*')
      expect(result).toContain('**bold text**')
    })
  })

  describe('Edge Cases', () => {
    it('should handle empty content', () => {
      const result = wrapper.vm.processContentForTemplate('', 'standaard')
      expect(result).toBe('')
    })

    it('should handle null or undefined content', () => {
      expect(wrapper.vm.processContentForTemplate(null, 'modern')).toBe('')
      expect(wrapper.vm.processContentForTemplate(undefined, 'professioneel')).toBe('')
    })

    it('should handle content with only headers', () => {
      const testContent = `# Only Header 1\n\n## Only Header 2\n\n### Only Header 3`
      
      const result = wrapper.vm.processContentForTemplate(testContent, 'compact')
      
      // Should result in mostly empty content (just line breaks)
      expect(result.trim()).toBe('')
    })

    it('should handle malformed headers gracefully', () => {
      const testContent = `#Not a proper header\n\n# Proper header\n\nContent here\n\n##Also not proper\n\n<h1>Proper HTML header</h1>\n\nMore content`
      
      const result = wrapper.vm.processContentForTemplate(testContent, 'standaard')
      
      expect(result).toContain('#Not a proper header')
      expect(result).toContain('##Also not proper')
      expect(result).not.toContain('# Proper header')
      expect(result).not.toContain('<h1>Proper HTML header</h1>')
      expect(result).toContain('Content here')
      expect(result).toContain('More content')
    })
  })

  describe('Template Layout Integration', () => {
    it('should work with all template layouts', () => {
      const testContent = `# Test Header\n\nTest content for all layouts.`
      const layouts = ['standaard', 'modern', 'professioneel', 'compact']
      
      layouts.forEach(layout => {
        const result = wrapper.vm.processContentForTemplate(testContent, layout)
        expect(result).not.toContain('# Test Header')
        expect(result).toContain('Test content for all layouts.')
      })
    })
  })

  describe('Real Content Examples', () => {
    it('should process samenvatting section correctly', () => {
      const result = wrapper.vm.processContentForTemplate(mockReport.content.samenvatting, 'standaard')
      
      expect(result).not.toContain('# Samenvatting')
      expect(result).not.toContain('## Subheader')
      expect(result).not.toContain('### Kleinere header')
      expect(result).toContain('Dit is een test samenvatting met een header.')
      expect(result).toContain('Meer inhoud met verschillende headers.')
      expect(result).toContain('Nog meer inhoud.')
    })

    it('should process belastbaarheid section correctly', () => {
      const result = wrapper.vm.processContentForTemplate(mockReport.content.belastbaarheid, 'modern')
      
      expect(result).not.toContain('# Belastbaarheid')
      expect(result).not.toContain('<h1>HTML Header</h1>')
      expect(result).not.toContain('<h2>Mentale belastbaarheid</h2>')
      expect(result).toContain('**Fysieke belastbaarheid:** Goed')
      expect(result).toContain('Uitstekend voor complexe taken.')
    })

    it('should process visie_ad section correctly', () => {
      const result = wrapper.vm.processContentForTemplate(mockReport.content.visie_ad, 'professioneel')
      
      expect(result).not.toContain('# Arbeidsdeskundige Visie')
      expect(result).not.toContain('### Professionele beoordeling')
      expect(result).toContain('De cliënt toont goede mogelijkheden voor werkhervatting.')
      expect(result).toContain('**Aanbevelingen:**')
      expect(result).toContain('- Geleidelijke werkhervatting')
    })

    it('should process matching section correctly', () => {
      const result = wrapper.vm.processContentForTemplate(mockReport.content.matching, 'compact')
      
      expect(result).not.toContain('## Matching Criteria')
      expect(result).not.toContain('<h3>Fysieke eisen</h3>')
      expect(result).not.toContain('<h1>Sociale vaardigheden</h1>')
      expect(result).toContain('Licht fysiek werk mogelijk.')
      expect(result).toContain('Uitstekende communicatie.')
    })
  })
})
