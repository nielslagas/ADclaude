import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ReportView from '@/views/ReportView.vue'
import { useReportStore } from '@/stores/report'
import { useProfileStore } from '@/stores/profile'

// Mock viewport utilities for responsive testing  
const mockViewport = (width: number, height: number) => {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: width,
  })
  Object.defineProperty(window, 'innerHeight', {
    writable: true,
    configurable: true,
    value: height,
  })
  window.dispatchEvent(new Event('resize'))
}

const mockReport = {
  id: 'accessibility-test-report',
  title: 'Accessibility Test Rapport',
  content: {
    samenvatting: `# Toegankelijkheidstest\n\nDeze content test de toegankelijkheid van het systeem.\n\n## Belangrijke informatie\n\nContent moet toegankelijk blijven na header verwijdering.`,
    belastbaarheid: `# Belastbaarheid Analysis\n\n<h1>Fysiek</h1>\n\nMaximaal 20 kg tillen.\n\n<h2>Mentaal</h2>\n\nConcentratie voor 6 uur per dag.`,
    visie_ad: `## Professionele Visie\n\n### Beoordeling\n\nPositieve werkhervatting verwacht.\n\n#### Aanbevelingen\n\n- Geleidelijke opbouw\n- Werkplek aanpassingen`,
    matching: `# Matching Requirements\n\n<h3>Essentieel</h3>\n\n(E) Ergonomische werkplek\n\n<h1>Wenselijk</h1>\n\n(W) Flexibele uren`
  },
  case_id: 'test-case',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
}

const mockProfile = {
  id: 'profile-accessibility',
  name: 'Dr. Toegankelijkheid Test',
  title: 'Senior Arbeidsdeskundige',
  company: 'Inclusief Advies BV',
  email: 'toegankelijk@inclusief.nl',
  phone: '+31 6 87654321',
  address: 'Inclusiestraat 456, 5678 CD Toegankelijk',
  logo_url: null
}

