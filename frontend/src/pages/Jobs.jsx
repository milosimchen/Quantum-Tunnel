import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import PageHeader from '../PageHeader'
import PrepPanel from '../jobs/PrepPanel'
import { useAuth } from '../AuthContext'
import { apiUrl } from '../api'
import { JOB_STATUSES, loadSavedJobs, removeSavedJob, saveJob, updateSavedJob } from '../progress'

const ROLE_PRESETS = [
  { label: 'All quantum roles', query: '' },
  { label: 'Software', query: 'software' },
  { label: 'Research', query: 'research' },
  { label: 'Hardware', query: 'hardware engineer' },
  { label: 'Internships', query: 'intern' },
]

const SORTS = [
  { value: 'date', label: 'Newest' },
  { value: 'relevance', label: 'Most relevant' },
  { value: 'salary', label: 'Highest salary' },
]

const AGES = [
  { value: '', label: 'Any time' },
  { value: '7', label: 'Past week' },
  { value: '30', label: 'Past month' },
]

function formatSalary(job) {
  const { salary_min: min, salary_max: max } = job
  if (!min && !max) return null
  const fmt = (n) => `$${Math.round(n / 1000)}k`
  const range = min && max && Math.round(min / 1000) !== Math.round(max / 1000) ? `${fmt(min)}–${fmt(max)}` : fmt(min || max)
  return job.salary_is_estimate ? `${range} (est.)` : range
}

function postedAgo(iso) {
  if (!iso) return null
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000)
  if (days <= 0) return 'today'
  if (days === 1) return 'yesterday'
  if (days < 30) return `${days} days ago`
  return `${Math.floor(days / 30)} mo ago`
}

