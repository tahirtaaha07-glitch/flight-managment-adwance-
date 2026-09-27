# n8n workflow setup

These are production-oriented workflow templates, not imported/credentialed workflow exports. Configure a PostgreSQL credential with access to the flight-operations database and Gmail/Pinecone credentials in n8n's credential store. Never place API keys or database passwords in workflow JSON.

## Ownership contract

- FastAPI is the only writer for `flights`, `seat_inventory`, `seats`, `seat_holds`, `bookings`, `refunds`, `travel_credits`, `approvals`, `audit_events`, and `idempotency_records`.
- n8n owns `automation_runs`, `policy_documents`, `fraud_scores`, and Pinecone index maintenance metadata.
- FastAPI emits `automation_outbox` rows in the business transaction. n8n may claim and update outbox status, but must not edit booking, seat, or flight ledgers directly.
- Waitlist promotion uses FastAPI's row-locked promotion endpoint; n8n triggers it on a schedule with an automation-worker identity. This prevents bypassing the cancellation/seat locking transaction.

## Change detection and locking

Poll `automation_outbox` on a short interval and use `sql/claim_outbox.sql` in a transaction. `FOR UPDATE SKIP LOCKED`, a bounded lease, exponential retry, and a dead-letter state survive worker restarts. PostgreSQL `NOTIFY` is optional wake-up optimization only; it is not the durable queue.

Use `sql/complete_outbox.sql` only after downstream work succeeds and `sql/retry_outbox.sql` on recoverable failure. Schedule `sql/reconciliation.sql`; alert on mismatched inventory/physical-seat counts rather than guessing a repair.

## Required scheduled jobs

1. Waitlist promotion: every minute, call `POST /api/automations/waitlist/promote` with the automation worker bearer token.
2. Check-in reminders, refund escalation, price-drop alerts, daily/weekly operations reports, fraud scans, historical batch review, and policy ingestion: call `POST /api/automations/{workflow}` on the configured schedule. Outbox events are the hand-off to email or indexing nodes.
3. Process notification outbox topics with Gmail. Suppress cancelled flights and deduplicate by booking/notification type.
4. Only send `email.approved_rag_response` after the corresponding `rag_response` approval is `approved`; rejected/pending drafts must never reach Gmail.
5. Pinecone ingestion must version/checksum policy documents before upsert. Fraud embeddings are signals for review, not automatic adverse action.

All workflow nodes must be idempotent by outbox ID. Set node error branches to update retry/dead-letter state, and keep raw customer data out of execution logs.
