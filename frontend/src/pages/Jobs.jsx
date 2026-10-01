import { useState, useEffect } from 'react'
import PageHeader from '../PageHeader'
import { apiUrl } from '../api'

function formatSalary(min, max) {
  if (!min && !max) return null
  const fmt = (n) => `$${Math.round(n / 1000)}k`
  if (min && max && min !== max) return `${fmt(min)} – ${fmt(max)}`
  return fmt(min || max)
}

function Jobs() {
  const [query, setQuery] = useState('quantum computing')
  const [jobs, setJobs] = useState([])
  const [totalCount, setTotalCount] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  async function search() {
    setIsLoading(true)
    setError(null)
    try {
      const response = await fetch(apiUrl('/jobs_search'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, location: '', page: 1 }),
      })
      const data = await response.json()
      if (data.success) {
        setJobs(data.jobs)
        setTotalCount(data.total_count)
      } else {
        setError(data.message)
        setJobs([])
      }
    } catch (e) {
      setError(`Search failed: ${e.message}`)
      setJobs([])
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    search()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="app-shell">
      <PageHeader subtitle="opportunities" />

      <div className="jobs-search-row">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && search()}
          placeholder="Search job titles or keywords..."
        />
        <button className="btn" onClick={search} disabled={isLoading}>
          {isLoading ? 'searching...' : 'search'}
        </button>
      </div>

      {error && <p className="error-text">{error}</p>}

      {!error && !isLoading && (
        <p className="jobs-count">{totalCount.toLocaleString()} total matches — showing {jobs.length}</p>
      )}

      {isLoading ? (
        <p className="empty-state">Searching...</p>
      ) : jobs.length === 0 && !error ? (
        <p className="empty-state">No results.</p>
      ) : (
        <div className="job-grid">
          {jobs.map((job) => (
            <div className="job-card" key={job.id}>
              <p className="job-title">{job.title}</p>
              <span className="job-company">{job.company}</span>
              <span className="job-location">{job.location}</span>
              {formatSalary(job.salary_min, job.salary_max) && (
                <span className="job-salary">{formatSalary(job.salary_min, job.salary_max)}</span>
              )}
              <p className="job-description">{job.description}</p>
                <a
                className="job-apply-link"
                href={job.apply_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                apply →
              </a>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default Jobs