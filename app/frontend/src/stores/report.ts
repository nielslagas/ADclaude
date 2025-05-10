import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiClient } from '@/services/api'
import type { Report, ReportCreate, ReportTemplate } from '@/types'

export const useReportStore = defineStore('report', () => {
  // State
  const reports = ref<Report[]>([])
  const currentReport = ref<Report | null>(null)
  const templates = ref<Record<string, ReportTemplate>>({})
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Actions
  const fetchReportTemplates = async () => {
    loading.value = true
    error.value = null
    
    try {
      console.log('Fetching report templates...')
      const response = await apiClient.get('/reports/templates')
      console.log('Report templates response:', response.data)
      
      // If response is empty or not an object, set as empty object
      if (!response.data || typeof response.data !== 'object') {
        console.warn('Empty or invalid templates response, using empty object')
        templates.value = {}
        return {}
      }
      
      templates.value = response.data
      return response.data
    } catch (err) {
      console.error('Error fetching report templates:', err)
      
      // Log more details about the error
      if (err.response) {
        console.error('Error response:', {
          status: err.response.status,
          data: err.response.data,
          headers: err.response.headers
        })
      }
      
      error.value = err.message || 'Failed to fetch report templates'
      
      // Return empty object instead of throwing error
      templates.value = {}
      return {}
    } finally {
      loading.value = false
    }
  }

  const createReport = async (reportData: ReportCreate) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiClient.post('/reports', reportData)
      const newReport = response.data
      reports.value.unshift(newReport)
      return newReport
    } catch (err) {
      console.error('Error creating report:', err)
      error.value = err.message || 'Failed to create report'
      throw err
    } finally {
      loading.value = false
    }
  }

  const fetchReport = async (id: string) => {
    loading.value = true
    error.value = null
    
    try {
      // Add a timestamp to prevent browser caching
      const response = await apiClient.get(`/reports/${id}?_t=${Date.now()}`)
      
      // Log report content for debugging
      console.log('Report fetched successfully:', { 
        id: response.data.id, 
        title: response.data.title, 
        status: response.data.status,
        contentKeys: response.data.content ? Object.keys(response.data.content) : 'none'
      })
      
      // Parse content if it's a string
      if (typeof response.data.content === 'string') {
        try {
          response.data.content = JSON.parse(response.data.content)
        } catch (e) {
          console.error('Failed to parse content string as JSON:', e)
        }
      }
      
      // Clear and set the current report to ensure reactivity
      currentReport.value = null
      currentReport.value = response.data
      return response.data
    } catch (err) {
      console.error(`Error fetching report ${id}:`, err)
      error.value = err.message || 'Failed to fetch report details'
      throw err
    } finally {
      loading.value = false
    }
  }

  const regenerateSection = async (params: { report_id: string, section_id: string }) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiClient.post('/reports/regenerate-section', {
        report_id: params.report_id,
        section_id: params.section_id
      })
      
      return response.data
    } catch (err) {
      console.error(`Error regenerating section ${params.section_id} for report ${params.report_id}:`, err)
      error.value = err.message || 'Failed to regenerate section'
      throw err
    } finally {
      loading.value = false
    }
  }

  const deleteReport = async (id: string) => {
    loading.value = true
    error.value = null
    
    try {
      await apiClient.delete(`/reports/${id}`)
      reports.value = reports.value.filter(r => r.id !== id)
      
      if (currentReport.value && currentReport.value.id === id) {
        currentReport.value = null
      }
    } catch (err) {
      console.error(`Error deleting report ${id}:`, err)
      error.value = err.message || 'Failed to delete report'
      throw err
    } finally {
      loading.value = false
    }
  }

  const reset = () => {
    reports.value = []
    currentReport.value = null
    error.value = null
  }

  // Download report as DOCX
  const downloadReportAsDocx = async (id: string) => {
    loading.value = true
    error.value = null
    
    try {
      // We need to use a different approach for file downloads
      // Create a temporary anchor element to trigger the download
      const downloadUrl = `${apiClient.defaults.baseURL}/reports/${id}/export/docx`
      
      // Get the auth token to include in the request
      let token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJleGFtcGxlX3VzZXJfaWQiLCJuYW1lIjoiVGVzdCBVc2VyIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
      
      try {
        const { data } = await apiClient.get('/auth/me')
        if (data && data.user_id) {
          token = data.token
        }
      } catch (err) {
        console.warn('Using default token for download')
      }
      
      // Create the download element
      const downloadLink = document.createElement('a')
      downloadLink.href = downloadUrl
      
      // Add the auth token as a header
      downloadLink.setAttribute('download', '')
      
      // We need to use a fetch request instead of direct link due to auth token requirement
      const response = await fetch(downloadUrl, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (!response.ok) {
        throw new Error(`Download failed: ${response.status} ${response.statusText}`)
      }
      
      // Get the filename from the Content-Disposition header if available
      let filename = 'report.docx'
      const contentDisposition = response.headers.get('Content-Disposition')
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/)
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1]
        }
      }
      
      // Convert the response to a blob
      const blob = await response.blob()
      
      // Create a URL for the blob
      const url = URL.createObjectURL(blob)
      
      // Set up the download link
      downloadLink.href = url
      downloadLink.download = filename
      
      // Append to body, click, and remove
      document.body.appendChild(downloadLink)
      downloadLink.click()
      document.body.removeChild(downloadLink)
      
      // Clean up the URL object
      setTimeout(() => URL.revokeObjectURL(url), 100)
      
      return true
    } catch (err) {
      console.error(`Error downloading report ${id} as DOCX:`, err)
      error.value = err.message || 'Failed to download report'
      throw err
    } finally {
      loading.value = false
    }
  }

  // Preview function - in a full implementation, this might open a PDF viewer or similar
  const previewReport = async (id: string) => {
    // For now, we'll use a simplified approach to preview the report by
    // showing all sections in a print-friendly format
    
    loading.value = true
    error.value = null
    
    try {
      // Ensure we have the latest report data
      const report = await fetchReport(id)
      
      if (!report.content || Object.keys(report.content).length === 0) {
        throw new Error('No content available to preview')
      }
      
      // Now, we might open a print dialog or a new window with formatted content
      // For this MVP, we'll just return all content and let the component handle display
      return report
    } catch (err) {
      console.error(`Error previewing report ${id}:`, err)
      error.value = err.message || 'Failed to preview report'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    reports,
    currentReport,
    templates,
    loading,
    error,
    fetchReportTemplates,
    createReport,
    fetchReport,
    regenerateSection,
    deleteReport,
    downloadReportAsDocx,
    previewReport,
    reset
  }
})
