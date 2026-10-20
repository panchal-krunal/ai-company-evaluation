import { ClaimList } from './Evidence'
import type { ResearchData } from './schemas'

export function ResearchView({ data }: { data: ResearchData }) {
  return (
    <div className="space-y-6">
      <p className="text-xs text-slate-500">
        {data.claims.length} claims from {data.passages_considered} retrieved passages
        {data.unsupported_claims > 0 &&
          ` · ${data.unsupported_claims} unsupported (struck through)`}
      </p>
      <ClaimList claims={data.claims} />
      {data.open_questions.length > 0 && (
        <div>
          <h3 className="mb-1 text-sm font-semibold">Open questions for the analyst</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
            {data.open_questions.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
