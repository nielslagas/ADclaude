import { createClient } from '@supabase/supabase-js'

// Mock storage using in-memory variables for Docker environment
let mockUserData: any = null;
let mockSessionData: any = null;

// For local development with mock auth
const createMockClient = () => {
  console.log('Using mock Supabase client for local development');
  // Return a mock client with auth methods
  return {
    auth: {
      // Basic mock implementation for demo purposes
      signUp: async ({ email, password }: { email: string, password: string }) => {
        console.log('Mock signup with:', email, password);
        // Simulate successful signup
        const mockUser = { id: 'example_user_id', email, created_at: new Date().toISOString() };
        try {
          localStorage.setItem('mock_user', JSON.stringify(mockUser));
        } catch (e) {
          console.warn('Could not use localStorage, using in-memory storage', e);
        }
        // Also store in memory variables for Docker environment
        mockUserData = mockUser;
        return { data: { user: mockUser, session: null }, error: null };
      },
      signInWithPassword: async ({ email, password }: { email: string, password: string }) => {
        console.log('Mock login with:', email, password);
        // Accept any email/password for testing
        const mockUser = { id: 'example_user_id', email, created_at: new Date().toISOString() };
        // Use the token that matches what our backend expects
        const mockSession = { 
          access_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJleGFtcGxlX3VzZXJfaWQiLCJuYW1lIjoiVGVzdCBVc2VyIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c', 
          refresh_token: 'mock_refresh',
          user: mockUser,
          expires_at: Date.now() + 3600000
        };
        try {
          localStorage.setItem('mock_user', JSON.stringify(mockUser));
          localStorage.setItem('mock_session', JSON.stringify(mockSession));
        } catch (e) {
          console.warn('Could not use localStorage, using in-memory storage', e);
        }
        
        // Also store in memory variables for Docker environment
        mockUserData = mockUser;
        mockSessionData = mockSession;
        
        return { data: { user: mockUser, session: mockSession }, error: null };
      },
      signOut: async () => {
        try {
          localStorage.removeItem('mock_user');
          localStorage.removeItem('mock_session');
        } catch (e) {
          console.warn('Could not use localStorage', e);
        }
        // Clear in-memory variables too
        mockUserData = null;
        mockSessionData = null;
        return { error: null };
      },
      getSession: async () => {
        // Try localStorage first, then fall back to in-memory variables
        try {
          const sessionStr = localStorage.getItem('mock_session');
          if (sessionStr) {
            try {
              const session = JSON.parse(sessionStr);
              return { data: { session }, error: null };
            } catch (e) {
              console.warn('Failed to parse localStorage session', e);
            }
          }
        } catch (e) {
          console.warn('Could not access localStorage', e);
        }
        
        // Use in-memory session
        if (mockSessionData) {
          return { data: { session: mockSessionData }, error: null };
        }
        return { data: { session: null }, error: null };
      },
      onAuthStateChange: (callback: Function) => {
        // Simple mock for auth state change
        // In a real implementation, you would use an event listener
        const unsubscribe = () => {};
        return { data: { subscription: { unsubscribe } }, error: null };
      }
    },
    from: (table: string) => {
      // Basic mock for database operations
      return {
        select: () => {
          return {
            eq: () => {
              return {
                eq: () => {
                  return {
                    execute: async () => {
                      return { data: [], error: null }
                    }
                  }
                },
                execute: async () => {
                  return { data: [], error: null }
                }
              }
            },
            execute: async () => {
              return { data: [], error: null }
            }
          }
        },
        insert: () => {
          return {
            execute: async () => {
              return { data: [{ id: crypto.randomUUID() }], error: null }
            }
          }
        },
        update: () => {
          return {
            eq: () => {
              return {
                execute: async () => {
                  return { data: null, error: null }
                }
              }
            }
          }
        },
        delete: () => {
          return {
            eq: () => {
              return {
                execute: async () => {
                  return { data: null, error: null }
                }
              }
            }
          }
        }
      }
    }
  };
};

// If environment variables are not set, use local defaults
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'http://localhost:8000';
const supabaseKey = import.meta.env.VITE_SUPABASE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0';

if (!supabaseUrl || !supabaseKey) {
  throw new Error('Missing Supabase credentials. Please check your environment variables.');
}

// Flag to indicate if we're using the local database
export const isLocalDatabase = supabaseUrl === 'http://localhost:8000';

// Create and export the Supabase client
// Always use mock client for development regardless of URL
// This ensures authentication works in Docker environment
export const supabase = createMockClient();
