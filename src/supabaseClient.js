import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = 'https://idkghmydocvjhuwtgojh.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imlka2dobXlkb2N2amh1d3Rnb2poIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQyNTU3NzgsImV4cCI6MjA4OTgzMTc3OH0.omQ4zi4gILIk8nQtbYPstcORhEyEhFvKDnFs5qwFlSM';

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
