-- Bind $1 to outbox id, $2 to error text. Backoff and dead-letter after 8 attempts.
UPDATE automation_outbox
SET status = CASE WHEN attempts >= 8 THEN 'DEAD_LETTER'::workflow_status ELSE 'PENDING'::workflow_status END,
    available_at = now() + make_interval(secs => LEAST(3600, power(2, attempts)::int * 15)),
    lease_until = NULL,
    last_error = $2
WHERE id = $1
  AND status = 'PROCESSING';
