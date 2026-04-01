/**
 * Supabase client initialization.
 * Uses env vars from Vite: VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY.
 */
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    'Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY. Check frontend/.env'
  )
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
