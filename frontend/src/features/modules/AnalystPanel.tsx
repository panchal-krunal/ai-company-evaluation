import { MessageSquare, PenLine } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useAnalystName } from '@/lib/analyst'
import { formatDateTime } from '@/lib/format'
import { useAddComment, useComments, useOverride, type Finding } from '../evaluations/api'

const input =
  'w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none'
const primary =
  'rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50'

export function OverridePanel({
  finding,
  evaluationId,
  locked,
}: {
  finding: Finding
  evaluationId: string
  locked: boolean
}) {
  const analyst = useAnalystName()
  const [editing, setEditing] = useState(false)
  const [summary, setSummary] = useState(finding.override_summary ?? '')
  const [reason, setReason] = useState(finding.override_reason ?? '')
  const override = useOverride(finding.id, evaluationId)

  const save = (e: FormEvent) => {
    e.preventDefault()
    override.mutate(
      { actor: analyst, summary: summary.trim(), reason: reason.trim() },
      { onSuccess: () => setEditing(false) },
    )
  }

  return (
    <div className="space-y-3">
      {finding.override_summary && !editing && (
        <div className="rounded-md border border-indigo-200 bg-indigo-50 p-3 text-sm">
          <p className="font-medium">{finding.override_summary}</p>
          <p className="mt-1 text-slate-600">Reason: {finding.override_reason}</p>
        </div>
      )}
      {!editing && !locked && (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setEditing(true)}
            disabled={!analyst}
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50"
          >
            <PenLine className="size-4" aria-hidden />
            {finding.override_summary ? 'Edit override' : 'Override conclusion'}
          </button>
          {finding.override_summary && (
            <button
              type="button"
              disabled={!analyst || override.isPending}
              onClick={() => override.mutate({ actor: analyst, summary: null, reason: null })}
              className="rounded-md px-3 py-1.5 text-sm text-red-700 hover:bg-red-50"
            >
              Remove override
            </button>
          )}
        </div>
      )}
      {editing && (
        <form onSubmit={save} className="space-y-2">
          <label className="block text-sm">
            <span className="mb-1 block font-medium">Analyst conclusion</span>
            <textarea
              required
              rows={3}
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              className={input}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">Reason (required)</span>
            <textarea
              required
              rows={2}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className={input}
            />
          </label>
          {override.error && <p className="text-sm text-red-700">{override.error.message}</p>}
          <div className="flex gap-2">
            <button type="submit" disabled={override.isPending} className={primary}>
              Save override
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="rounded-md px-3 py-1.5 text-sm hover:bg-slate-100"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
      {!analyst && !locked && (
        <p className="text-xs text-amber-800">Enter your name at the top of the page to act.</p>
      )}
    </div>
  )
}

export function CommentsPanel({
  findingId,
  evaluationId,
}: {
  findingId: string
  evaluationId: string
}) {
  const analyst = useAnalystName()
  const comments = useComments(findingId)
  const add = useAddComment(findingId, evaluationId)
  const [body, setBody] = useState('')

  const submit = (e: FormEvent) => {
    e.preventDefault()
    add.mutate({ author: analyst, body: body.trim() }, { onSuccess: () => setBody('') })
  }

  return (
    <div className="space-y-3">
      {comments.data && comments.data.length > 0 ? (
        <ul className="space-y-3">
          {comments.data.map((c) => (
            <li key={c.id} className="text-sm">
              <p className="text-xs text-slate-500">
                <span className="font-medium text-slate-700">{c.author}</span> ·{' '}
                {formatDateTime(c.created_at)}
              </p>
              <p className="whitespace-pre-wrap">{c.body}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">No comments yet.</p>
      )}
      <form onSubmit={submit} className="flex flex-col gap-2 sm:flex-row">
        <label className="sr-only" htmlFor={`comment-${findingId}`}>
          Add a comment
        </label>
        <textarea
          id={`comment-${findingId}`}
          rows={2}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Add a comment…"
          className={input}
        />
        <button
          type="submit"
          disabled={!analyst || !body.trim() || add.isPending}
          className={`${primary} inline-flex items-center gap-1 self-start`}
        >
          <MessageSquare className="size-4" aria-hidden /> Comment
        </button>
      </form>
    </div>
  )
}
