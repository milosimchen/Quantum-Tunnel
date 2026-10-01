// Choices shown on the Account page; values must match the checks in supabase/schema.sql.
export const EXPERIENCE_LEVELS = [
  { value: 'new', label: 'New to quantum computing' },
  { value: 'some', label: 'Know the basics (qubits, gates)' },
  { value: 'comfortable', label: 'Comfortable with circuits and algorithms' },
  { value: 'advanced', label: 'Advanced (grad level or working in the field)' },
]

export const GOALS = [
  { value: 'interview', label: 'Preparing for job interviews' },
  { value: 'coursework', label: 'Coursework or exams' },
  { value: 'research', label: 'Getting into research' },
  { value: 'curious', label: 'Just curious' },
]
