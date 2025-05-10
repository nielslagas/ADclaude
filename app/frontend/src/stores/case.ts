import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiClient } from '@/services/api'
import type { Case, CaseCreate, Document, Report } from '@/types'

export const useCaseStore = defineStore('case', () => {
  // State
  const cases = ref<Case[]>([])
  const currentCase = ref<Case | null>(null)
  const documents = ref<Document[]>([])
  const reports = ref<Report[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const getCaseById = computed(() => {
    return (id: string) => cases.value.find(c => c.id === id)
  })

  // Actions
  const fetchCases = async () => {
    loading.value = true
    error.value = null
    
    try {
      console.log('Fetching cases...')
      const response = await apiClient.get('/cases/')
      console.log('Cases response:', response.data)
      cases.value = response.data || []
      
      if (!response.data || response.data.length === 0) {
        console.log('No cases found or empty response')
      }
    } catch (err) {
      console.error('Error fetching cases:', err)
      if (err.response) {
        console.error('Error response:', {
          status: err.response.status,
          statusText: err.response.statusText,
          data: err.response.data
        })
      }
      error.value = 'Er is een fout opgetreden bij het ophalen van cases.'
      
      // Provide empty array instead of throwing to handle error gracefully
      cases.value = []
    } finally {
      loading.value = false
    }
  }

  const fetchCase = async (id: string) => {
    loading.value = true
    error.value = null
    
    try {
      console.log(`Fetching case with ID: ${id}`)
      const response = await apiClient.get(`/cases/${id}`)
      console.log('Case data received:', response.data)
      
      if (!response.data) {
        console.error('Empty response data when fetching case')
        throw new Error('Geen case gegevens ontvangen')
      }
      
      currentCase.value = response.data
      return response.data
    } catch (err) {
      console.error(`Error fetching case ${id}:`, err)
      
      // Log detailed error information
      if (err.response) {
        console.error('Error response details:', {
          status: err.response.status,
          statusText: err.response.statusText,
          data: err.response.data,
          headers: err.response.headers
        })
      } else if (err.request) {
        console.error('No response received:', err.request)
      }
      
      console.error('Full error object:', JSON.stringify(err, null, 2))
      error.value = err.message || 'Failed to fetch case details'
      throw err
    } finally {
      loading.value = false
    }
  }

  const createCase = async (caseData: CaseCreate) => {
    loading.value = true
    error.value = null
    
    try {
      console.log('Creating case with data:', caseData)
      const response = await apiClient.post('/cases/', caseData)
      console.log('Create case response:', response.data)
      const newCase = response.data
      cases.value.unshift(newCase)
      return newCase
    } catch (err) {
      console.error('Error creating case:', err)
      if (err.response) {
        console.error('Error response:', {
          status: err.response.status,
          statusText: err.response.statusText,
          data: err.response.data
        })
      }
      error.value = 'Er is een fout opgetreden bij het aanmaken van de case.'
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateCase = async (id: string, caseData: Partial<CaseCreate>) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiClient.patch(`/cases/${id}`, caseData)
      const updatedCase = response.data
      
      // Update in the cases array
      const index = cases.value.findIndex(c => c.id === id)
      if (index !== -1) {
        cases.value[index] = updatedCase
      }
      
      // Update currentCase if it's the one being edited
      if (currentCase.value && currentCase.value.id === id) {
        currentCase.value = updatedCase
      }
      
      return updatedCase
    } catch (err) {
      console.error(`Error updating case ${id}:`, err)
      error.value = err.message || 'Failed to update case'
      throw err
    } finally {
      loading.value = false
    }
  }

  const deleteCase = async (id: string) => {
    loading.value = true
    error.value = null
    
    try {
      await apiClient.delete(`/cases/${id}`)
      cases.value = cases.value.filter(c => c.id !== id)
      
      if (currentCase.value && currentCase.value.id === id) {
        currentCase.value = null
      }
    } catch (err) {
      console.error(`Error deleting case ${id}:`, err)
      error.value = err.message || 'Failed to delete case'
      throw err
    } finally {
      loading.value = false
    }
  }

  const fetchCaseDocuments = async (caseId: string) => {
    loading.value = true
    error.value = null
    
    try {
      // Add a timestamp to prevent browser caching
      const response = await apiClient.get(`/documents/case/${caseId}?_t=${Date.now()}`)
      
      // Log the response data for debugging
      console.log(`Fetched ${response.data.length} documents for case ${caseId}:`, 
        response.data.map(d => ({id: d.id, filename: d.filename, status: d.status})));
      
      documents.value = response.data
      return response.data
    } catch (err) {
      console.error(`Error fetching documents for case ${caseId}:`, err)
      error.value = err.message || 'Failed to fetch documents'
      throw err
    } finally {
      loading.value = false
    }
  }

  const fetchCaseReports = async (caseId: string) => {
    loading.value = true
    error.value = null
    
    try {
      // Add a timestamp to prevent browser caching
      const response = await apiClient.get(`/reports/case/${caseId}?_t=${Date.now()}`)
      
      // Log the response data for debugging
      console.log(`Fetched ${response.data.length} reports for case ${caseId}:`, 
        response.data.map(r => ({id: r.id, title: r.title, status: r.status})));
      
      // Update the reports with new data
      reports.value = response.data
      return response.data
    } catch (err) {
      console.error(`Error fetching reports for case ${caseId}:`, err)
      error.value = err.message || 'Failed to fetch reports'
      throw err
    } finally {
      loading.value = false
    }
  }

  const reset = () => {
    cases.value = []
    currentCase.value = null
    documents.value = []
    reports.value = []
    error.value = null
  }

  return {
    cases,
    currentCase,
    documents,
    reports,
    loading,
    error,
    getCaseById,
    fetchCases,
    fetchCase,
    createCase,
    updateCase,
    deleteCase,
    fetchCaseDocuments,
    fetchCaseReports,
    reset
  }
})
