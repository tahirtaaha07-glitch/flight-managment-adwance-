-- Bind $1 to outbox id. Only mark complete after the downstream action succeeds.
UPDATE automation_outbox
SET status = 'COMPLETED',
    lease_until = NULL,
    last_error = NULL
WHERE id = $1
  AND status = 'PROCESSING';
