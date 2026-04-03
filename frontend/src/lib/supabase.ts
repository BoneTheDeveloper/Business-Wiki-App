/**
 * Supabase client initialization.
 * PKCE flow with manual code exchange — init() controls timing to avoid
 * SIGNED_IN events firing before onAuthStateChange listener is registered.
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
    detectSessionInUrl: false, // init() handles PKCE exchange to control timing
    persistSession: true,
    autoRefreshToken: true,
  },
})
