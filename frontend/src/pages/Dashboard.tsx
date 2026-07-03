import { Link } from 'react-router-dom'

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-card p-8 shadow-sm">
        <h1 className="text-2xl font-semibold text-heading">AI Testing Platform</h1>
        <p className="mt-3 max-w-2xl text-sm text-slate-600">
          Run intelligent AI-powered website tests against any public URL.
          Results include website analysis, intelligent planning, execution, evidence collection,
          and AI diagnosis.
        </p>
        <Link
          to="/run-test"
          className="mt-6 inline-flex rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white transition hover:bg-primary/90"
        >
          Run New Test
        </Link>
      </div>

      <div className="rounded-xl border border-slate-200 bg-card p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-heading">Recent activity</h3>
        <p className="mt-2 text-sm text-slate-500">
          Your recent test runs will appear here.
        </p>
      </div>
    </div>
  )
}