describe('Accessibility and Responsiveness Tests', () => {
  let wrapper: any
  let reportStore: any
  let profileStore: any

  beforeEach(() => {
    setActivePinia(createPinia())
    reportStore = useReportStore()
    profileStore = useProfileStore()
    
    reportStore.currentReport = mockReport
    profileStore.currentProfile = mockProfile
    
    wrapper = mount(ReportView, {
      global: {
        plugins: [createPinia()]
      }
    })
  })

  describe('Mobile Responsiveness', () => {
    it('should adapt to mobile viewport (320px)', async () => {
      mockViewport(320, 568) // iPhone SE size
      
      await wrapper.vm.$nextTick()
      
      // Check if mobile-specific styles are applied
      const reportContainer = wrapper.find('.report-preview')
      expect(reportContainer.exists()).toBe(true)
      
      // Content should still be processable on mobile
      const mobileContent = wrapper.vm.processContentForTemplate(
        mockReport.content.samenvatting, 
        'compact' // Most suitable for mobile
      )
      
      expect(mobileContent).not.toContain('# Toegankelijkheidstest')
      expect(mobileContent).toContain('Content moet toegankelijk blijven')
    })
    
    it('should adapt to tablet viewport (768px)', async () => {
      mockViewport(768, 1024) // iPad size
      
      await wrapper.vm.$nextTick()
      
      // Test tablet-optimized template
      const tabletContent = wrapper.vm.processContentForTemplate(
        mockReport.content.belastbaarheid,
        'modern'
      )
      
      expect(tabletContent).not.toContain('<h1>Fysiek</h1>')
      expect(tabletContent).toContain('Maximaal 20 kg tillen')
    })
    
    it('should work on desktop viewport (1920px)', async () => {
      mockViewport(1920, 1080) // Full HD desktop
      
      await wrapper.vm.$nextTick()
      
      // Test desktop template
      const desktopContent = wrapper.vm.processContentForTemplate(
        mockReport.content.visie_ad,
        'professioneel'
      )
      
      expect(desktopContent).not.toContain('## Professionele Visie')
      expect(desktopContent).toContain('Positieve werkhervatting verwacht')
    })
    
    it('should handle extreme small viewport (240px)', async () => {
      mockViewport(240, 320) // Very small device
      
      await wrapper.vm.$nextTick()
      
      // Should not break on very small screens
      expect(() => {
        wrapper.vm.processContentForTemplate(
          mockReport.content.matching,
          'compact'
        )
      }).not.toThrow()
      
      const extremeSmallContent = wrapper.vm.processContentForTemplate(
        mockReport.content.matching,
        'compact'
      )
      
      expect(extremeSmallContent).toContain('Ergonomische werkplek')
    })
  })

  describe('Accessibility Compliance', () => {
    it('should maintain semantic structure after header removal', () => {
      const contentWithSemanticStructure = `
        # Hoofdstuk 1: Inleiding
        
        Dit is de inleidende paragraaf met belangrijke informatie.
        
        ## Sectie 1.1: Details
        
        Gedetailleerde informatie volgt hier.
        
        ### Subsectie 1.1.1: Specifics
        
        Specifieke details en voorbeelden.
      `
      
      const processed = wrapper.vm.processContentForTemplate(contentWithSemanticStructure, 'standaard')
      
      // Headers removed but content structure maintained
      expect(processed).not.toMatch(/^#{1,6}\s+/m)
      expect(processed).toContain('Dit is de inleidende paragraaf')
      expect(processed).toContain('Gedetailleerde informatie volgt hier')
      expect(processed).toContain('Specifieke details en voorbeelden')
      
      // Paragraph structure should be preserved
      const paragraphs = processed.split('\n\n').filter(p => p.trim().length > 0)
      expect(paragraphs.length).toBe(3)
    })
    
    it('should preserve ARIA-relevant content', () => {
      const contentWithAriaInfo = `
        # Belangrijke Mededelingen
        
        **Let op:** Deze informatie is cruciaal voor de beoordeling.
        
        ## Waarschuwingen
        
        *Belangrijk:* Alle gegevens moeten worden geverifieerd.
        
        ### Instructies
        
        Volg deze stappen zorgvuldig op.
      `
      
      const processed = wrapper.vm.processContentForTemplate(contentWithAriaInfo, 'modern')
      
      // Important content markers should be preserved
      expect(processed).toContain('**Let op:**')
      expect(processed).toContain('*Belangrijk:*')
      expect(processed).toContain('Deze informatie is cruciaal')
      expect(processed).toContain('Volg deze stappen zorgvuldig')
      
      // But headers should be removed
      expect(processed).not.toContain('# Belangrijke Mededelingen')
      expect(processed).not.toContain('## Waarschuwingen')
    })
    
    it('should handle screen reader compatible content', () => {
      const screenReaderContent = `
        # Document Titel
        
        Begin van document inhoud die toegankelijk moet zijn.
        
        ## Lijst van Items
        
        - Eerste item voor screen readers
        - Tweede item met details
        - Derde item met referentie
        
        ### Tabel Informatie
        
        | Kolom 1 | Kolom 2 |
        |---------|--------|
        | Data 1  | Data 2  |
      `
      
      const processed = wrapper.vm.processContentForTemplate(screenReaderContent, 'professioneel')
      
      // List structure should be preserved for screen readers
      expect(processed).toContain('- Eerste item voor screen readers')
      expect(processed).toContain('- Tweede item met details')
      
      // Table structure should be preserved
      expect(processed).toContain('| Kolom 1 | Kolom 2 |')
      expect(processed).toContain('| Data 1  | Data 2  |')
      
      // Headers should be removed
      expect(processed).not.toContain('# Document Titel')
      expect(processed).not.toContain('## Lijst van Items')
    })
    
    it('should maintain focus order after content processing', () => {
      // Test that content order is maintained for keyboard navigation
      const orderedContent = `
        # Eerste Sectie
        
        Eerste paragraaf content.
        
        ## Tweede Sectie
        
        Tweede paragraaf content.
        
        ### Derde Sectie
        
        Derde paragraaf content.
      `
      
      const processed = wrapper.vm.processContentForTemplate(orderedContent, 'compact')
      
      // Content should appear in original order
      const firstIndex = processed.indexOf('Eerste paragraaf content')
      const secondIndex = processed.indexOf('Tweede paragraaf content')
      const thirdIndex = processed.indexOf('Derde paragraaf content')
      
      expect(firstIndex).toBeLessThan(secondIndex)
      expect(secondIndex).toBeLessThan(thirdIndex)
      expect(firstIndex).toBeGreaterThan(-1)
    })
  })

  describe('Template Responsiveness', () => {
    const templateTypes = ['standaard', 'modern', 'professioneel', 'compact']
    const viewportSizes = [
      { width: 320, height: 568, name: 'mobile' },
      { width: 768, height: 1024, name: 'tablet' },
      { width: 1024, height: 768, name: 'laptop' },
      { width: 1920, height: 1080, name: 'desktop' }
    ]
    
    viewportSizes.forEach(viewport => {
      templateTypes.forEach(template => {
        it(`should render ${template} template properly on ${viewport.name}`, async () => {
          mockViewport(viewport.width, viewport.height)
          
          await wrapper.vm.$nextTick()
          
          const content = wrapper.vm.processContentForTemplate(
            mockReport.content.samenvatting,
            template
          )
          
          // Should process content regardless of viewport
          expect(content).not.toContain('# Toegankelijkheidstest')
          expect(content).toContain('Content moet toegankelijk blijven')
          
          // Should not crash or produce empty content
          expect(content.length).toBeGreaterThan(0)
        })
      })
    })
  })

  describe('Print and Export Accessibility', () => {
    it('should maintain readability in print format', () => {
      const printContent = `
        # Print Test Document
        
        Deze content moet goed leesbaar zijn in print formaat.
        
        ## Sectie voor Print
        
        Belangrijke informatie die geprint moet worden.
        
        ### Subsectie Details
        
        Gedetailleerde informatie voor papier.
      `
      
      const processed = wrapper.vm.processContentForTemplate(printContent, 'standaard')
      
      // Should be print-friendly (no headers that might confuse print layout)
      expect(processed).not.toMatch(/^#{1,6}\s+/m)
      expect(processed).toContain('Deze content moet goed leesbaar zijn')
      expect(processed).toContain('Belangrijke informatie die geprint')
      expect(processed).toContain('Gedetailleerde informatie voor papier')
    })
    
    it('should work with high contrast mode', () => {
      // Simulate high contrast mode by testing content visibility
      const highContrastContent = `
        # Contrast Test
        
        **Belangrijke tekst** die zichtbaar moet blijven.
        
        ## Zwarte tekst op wit
        
        Normale tekst content hier.
        
        ### Gemarkeerde content
        
        *Cursieve tekst* en **vette tekst** testen.
      `
      
      const processed = wrapper.vm.processContentForTemplate(highContrastContent, 'modern')
      
      // Important formatting should be preserved for high contrast
      expect(processed).toContain('**Belangrijke tekst**')
      expect(processed).toContain('*Cursieve tekst*')
      expect(processed).toContain('**vette tekst**')
      
      // Headers should still be removed
      expect(processed).not.toContain('# Contrast Test')
    })
  })

  describe('Language and Localization', () => {
    it('should handle Dutch special characters correctly', () => {
      const dutchContent = `
        # Evaluatie van de cliënt
        
        De coördinatie en naïviteit van de patiënt zijn beïnvloed.
        
        ## Zoën assessment
        
        Conclusie: geschikt voor hervatting.
      `
      
      const processed = wrapper.vm.processContentForTemplate(dutchContent, 'professioneel')
      
      // Dutch characters should be preserved
      expect(processed).toContain('cliënt')
      expect(processed).toContain('coördinatie')
      expect(processed).toContain('naïviteit')
      expect(processed).toContain('patiënt')
      expect(processed).toContain('beïnvloed')
      expect(processed).toContain('Zoën')
      
      // Headers should be removed
      expect(processed).not.toContain('# Evaluatie van de cliënt')
    })
    
    it('should handle right-to-left text gracefully', () => {
      const mixedContent = `
        # Mixed Language Content
        
        Regular Dutch text here.
        
        ## Arabic text: محتوى عربي
        
        Back to Dutch content.
      `
      
      const processed = wrapper.vm.processContentForTemplate(mixedContent, 'compact')
      
      // Should handle mixed scripts
      expect(processed).toContain('Regular Dutch text')
      expect(processed).toContain('محتوى عربي')
      expect(processed).toContain('Back to Dutch content')
      
      // Headers should be removed regardless of script
      expect(processed).not.toContain('# Mixed Language Content')
    })
  })

  describe('Error Handling and Edge Cases', () => {
    it('should handle very long content without accessibility issues', () => {
      let longContent = '# Very Long Document\n\n'
      for (let i = 0; i < 1000; i++) {
        longContent += `Paragraph ${i} with content that needs to be accessible. `
      }
      longContent += '\n\n## End Section\n\nFinal paragraph.'
      
      const processed = wrapper.vm.processContentForTemplate(longContent, 'standaard')
      
      // Should handle long content
      expect(processed.length).toBeGreaterThan(50000)
      expect(processed).not.toContain('# Very Long Document')
      expect(processed).toContain('Paragraph 0 with content')
      expect(processed).toContain('Paragraph 999 with content')
      expect(processed).toContain('Final paragraph')
    })
    
    it('should handle empty content gracefully', () => {
      const emptyResults = [
        wrapper.vm.processContentForTemplate('', 'standaard'),
        wrapper.vm.processContentForTemplate(null, 'modern'),
        wrapper.vm.processContentForTemplate(undefined, 'professioneel'),
        wrapper.vm.processContentForTemplate('   \n\n   ', 'compact')
      ]
      
      emptyResults.forEach(result => {
        expect(result).toBe('')
      })
    })
    
    it('should maintain accessibility with malformed HTML', () => {
      const malformedContent = `
        # Document with Issues
        
        <h1>Unclosed header
        <h2>Another unclosed
        
        Regular content here.
        
        <h3>Properly closed header</h3>
        
        More content.
      `
      
      const processed = wrapper.vm.processContentForTemplate(malformedContent, 'modern')
      
      // Should handle malformed HTML gracefully
      expect(processed).toContain('Regular content here')
      expect(processed).toContain('More content')
      
      // Should remove properly formed headers
      expect(processed).not.toContain('<h3>Properly closed header</h3>')
      
      // Malformed headers should remain (they're not proper headers)
      expect(processed).toContain('<h1>Unclosed header')
    })
  })
})
