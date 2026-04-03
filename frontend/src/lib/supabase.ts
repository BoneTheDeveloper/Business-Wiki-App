/**
 * Supabase client initialization.
 * PKCE flow with detectSessionInUrl: Supabase auto-exchanges ?code= on redirect.
 * No manual exchangeCodeForSession() needed.
 */
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    'Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY. Check frontend/.env'
  )
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    flowType: 'pkce',
    detectSessionInUrl: true, // Let Supabase auto-handle PKCE exchange from ?code=
    persistSession: true,
    autoRefreshToken: true,
  },
})
