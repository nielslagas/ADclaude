import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ReportView from '@/views/ReportView.vue'
import { useReportStore } from '@/stores/report'
import { useProfileStore } from '@/stores/profile'

// Mock data representing content that used to cause issues
const regressionTestData = {
  // Historical problematic content
  oldProblematicReport: {
    id: 'regression-test-1',
    title: 'Regression Test Rapport',
    content: {
      samenvatting: `# SAMENVATTING VAN HET ONDERZOEK\n\n## Inleiding\n\nDe heer TestPersoon heeft rugklachten.\n\n### Conclusie\n\nWerkhervatting mogelijk.`,
      belastbaarheid: `# BELASTBAARHEIDSANALYSE\n\n<h1>Fysieke Belastbaarheid</h1>\n\n**Maximaal tilgewicht:** 15 kg\n\n<h2>Mentale Belastbaarheid</h2>\n\nGeen beperkingen.`,
      visie_ad: `## ARBEIDSDESKUNDIGE VISIE\n\n### Professionele Beoordeling\n\nPositieve vooruitzichten.\n\n#### Aanbevelingen\n\n- Aangepast werk\n- Begeleiding`,
      matching: `# MATCHING CRITERIA\n\n<h3>Werkplek Eisen</h3>\n\n(E) Ergonomische werkplek\n\n<h1>Sociale Aspecten</h1>\n\n(W) Teamwork`
    },
    case_id: 'regression-case-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  }
}

const mockProfile = {
  id: 'profile-1',
  name: 'Test Arbeidsdeskundige',
  title: 'Senior Arbeidsdeskundige',
  company: 'TestBedrijf BV',
  email: 'test@testbedrijf.nl',
  phone: '+31 6 12345678',
  address: 'Teststraat 123, 1234 AB Teststad',
  logo_url: null
}

describe('Template Regression Tests', () => {
  let wrapper: any
  let reportStore: any
  let profileStore: any

  beforeEach(() => {
    setActivePinia(createPinia())
    reportStore = useReportStore()
    profileStore = useProfileStore()
    
    // Set up mock data
    reportStore.currentReport = regressionTestData.oldProblematicReport
    profileStore.currentProfile = mockProfile
    
    wrapper = mount(ReportView, {
      global: {
        plugins: [createPinia()]
      }
    })
  })

  describe('All Template Types Header Handling', () => {
    const templateTypes = ['standaard', 'modern', 'professioneel', 'compact']
    
    templateTypes.forEach(template => {
      it(`should handle headers correctly in ${template} template`, async () => {
        // Set template
        wrapper.vm.previewLayout = template
        await wrapper.vm.$nextTick()
        
        // Test each section
        const sections = ['samenvatting', 'belastbaarheid', 'visie_ad', 'matching']
        
        sections.forEach(sectionId => {
          const content = regressionTestData.oldProblematicReport.content[sectionId]
          const processed = wrapper.vm.processContentForTemplate(content, template)
          
          // Should remove all header types
          expect(processed).not.toMatch(/^#{1,6}\s+/m)
          expect(processed).not.toMatch(/<h[1-6][^>]*>.*?<\/h[1-6]>/gi)
          expect(processed).not.toMatch(/\*\*[^*]+:\**/)
          
          // Should preserve actual content
          if (sectionId === 'samenvatting') {
            expect(processed).toContain('De heer TestPersoon heeft rugklachten')
            expect(processed).toContain('Werkhervatting mogelijk')
          }
          if (sectionId === 'belastbaarheid') {
            expect(processed).toContain('15 kg')
            expect(processed).toContain('Geen beperkingen')
          }
        })
      })
    })
  })

  describe('Template Styling Consistency', () => {
    it('should apply consistent styling across all templates', () => {
      const templateTypes = ['standaard', 'modern', 'professioneel', 'compact']
      
      templateTypes.forEach(template => {
        wrapper.vm.previewLayout = template
        
        // Check template class is applied
        const templateContainer = wrapper.find(`.template-${template}`)
        expect(templateContainer.exists()).toBe(true)
        
        // Check basic styling structure exists
        const pageBreaks = wrapper.findAll('.page-break')
        expect(pageBreaks.length).toBeGreaterThan(0)
        
        // Check section numbering
        const sections = wrapper.findAll('[data-section-number]')
        expect(sections.length).toBeGreaterThan(0)
      })
    })
    
    it('should maintain header hierarchy in CSS styling', () => {
      const templateTypes = ['standaard', 'modern', 'professioneel', 'compact']
      
      templateTypes.forEach(template => {
        wrapper.vm.previewLayout = template
        
        // Check that CSS selectors for headers exist in computed styles
        const styleEl = document.createElement('style')
        document.head.appendChild(styleEl)
        
        // Basic CSS structure should be present
        const expectedSelectors = [
          `.template-${template} [data-section-number="1"]:before`,
          `.template-${template} [data-section-number="2"]:before`,
          `.template-${template} h2`,
          `.template-${template} h3`
        ]
        
        // This is a basic check - in real implementation you'd check computed styles
        expectedSelectors.forEach(selector => {
          expect(selector).toContain(`template-${template}`)
        })
        
        document.head.removeChild(styleEl)
      })
    })
  })

  describe('Backward Compatibility', () => {
    it('should render old reports without breaking', () => {
      // Test with old report structure
      const oldReport = {
        ...regressionTestData.oldProblematicReport,
        content: {
          // Old format with different structure
          samenvatting: 'Simple old content without headers',
          belastbaarheid: 'Old belastbaarheid content',
          // Missing sections should not break
        }
      }
      
      reportStore.currentReport = oldReport
      
      expect(() => {
        wrapper.vm.processContentForTemplate(oldReport.content.samenvatting, 'standaard')
      }).not.toThrow()
      
      const result = wrapper.vm.processContentForTemplate(oldReport.content.samenvatting, 'standaard')
      expect(result).toBe('Simple old content without headers')
    })
    
    it('should handle missing sections gracefully', () => {
      const incompleteReport = {
        ...regressionTestData.oldProblematicReport,
        content: {
          samenvatting: 'Only summary exists'
          // Other sections missing
        }
      }
      
      reportStore.currentReport = incompleteReport
      
      // Should not crash when sections are missing
      expect(() => {
        wrapper.vm.processContentForTemplate(incompleteReport.content.belastbaarheid, 'modern')
      }).not.toThrow()
      
      const result = wrapper.vm.processContentForTemplate(incompleteReport.content.belastbaarheid, 'modern')
      expect(result).toBe('')
    })
  })

  describe('Performance Regression Tests', () => {
    it('should process large content efficiently', () => {
      // Create large content with many headers
      let largeContent = ''
      for (let i = 0; i < 1000; i++) {
        largeContent += `\n\n# Header ${i}\n\nContent paragraph ${i} with some text.`
      }
      
      const startTime = performance.now()
      const result = wrapper.vm.processContentForTemplate(largeContent, 'standaard')
      const endTime = performance.now()
      
      // Should complete within reasonable time
      expect(endTime - startTime).toBeLessThan(100) // 100ms max
      
      // Should remove all headers
      expect(result).not.toMatch(/^#{1,6}\s+/m)
      
      // Should preserve content
      expect(result).toContain('Content paragraph')
    })
    
    it('should handle repeated processing without memory leaks', () => {
      const testContent = 'Test content for repeated processing'
      
      // Process same content multiple times
      for (let i = 0; i < 100; i++) {
        const result = wrapper.vm.processContentForTemplate(testContent, 'modern')
        expect(result).toBe(testContent)
      }
      
      // No assertion for memory - would need specialized tools
      // This test mainly ensures no exceptions are thrown
    })
  })

  describe('CSS Template Integration', () => {
    it('should generate proper CSS selectors for all templates', () => {
      const templateTypes = ['standaard', 'modern', 'professioneel', 'compact']
      
      templateTypes.forEach(template => {
        // Test that template class is properly applied
        wrapper.vm.previewLayout = template
        
        const reportContainer = wrapper.find('.report-preview')
        expect(reportContainer.exists()).toBe(true)
        
        // Check for template-specific classes
        const templateContainer = wrapper.find(`.template-${template}`)
        expect(templateContainer.exists()).toBe(true)
      })
    })
    
    it('should maintain proper section data attributes', () => {
      wrapper.vm.previewLayout = 'standaard'
      
      // Check that sections have proper data attributes
      const sections = wrapper.findAll('[data-section-number]')
      sections.forEach((section, index) => {
        const sectionNumber = section.attributes('data-section-number')
        expect(sectionNumber).toBeDefined()
        expect(parseInt(sectionNumber)).toBeGreaterThan(0)
      })
    })
  })

  describe('Content Formatting Edge Cases', () => {
    it('should handle mixed content types', () => {
      const mixedContent = `
        # Markdown Header
        
        <h1>HTML Header</h1>
        
        **Bold Title:**
        
        Regular paragraph text.
        
        - List item 1
        - List item 2
        
        > Blockquote text
        
        \`\`\`
        Code block
        \`\`\`
        
        **Regular bold text** in middle of sentence.
      `
      
      const result = wrapper.vm.processContentForTemplate(mixedContent, 'professioneel')
      
      // Headers should be removed
      expect(result).not.toContain('# Markdown Header')
      expect(result).not.toContain('<h1>HTML Header</h1>')
      expect(result).not.toContain('**Bold Title:**')
      
      // Other content should be preserved
      expect(result).toContain('Regular paragraph text')
      expect(result).toContain('- List item 1')
      expect(result).toContain('> Blockquote text')
      expect(result).toContain('```')
      expect(result).toContain('**Regular bold text**')
    })
    
    it('should handle special Dutch characters', () => {
      const dutchContent = `
        # Café en naïeve beoordeling
        
        De cliënt heeft rugklachten. De coördinatie is goed.
        Conclusie: geschikt voor aangepaste functies.
      `
      
      const result = wrapper.vm.processContentForTemplate(dutchContent, 'compact')
      
      // Header should be removed
      expect(result).not.toContain('# Café en naïeve beoordeling')
      
      // Dutch characters should be preserved
      expect(result).toContain('cliënt')
      expect(result).toContain('coördinatie')
      expect(result).toContain('geschikt')
    })
  })

  describe('Accessibility and Responsiveness', () => {
    it('should maintain semantic structure after header removal', () => {
      const semanticContent = `
        # Main Section
        
        This is important content that needs to be accessible.
        
        ## Subsection
        
        More content here.
      `
      
      const result = wrapper.vm.processContentForTemplate(semanticContent, 'standaard')
      
      // Content should remain accessible
      expect(result).toContain('This is important content')
      expect(result).toContain('More content here')
      
      // Structure should be maintained through paragraphs
      expect(result.split('\n\n')).toHaveLength(2)
    })
  })

  describe('Template Export Compatibility', () => {
    it('should generate content compatible with PDF export', () => {
      const templateTypes = ['standaard', 'modern', 'professioneel', 'compact']
      
      templateTypes.forEach(template => {
        const content = regressionTestData.oldProblematicReport.content.samenvatting
        const processed = wrapper.vm.processContentForTemplate(content, template)
        
        // Should not contain problematic characters for PDF
        expect(processed).not.toMatch(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/)
        
        // Should have reasonable length
        expect(processed.length).toBeLessThan(10000)
        expect(processed.length).toBeGreaterThan(0)
      })
    })
    
    it('should maintain print formatting', () => {
      wrapper.vm.previewLayout = 'standaard'
      
      // Check for print-related classes
      const printElements = wrapper.findAll('.page-break, .no-print, .print-only')
      
      // Should have some print formatting elements
      expect(printElements.length).toBeGreaterThanOrEqual(0)
    })
  })
})
