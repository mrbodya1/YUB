import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = 'https://ohaspovkdvtihosvzpli.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9oYXNwb3ZrZHZ0aWhvc3Z6cGxpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ1NjI1ODEsImV4cCI6MjA5MDEzODU4MX0.5OvphjjVlBP8hXvLMIALsD6pZn5453mkSEpCeOl8280';

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
