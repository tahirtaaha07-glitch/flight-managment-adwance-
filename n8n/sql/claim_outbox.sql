-- Execute as one Postgres node transaction. The lease makes a crashed worker retryable.
WITH claimed AS (
    SELECT id
    FROM automation_outbox
    WHERE status = 'PENDING'
      AND available_at <= now()
    ORDER BY created_at, id
    FOR UPDATE SKIP LOCKED
    LIMIT 25
)
UPDATE automation_outbox AS job
SET status = 'PROCESSING',
    lease_until = now() + interval '5 minutes',
    attempts = attempts + 1
FROM claimed
WHERE job.id = claimed.id
RETURNING job.id, job.topic, job.payload, job.attempts, job.lease_until;