function Jobs() {
  const { user, accountsEnabled } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = searchParams.get('tab') === 'saved' ? 'saved' : 'search'

  const [query, setQuery] = useState('')
  const [location, setLocation] = useState('')
  const [sort, setSort] = useState('date')
  const [maxDaysOld, setMaxDaysOld] = useState('')
  const [quantumTitlesOnly, setQuantumTitlesOnly] = useState(true)
  const [fullTimeOnly, setFullTimeOnly] = useState(false)
  const [page, setPage] = useState(1)

  const [results, setResults] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const [savedJobs, setSavedJobs] = useState([])
  const [prepJob, setPrepJob] = useState(null)

  useEffect(() => {
    loadSavedJobs(user).then(setSavedJobs)
  }, [user])

  async function search(overrides = {}) {
    const params = {
      query,
      location,
      sort,
      max_days_old: maxDaysOld ? Number(maxDaysOld) : null,
      quantum_titles_only: quantumTitlesOnly,
      full_time_only: fullTimeOnly,
      page,
      ...overrides,
    }
    setIsLoading(true)
    setError(null)
    try {
      const response = await fetch(apiUrl('/jobs_search'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      })
      const data = await response.json()
      if (data.success) {
        setResults(data)
        setPage(data.page)
      } else {
        setError(data.message)
        setResults(null)
      }
    } catch (e) {
      setError(`Search failed: ${e.message}`)
      setResults(null)
    } finally {
      setIsLoading(false)
    }
  }

  // Initial search. Later searches are explicit (button, Enter, preset, filter change).
  useEffect(() => {
    search({ page: 1 })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function runSearch(overrides = {}) {
    search({ page: 1, ...overrides })
  }

  const savedIds = new Set(savedJobs.map((j) => j.job_id))

  async function toggleSave(job) {
    if (savedIds.has(job.id)) {
      await removeSavedJob(user, job.id)
      setSavedJobs((current) => current.filter((j) => j.job_id !== job.id))
    } else {
      const row = await saveJob(user, job)
      if (row) setSavedJobs((current) => [row, ...current])
    }
  }

  async function changeSaved(jobId, fields) {
    setSavedJobs((current) => current.map((j) => (j.job_id === jobId ? { ...j, ...fields } : j)))
    await updateSavedJob(user, jobId, fields)
  }

  async function removeSaved(jobId) {
    setSavedJobs((current) => current.filter((j) => j.job_id !== jobId))
    await removeSavedJob(user, jobId)
  }

  return (
    <div className="app-shell">
      <PageHeader subtitle="opportunities" />

      <section className="module-intro">
        <h1 className="module-title">Opportunities</h1>
        <p className="module-lede">
          Live quantum computing job listings. Save the ones you like, track where you are with each, and get a prep plan
          built from Study lessons and Interview Prep challenges that match the role.
        </p>
        {!user && accountsEnabled && (
          <p className="module-note">
            Saved jobs are kept in this browser. <Link to="/login">Sign in</Link> to keep them across devices.
          </p>
        )}
      </section>

      <div className="tab-row" role="tablist">
        <button role="tab" aria-selected={tab === 'search'} className={`tab ${tab === 'search' ? 'tab-active' : ''}`} onClick={() => setSearchParams({})}>
          Search
        </button>
        <button role="tab" aria-selected={tab === 'saved'} className={`tab ${tab === 'saved' ? 'tab-active' : ''}`} onClick={() => setSearchParams({ tab: 'saved' })}>
          Saved <span className="tab-count">{savedJobs.length}</span>
        </button>
      </div>

      {tab === 'saved' ? (
        <SavedJobs jobs={savedJobs} onChange={changeSaved} onRemove={removeSaved} onPrep={(job) => setPrepJob({ ...job, id: job.job_id })} />
      ) : (
        <>
          <form className="jobs-filters" onSubmit={(e) => { e.preventDefault(); runSearch() }}>
            <div className="jobs-search-row">
              <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Keywords, e.g. qiskit, error correction, physicist" aria-label="Keywords" />
              <input type="text" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="City, state or zip" aria-label="Location" className="jobs-location" />
              <button className="btn" type="submit" disabled={isLoading}>{isLoading ? 'searching…' : 'search'}</button>
            </div>

            <div className="chip-row">
              {ROLE_PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  className={`filter-chip ${query === preset.query ? 'filter-chip-active' : ''}`}
                  onClick={() => { setQuery(preset.query); runSearch({ query: preset.query }) }}
                >
                  {preset.label}
                </button>
              ))}
            </div>

            <div className="jobs-filter-row">
              <label className="field-label">
                sort{' '}
                <select value={sort} onChange={(e) => { setSort(e.target.value); runSearch({ sort: e.target.value }) }}>
                  {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </label>
              <label className="field-label">
                posted{' '}
                <select value={maxDaysOld} onChange={(e) => { setMaxDaysOld(e.target.value); runSearch({ max_days_old: e.target.value ? Number(e.target.value) : null }) }}>
                  {AGES.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
                </select>
              </label>
              <label className="toggle">
                <input type="checkbox" checked={quantumTitlesOnly} onChange={(e) => { setQuantumTitlesOnly(e.target.checked); runSearch({ quantum_titles_only: e.target.checked }) }} />
                "Quantum" in job title
              </label>
              <label className="toggle">
                <input type="checkbox" checked={fullTimeOnly} onChange={(e) => { setFullTimeOnly(e.target.checked); runSearch({ full_time_only: e.target.checked }) }} />
                Full-time only
              </label>
            </div>
          </form>

          {error && <p className="error-text">{error}</p>}

          {isLoading && !results ? (
            <p className="empty-state">Searching…</p>
          ) : results && results.jobs.length === 0 ? (
            <p className="empty-state">No matches. Try fewer keywords, a wider location, or turn off "Quantum in job title".</p>
          ) : results && (
            <>
              <p className="jobs-count">
                {results.total_count.toLocaleString()} matches · page {results.page} of {results.total_pages.toLocaleString()}
                <span className="jobs-source"> · listings via Adzuna; salaries marked "est." are Adzuna's estimates</span>
              </p>
              <div className={`job-grid ${isLoading ? 'is-loading' : ''}`}>
                {results.jobs.map((job) => (
                  <JobCard key={job.id} job={job} isSaved={savedIds.has(job.id)} onToggleSave={() => toggleSave(job)} onPrep={() => setPrepJob(job)} />
                ))}
              </div>
              <div className="pager">
                <button className="btn" disabled={isLoading || results.page <= 1} onClick={() => search({ page: results.page - 1 })}>← previous</button>
                <button className="btn" disabled={isLoading || results.page >= results.total_pages} onClick={() => search({ page: results.page + 1 })}>next →</button>
              </div>
            </>
          )}
        </>
      )}

      {prepJob && <PrepPanel job={prepJob} onClose={() => setPrepJob(null)} />}
    </div>
  )
}

function JobCard({ job, isSaved, onToggleSave, onPrep }) {
  const salary = formatSalary(job)
  return (
    <article className="job-card">
      <div className="job-card-head">
        <p className="job-title">{job.title}</p>
        <button className={`save-btn ${isSaved ? 'save-btn-on' : ''}`} onClick={onToggleSave} aria-pressed={isSaved} aria-label={isSaved ? 'Remove from saved' : 'Save job'}>
          {isSaved ? '★ saved' : '☆ save'}
        </button>
      </div>
      <span className="job-company">{job.company}</span>
      <span className="job-location">{job.location}{job.posted && ` · ${postedAgo(job.posted)}`}</span>
      {salary && <span className="job-salary">{salary}</span>}
      <p className="job-description">{job.description}</p>
      <div className="job-actions">
        <button className="btn btn-teal" onClick={onPrep}>prep me for this</button>
        <a className="job-apply-link" href={job.apply_url} target="_blank" rel="noopener noreferrer">view posting ↗</a>
      </div>
    </article>
  )
}

function SavedJobs({ jobs, onChange, onRemove, onPrep }) {
  if (jobs.length === 0) {
    return <p className="empty-state">No saved jobs yet. Use ☆ save on any listing in Search.</p>
  }
  return (
    <div className="saved-jobs">
      {JOB_STATUSES.map((status) => {
        const group = jobs.filter((j) => j.status === status.value)
        if (group.length === 0) return null
        return (
          <section key={status.value} className="saved-group">
            <h2 className="saved-group-title">{status.label} <span className="tab-count">{group.length}</span></h2>
            {group.map((job) => (
              <article key={job.job_id} className="saved-job">
                <div className="saved-job-main">
                  <p className="job-title">{job.title}</p>
                  <span className="job-company">{job.company}</span>
                  {job.location && <span className="job-location"> · {job.location}</span>}
                </div>
                <div className="saved-job-controls">
                  <select value={job.status} onChange={(e) => onChange(job.job_id, { status: e.target.value })} aria-label="Status">
                    {JOB_STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                  </select>
                  <button className="btn btn-teal" onClick={() => onPrep(job)}>prep</button>
                  {job.apply_url && <a className="job-apply-link" href={job.apply_url} target="_blank" rel="noopener noreferrer">posting ↗</a>}
                  <button className="link-btn" onClick={() => onRemove(job.job_id)}>remove</button>
                </div>
                <textarea
                  className="saved-job-notes"
                  defaultValue={job.notes || ''}
                  placeholder="Notes: contacts, deadlines, what to prepare…"
                  onBlur={(e) => e.target.value !== (job.notes || '') && onChange(job.job_id, { notes: e.target.value })}
                  rows={2}
                />
              </article>
            ))}
          </section>
        )
      })}
    </div>
  )
}

export default Jobs
