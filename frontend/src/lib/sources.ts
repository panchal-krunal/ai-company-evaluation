import { z } from 'zod'

/** A document a figure or finding is traced to. Accepts both backend shapes (url / source_url). */
export const sourceSchema = z
  .object({
    id: z.string().optional(),
    source_document_id: z.string().optional(),
    title: z.string(),
    url: z.string().nullable().optional(),
    source_url: z.string().nullable().optional(),
    publisher: z.string().nullable(),
    is_primary: z.boolean(),
  })
  .transform((s) => ({
    id: s.id ?? s.source_document_id ?? '',
    title: s.title,
    url: s.url ?? s.source_url ?? null,
    publisher: s.publisher,
    isPrimary: s.is_primary,
  }))
export type Source = z.infer<typeof sourceSchema>

export function sourceMap(sources: Source[] | undefined): Map<string, Source> {
  return new Map((sources ?? []).map((s) => [s.id, s]))
}
