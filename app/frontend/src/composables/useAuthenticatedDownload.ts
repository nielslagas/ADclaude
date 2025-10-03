import { supabase } from '@/services/supabase';
import { getFullApiUrl } from '@/services/api';

export const useAuthenticatedDownload = () => {
  
  const getAuthToken = async (): Promise<string | null> => {
    try {
      const { data } = await supabase.auth.getSession();
      const token = data?.session?.access_token;
      
      if (token) {
        return token;
      }
      
      // Fallback to development token (same as in api.ts)
      return 'eyJhbGciOiAibm9uZSIsICJ0eXAiOiAiSldUIn0.eyJzdWIiOiAiOTI3MzQyYWQtZDVhMC00Zjg4LTliYzMtODBmNzcwMjA3M2UwIiwgIm5hbWUiOiAiTmllbHMgTGFnYXMiLCAiaWF0IjogMTUxNjIzOTAyMn0.';
    } catch (error) {
      console.error('Error getting auth token:', error);
      // Return fallback token
      return 'eyJhbGciOiAibm9uZSIsICJ0eXAiOiAiSldUIn0.eyJzdWIiOiAiOTI3MzQyYWQtZDVhMC00Zjg4LTliYzMtODBmNzcwMjA3M2UwIiwgIm5hbWUiOiAiTmllbHMgTGFnYXMiLCAiaWF0IjogMTUxNjIzOTAyMn0.';
    }
  };

  const downloadFile = async (
    url: string, 
    filename: string, 
    queryParams: Record<string, string> = {}
  ): Promise<void> => {
    try {
      const token = await getAuthToken();
      
      if (!token) {
        throw new Error('No authentication token available');
      }

      // Build URL with query parameters
      const fullApiUrl = getFullApiUrl(url);
      const urlObj = new URL(fullApiUrl);
      Object.entries(queryParams).forEach(([key, value]) => {
        urlObj.searchParams.set(key, value);
      });
      
      // Add token to URL for download links (since we can't set headers on anchor links)
      urlObj.searchParams.set('token', token);
      
      const finalUrl = urlObj.toString();

      // Fetch the file with authentication
      const response = await fetch(finalUrl, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Download failed: ${response.status} ${response.statusText} - ${errorText}`);
      }

      // Get the blob
      const blob = await response.blob();
      
      // Create download link
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      link.style.display = 'none';
      
      // Trigger download
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Cleanup
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error('Download failed:', error);
      throw error;
    }
  };

  const buildAuthenticatedUrl = async (
    path: string,
    queryParams: Record<string, string> = {}
  ): Promise<string> => {
    const token = await getAuthToken();
    const url = new URL(getFullApiUrl(path));
    
    // Add query parameters
    Object.entries(queryParams).forEach(([key, value]) => {
      url.searchParams.set(key, value);
    });
    
    // Add token for authentication
    if (token) {
      url.searchParams.set('token', token);
    }
    
    return url.toString();
  };

  return {
    downloadFile,
    buildAuthenticatedUrl,
    getAuthToken
  };
};