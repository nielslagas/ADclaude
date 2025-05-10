import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { supabase } from '@/services/supabase'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const isLoggedIn = computed(() => !!user.value)

  // Actions
  const initialize = async () => {
    try {
      // Check if there's an active session
      const { data, error: sessionError } = await supabase.auth.getSession()
      
      if (sessionError) throw sessionError
      
      if (data?.session?.user) {
        user.value = data.session.user
      } else {
        user.value = null
      }

      // Set up auth state change listener
      supabase.auth.onAuthStateChange((event, session) => {
        if (event === 'SIGNED_IN' && session) {
          user.value = session.user
        } else if (event === 'SIGNED_OUT') {
          user.value = null
        }
      })
    } catch (err) {
      console.error('Auth initialization error:', err)
      error.value = err.message || 'Authentication error'
    }
  }

  const login = async (email: string, password: string) => {
    loading.value = true
    error.value = null
    
    try {
      const { data, error: authError } = await supabase.auth.signInWithPassword({
        email,
        password
      })
      
      if (authError) throw authError
      
      user.value = data.user
      return data
    } catch (err) {
      console.error('Login error:', err)
      error.value = err.message || 'Failed to login'
      throw err
    } finally {
      loading.value = false
    }
  }

  const logout = async () => {
    loading.value = true
    error.value = null
    
    try {
      const { error: authError } = await supabase.auth.signOut()
      if (authError) throw authError
      
      user.value = null
    } catch (err) {
      console.error('Logout error:', err)
      error.value = err.message || 'Failed to logout'
      throw err
    } finally {
      loading.value = false
    }
  }

  const register = async (email: string, password: string) => {
    loading.value = true
    error.value = null
    
    try {
      const { data, error: authError } = await supabase.auth.signUp({
        email,
        password
      })
      
      if (authError) throw authError
      
      return data
    } catch (err) {
      console.error('Registration error:', err)
      error.value = err.message || 'Failed to register'
      throw err
    } finally {
      loading.value = false
    }
  }

  // Initialize on store creation - wrap in setTimeout to ensure it runs after Vue app is mounted
  setTimeout(() => {
    initialize()
  }, 100)

  return {
    user,
    loading,
    error,
    isLoggedIn,
    login,
    logout,
    register,
    initialize
  }
})
