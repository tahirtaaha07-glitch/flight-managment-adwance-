-- Run on a schedule. These findings should alert operations; do not silently repair bookings.
WITH seat_counts AS (
    SELECT flight_id, cabin,
           count(*) FILTER (WHERE status = 'HELD') AS held_seats,
           count(*) FILTER (WHERE status = 'BOOKED') AS booked_seats
    FROM seats
    GROUP BY flight_id, cabin
)
SELECT i.flight_id, i.cabin, i.booked AS inventory_booked, coalesce(s.booked_seats, 0) AS physical_booked,
       i.held AS inventory_held, coalesce(s.held_seats, 0) AS physical_held
FROM seat_inventory i
LEFT JOIN seat_counts s ON s.flight_id = i.flight_id AND s.cabin = i.cabin
WHERE i.booked <> coalesce(s.booked_seats, 0)
   OR i.held <> coalesce(s.held_seats, 0)
   OR i.booked + i.held > i.capacity + i.overbooking_buffer;
