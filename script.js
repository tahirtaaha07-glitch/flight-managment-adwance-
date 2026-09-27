document.addEventListener("DOMContentLoaded", () => {
  const STORE_KEY = "northstar-flight-ops-demo-v1";
  const main = document.querySelector("#main-content");
  const modalBackdrop = document.querySelector("#modal-backdrop");
  const modal = document.querySelector("#modal");
  const toastRegion = document.querySelector("#toast-region");
  const today = new Date();
  const localDate = (offset = 0, hour = 9) => {
    const date = new Date(today);
    date.setDate(date.getDate() + offset);
    date.setHours(hour, 0, 0, 0);
    const pad = (value) => String(value).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  };
  const isoDay = (value) => String(value || "").slice(0, 10);
  const uid = (prefix) => `${prefix}-${Math.random().toString(36).slice(2, 8).toUpperCase()}`;
  const initialState = () => ({
    role: "super-admin",
    currency: "USD",
    locale: "en-US",
    flights: [
      { id: "FL-101", number: "NS204", origin: "London (LHR)", destination: "Dubai (DXB)", originCode: "LHR", destinationCode: "DXB", departure: localDate(1, 9), arrival: localDate(1, 19), capacity: 100, seats: { First: 20, Business: 30, Economy: 50 }, prices: { First: 1840, Business: 980, Economy: 420 }, status: "Scheduled", overbooking: { First: 0, Business: 0, Economy: 0 }, cutoffs: { First: 2, Business: 3, Economy: 6 }, timezone: "Europe/London" },
      { id: "FL-102", number: "NS318", origin: "New York (JFK)", destination: "Paris (CDG)", originCode: "JFK", destinationCode: "CDG", departure: localDate(1, 14), arrival: localDate(1, 22), capacity: 120, seats: { First: 12, Business: 28, Economy: 80 }, prices: { First: 1520, Business: 760, Economy: 360 }, status: "Scheduled", overbooking: { First: 0, Business: 0, Economy: 0 }, cutoffs: { First: 2, Business: 3, Economy: 6 }, timezone: "America/New_York" },
      { id: "FL-103", number: "NS611", origin: "Dubai (DXB)", destination: "Singapore (SIN)", originCode: "DXB", destinationCode: "SIN", departure: localDate(2, 8), arrival: localDate(2, 16), capacity: 90, seats: { First: 10, Business: 20, Economy: 60 }, prices: { First: 1290, Business: 610, Economy: 285 }, status: "Scheduled", overbooking: { First: 0, Business: 0, Economy: 0 }, cutoffs: { First: 2, Business: 3, Economy: 6 }, timezone: "Asia/Dubai" },
      { id: "FL-104", number: "NS407", origin: "Paris (CDG)", destination: "Rome (FCO)", originCode: "CDG", destinationCode: "FCO", departure: localDate(0, 11), arrival: localDate(0, 13), capacity: 72, seats: { First: 8, Business: 16, Economy: 48 }, prices: { First: 580, Business: 310, Economy: 145 }, status: "Boarding", overbooking: { First: 0, Business: 0, Economy: 0 }, cutoffs: { First: 2, Business: 3, Economy: 6 }, timezone: "Europe/Paris" },
      { id: "FL-105", number: "NS520", origin: "London (LHR)", destination: "Rome (FCO)", originCode: "LHR", destinationCode: "FCO", departure: localDate(3, 10), arrival: localDate(3, 14), capacity: 88, seats: { First: 8, Business: 20, Economy: 60 }, prices: { First: 650, Business: 340, Economy: 165 }, status: "Scheduled", overbooking: { First: 0, Business: 0, Economy: 0 }, cutoffs: { First: 2, Business: 3, Economy: 6 }, timezone: "Europe/London" },
    ],
    bookings: [
      { id: "BK-8201", flightId: "FL-101", passenger: "Olivia Bennett", email: "olivia@example.com", passengers: ["Olivia Bennett", "James Bennett"], class: "Economy", fare: "Flexible", status: "Confirmed", createdAt: Date.now() - 86400000, farePrice: 420, idempotencyKey: "seed-BK-8201" },
      { id: "BK-8202", flightId: "FL-101", passenger: "Noah Williams", email: "noah@example.com", passengers: ["Noah Williams"], class: "Business", fare: "Flexible", status: "Confirmed", createdAt: Date.now() - 52000000, farePrice: 980, idempotencyKey: "seed-BK-8202" },
      { id: "BK-8203", flightId: "FL-102", passenger: "Amelia Chen", email: "amelia@example.com", passengers: ["Amelia Chen", "Liam Chen", "Mia Chen"], class: "Economy", fare: "Basic Economy", status: "Confirmed", createdAt: Date.now() - 23000000, farePrice: 360, idempotencyKey: "seed-BK-8203" },
      { id: "BK-8204", flightId: "FL-104", passenger: "Ethan Martin", email: "ethan@example.com", passengers: ["Ethan Martin"], class: "First", fare: "Refundable", status: "Confirmed", createdAt: Date.now() - 6000000, farePrice: 580, idempotencyKey: "seed-BK-8204" },
      { id: "BK-8205", flightId: "FL-103", passenger: "Sophia Patel", email: "sophia@example.com", passengers: ["Sophia Patel"], class: "Economy", fare: "Flexible", status: "Confirmed", createdAt: Date.now() - 3600000, farePrice: 285, idempotencyKey: "seed-BK-8205" },
    ],
    holds: [],
    waitlist: [
      { id: "WL-301", flightId: "FL-101", passenger: "Isabella Wright", email: "isabella@example.com", class: "Economy", loyalty: "Gold", fare: "Flexible", joinedAt: Date.now() - 4000000, status: "Waiting" },
      { id: "WL-302", flightId: "FL-101", passenger: "Lucas Taylor", email: "lucas@example.com", class: "Economy", loyalty: "Silver", fare: "Basic Economy", joinedAt: Date.now() - 9000000, status: "Waiting" },
      { id: "WL-303", flightId: "FL-102", passenger: "Ava Johnson", email: "ava@example.com", class: "Business", loyalty: "Platinum", fare: "Flexible", joinedAt: Date.now() - 600000, status: "Waiting" },
    ],
    approvals: [
      { id: "AP-401", type: "Schedule-change compensation", subject: "Booking BK-8203 · Amelia Chen", detail: "Airline schedule changed by 4h 20m. Fare-policy override requested.", amount: 240, status: "Pending", createdAt: Date.now() - 7200000, source: "Schedule-change workflow" },
      { id: "AP-402", type: "RAG response review", subject: "Case CS-0912 · Noah Williams", detail: "Draft references the passenger's actual Flexible fare and cancellation conditions.", amount: 0, status: "Pending", createdAt: Date.now() - 3600000, source: "Policy assistant" },
      { id: "AP-403", type: "Denied-boarding compensation", subject: "Booking BK-8204 · Ethan Martin", detail: "Manual eligibility and regulation check required before compensation.", amount: 650, status: "Pending", createdAt: Date.now() - 900000, source: "Gate operations" },
    ],
    refunds: [
      { id: "RF-210", bookingId: "BK-8108", passenger: "Grace Hall", amount: 185, status: "Processing", createdAt: Date.now() - 4 * 86400000 },
      { id: "RF-211", bookingId: "BK-8121", passenger: "Jack Wilson", amount: 72, status: "Processing", createdAt: Date.now() - 86400000 },
    ],
    audit: [
      { id: "AU-01", actor: "Alex Morgan", action: "Created flight", target: "NS204 · LHR → DXB", detail: "Seeded demo flight; 100-seat capacity, 20 First / 30 Business / 50 Economy.", at: Date.now() - 86400000 },
      { id: "AU-02", actor: "System · Demo", action: "Automatic decision", target: "Booking BK-8201", detail: "Seat inventory confirmed atomically; idempotency key checked; hard-oversell policy applied.", at: Date.now() - 54000000 },
      { id: "AU-03", actor: "System · Demo", action: "Approval routed", target: "AP-401", detail: "Schedule-change compensation requires human sign-off; no email was sent.", at: Date.now() - 7200000 },
    ],
    priceAlerts: [],
    lastAutomation: null,
  });
  let state = localStorage.getItem(STORE_KEY) ? JSON.parse(localStorage.getItem(STORE_KEY)) : initialState();
  const remote = {
    base: localStorage.getItem("northstar-api-base") || (window.location.protocol === "file:" ? "http://localhost:8000" : window.location.origin),
    token: sessionStorage.getItem("northstar-api-token") || "",
    connected: false,
    user: null,
    policy: null,
  };
  let currentView = "dashboard";
  let flightSearch = { origin: "", destination: "", date: isoDay(localDate(1)), passengers: 1, itinerary: false, cabin: "Economy" };
  let flightsFilter = "";
  let bookingsFilter = "";
  let apiSearchResults = null;
  let apiItineraryResults = null;

  function save() {
    if (!remote.connected) localStorage.setItem(STORE_KEY, JSON.stringify(state));
    updateBadges();
  }
  function connectApiModal() {
    openModal(remote.connected ? "Disconnect live API" : "Connect to the real API", remote.connected ? "Clear this session's access token and return to the local sample demo." : "Sign in to the PostgreSQL-backed FastAPI service. The browser stores only the short-lived access token in this tab.", `
      ${remote.connected ? `<div class="notice success"><span>✓</span><span>Connected to <strong>${esc(remote.base)}</strong> as ${esc(remote.user?.email || "admin")}.</span></div><div class="form-actions"><button class="btn" data-action="close-modal">Keep connected</button><button class="btn btn-danger" data-action="disconnect-api">Disconnect</button></div>` : `<form id="backend-connect-form" class="form-grid"><label class="form-field form-full">API base URL<input name="base" type="url" required value="${esc(remote.base)}" placeholder="http://localhost:8000"><small>For local Docker setup, use http://localhost:8000.</small></label><label class="form-field form-full">Admin email<input name="email" type="email" required autocomplete="username" placeholder="admin@example.com"></label><label class="form-field form-full">Password<input name="password" type="password" required autocomplete="current-password"></label><div class="notice form-full">Use an account created by the setup instructions. API writes require idempotency keys and are saved to PostgreSQL.</div><div class="form-actions form-full"><button type="button" class="btn" data-action="close-modal">Cancel</button><button class="btn btn-primary" type="submit">Connect securely</button></div></form>`}`);
  }
  function makeIdempotencyKey() {
    return globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }
  async function apiRequest(path, { method = "GET", body, token = remote.token, base = remote.base } = {}) {
    const headers = { Accept: "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) headers["Idempotency-Key"] = makeIdempotencyKey();
    let response;
    try {
      response = await fetch(`${base.replace(/\/+$/, "")}${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    } catch {
      throw new Error("Cannot reach the API. Check the server address and that FastAPI is running.");
    }
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
    return payload;
  }
  const apiFare = (fare) => ({ "Basic Economy": "basic_economy", "Flexible": "flexible", "Refundable": "refundable", "Credit-only": "credit_only", "Non-refundable": "non_refundable" })[fare] || "flexible";
  const uiFare = (fare) => ({ basic_economy: "Basic Economy", flexible: "Flexible", refundable: "Refundable", credit_only: "Credit-only", non_refundable: "Non-refundable" })[fare] || fare;
  const uiStatus = (value) => ({
    scheduled: "Scheduled", boarding: "Boarding", cancelled: "Cancelled", completed: "Completed",
    confirmed: "Confirmed", canceled: "Cancelled", refund_pending: "Refund processing",
    rebooking_required: "Rebooking required", credit_issued: "Credit issued",
    held: "Held", expired: "Expired", released: "Released",
    waiting: "Waiting", claim_window: "Claim window", claimed: "Claimed",
    pending: "Pending", approved: "Approved", rejected: "Rejected",
    processing: "Processing", failed: "Failed",
  })[String(value || "").toLowerCase()] || value;
  function mapRemoteState(data) {
    const user = data.current_user;
    const currency = data.flights[0]?.currency || "USD";
    state = {
      role: user.role === "super_admin" ? "super-admin" : user.role === "ops_agent" ? "ops-agent" : user.role,
      currency,
      locale: navigator.language || "en-US",
      flights: data.flights.map((flight) => ({
        id: String(flight.id), number: flight.flight_number, origin: flight.origin, destination: flight.destination,
        originCode: flight.origin_code, destinationCode: flight.destination_code,
        departure: localInputAtAirport(flight.departure_at, flight.origin_timezone),
        arrival: localInputAtAirport(flight.arrival_at, flight.destination_timezone),
        timezone: flight.origin_timezone, destinationTimezone: flight.destination_timezone,
        capacity: flight.capacity, seats: flight.seats_by_class,
        available: flight.available_by_class, prices: flight.prices, status: uiStatus(flight.status),
        overbooking: { First: 0, Business: 0, Economy: 0 }, cutoffs: { First: 2, Business: 3, Economy: 6 },
      })),
      bookings: data.bookings.map((booking) => ({
        id: String(booking.id), reference: booking.reference, flightId: String(booking.flight_id),
        passenger: booking.passenger_names[0] || "", email: booking.email,
        passengers: booking.passenger_names, class: booking.cabin, fare: uiFare(booking.fare_rule),
        status: uiStatus(booking.status), createdAt: new Date(booking.created_at).getTime(),
        farePrice: Number(booking.price_each), currency: booking.currency, changeNotice: booking.schedule_notice,
        idempotencyKey: booking.idempotency_key,
      })),
      holds: data.holds.map((hold) => ({
        id: String(hold.id), flightId: String(hold.flight_id), passenger: hold.passengers[0] || "",
        passengers: hold.passengers, email: hold.email, class: hold.cabin, fare: uiFare(hold.fare_rule),
        amount: Number(hold.price_each) * hold.passenger_count, priceEach: Number(hold.price_each),
        status: uiStatus(hold.status), expiresAt: new Date(hold.expires_at).getTime(), currency: hold.currency,
      })),
      waitlist: data.waitlist.map((entry) => ({
        id: String(entry.id), flightId: String(entry.flight_id), passenger: entry.passenger_name,
        email: entry.passenger_email, class: entry.cabin, loyalty: entry.loyalty_tier,
        fare: uiFare(entry.fare_rule), joinedAt: new Date(entry.created_at).getTime(),
        status: uiStatus(entry.status), claimUntil: entry.claim_until ? new Date(entry.claim_until).getTime() : null,
      })),
      approvals: data.approvals.map((approval) => ({
        id: String(approval.id), type: approval.type, subject: approval.subject,
        detail: approval.detail, amount: Number(approval.evidence?.requested_amount || 0),
        status: uiStatus(approval.status), createdAt: new Date(approval.created_at).getTime(),
      })),
      refunds: data.refunds.map((refund) => ({
        id: String(refund.id), bookingId: String(refund.booking_id),
        passenger: (refund.passenger_names || []).join(", "), amount: Number(refund.amount),
        status: uiStatus(refund.status), createdAt: new Date(refund.created_at).getTime(),
      })),
      audit: data.audit.map((item) => ({
        id: String(item.id), actor: item.actor, action: item.action,
        target: `${item.entity_type} ${item.entity_id}`, detail: item.rationale,
        at: new Date(item.created_at).getTime(),
      })),
      priceAlerts: [],
      lastAutomation: null,
    };
    remote.user = user;
    remote.policy = data.policy;
  }
  async function refreshRemote({ keepMessage = false } = {}) {
    if (!remote.token) return false;
    try {
      const data = await apiRequest("/api/bootstrap");
      mapRemoteState(data);
      remote.connected = true;
      render();
      if (!keepMessage) toast(`Connected to PostgreSQL API as ${remote.user.email}.`);
      return true;
    } catch (error) {
      remote.connected = false;
      toast(error.message, true);
      return false;
    }
  }
  async function apiWrite(path, body, method = "POST") {
    const result = await apiRequest(path, { method, body });
    await refreshRemote({ keepMessage: true });
    return result;
  }
  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
  }
  function money(value, currency = state.currency, locale = state.locale) {
    return new Intl.NumberFormat(locale || "en-US", { style: "currency", currency: currency || "USD", maximumFractionDigits: 0 }).format(Number(value) || 0);
  }
  function flightById(id) {
    return state.flights.find((flight) => flight.id === id);
  }
  function formatDate(value, options = {}) {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "—" : new Intl.DateTimeFormat(state.locale || "en-US", { month: "short", day: "numeric", ...options }).format(date);
  }
  function formatTime(value) {
    if (!value) return "—";
    return new Intl.DateTimeFormat(state.locale || "en-US", { hour: "2-digit", minute: "2-digit" }).format(new Date(value));
  }
  function formatAirportTime(value, timezone) {
    if (!value) return "—";
    return new Intl.DateTimeFormat(state.locale || "en-US", { hour: "2-digit", minute: "2-digit", timeZone: timezone || undefined }).format(new Date(value));
  }
  function localInputAtAirport(instant, timezone) {
    if (!instant) return "";
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: timezone || "UTC", year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hourCycle: "h23",
    }).formatToParts(new Date(instant));
    const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
    return `${values.year}-${values.month}-${values.day}T${values.hour}:${values.minute}`;
  }
  function airportInputToUtc(value, timezone) {
    const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value);
    if (!match) throw new Error("Enter a valid local date and time.");
    const target = Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]), Number(match[4]), Number(match[5]));
    let candidate = target;
    const formatter = new Intl.DateTimeFormat("en-CA", {
      timeZone: timezone || "UTC", year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
    });
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const parts = Object.fromEntries(formatter.formatToParts(new Date(candidate)).map((part) => [part.type, part.value]));
      const represented = Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day), Number(parts.hour), Number(parts.minute), Number(parts.second));
      candidate += target - represented;
    }
    const finalParts = Object.fromEntries(formatter.formatToParts(new Date(candidate)).map((part) => [part.type, part.value]));
    const matches = Number(finalParts.year) === Number(match[1]) && Number(finalParts.month) === Number(match[2]) &&
      Number(finalParts.day) === Number(match[3]) && Number(finalParts.hour) === Number(match[4]) && Number(finalParts.minute) === Number(match[5]);
    if (!matches) throw new Error("That local time does not exist in the selected airport timezone because of a daylight-saving transition.");
    return new Date(candidate).toISOString();
  }
  function elapsed(value) {
    const seconds = Math.max(0, Math.floor((Date.now() - value) / 1000));
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  }
  function toast(message, error = false) {
    const node = document.createElement("div");
    node.className = `toast${error ? " error" : ""}`;
    node.textContent = message;
    toastRegion.append(node);
    window.setTimeout(() => node.remove(), 3600);
  }
  function log(action, target, detail) {
    state.audit.unshift({ id: uid("AU"), actor: state.role === "super-admin" ? "Alex Morgan · Super-admin" : "Alex Morgan · Operations agent", action, target, detail, at: Date.now() });
    save();
  }
  function activeCount(flightId, cabin) {
    const confirmed = state.bookings.reduce((sum, booking) => sum + (booking.flightId === flightId && booking.class === cabin && booking.status === "Confirmed" ? booking.passengers.length : 0), 0);
    const held = state.holds.reduce((sum, hold) => sum + (hold.flightId === flightId && hold.class === cabin && hold.expiresAt > Date.now() ? hold.passengers.length : 0), 0);
    const promoted = state.waitlist.reduce((sum, entry) => sum + (entry.flightId === flightId && entry.class === cabin && entry.status === "Claim window" && entry.claimUntil > Date.now() ? 1 : 0), 0);
    return confirmed + held + promoted;
  }
  function available(flight, cabin) {
    if (!flight || flight.status === "Cancelled") return 0;
    if (remote.connected && flight.available) return Number(flight.available[cabin]) || 0;
    return Math.max(0, (Number(flight.seats[cabin]) || 0) + (Number(flight.overbooking?.[cabin]) || 0) - activeCount(flight.id, cabin));
  }
  function totalBooked(flightId) {
    return state.bookings.filter((booking) => booking.flightId === flightId && booking.status === "Confirmed").reduce((sum, booking) => sum + booking.passengers.length, 0);
  }
  function updateBadges() {
    const flightsBadge = document.querySelector("#flight-nav-count");
    const approvalsBadge = document.querySelector("#approval-nav-count");
    const waitlistBadge = document.querySelector("#waitlist-nav-count");
    if (flightsBadge) flightsBadge.textContent = String(state.flights.filter((flight) => flight.status !== "Cancelled").length);
    if (approvalsBadge) approvalsBadge.textContent = String(state.approvals.filter((item) => item.status === "Pending").length);
    if (waitlistBadge) waitlistBadge.textContent = String(state.waitlist.filter((entry) => entry.status === "Waiting" || entry.status === "Claim window").length);
  }
  function statusPill(value) {
    return `<span class="status status-${esc(String(value).toLowerCase().replace(/[^a-z]+/g, "-"))}">${esc(value)}</span>`;
  }
  function pageHeading(title, subtitle, action = "") {
    return `<div class="page-heading"><div><p class="eyebrow">Operations workspace</p><h1>${title}</h1><p class="heading-subtitle">${subtitle}</p></div>${action}</div>`;
  }
  function tableEmpty(cols, message) {
    return `<tr><td colspan="${cols}"><div class="empty-state"><strong>Nothing to show</strong>${message}</div></td></tr>`;
  }
  function activityMarkup(items) {
    if (!items.length) return `<div class="empty-state">No recent activity</div>`;
    return `<div class="activity-list">${items.map((item) => `<div class="activity-item"><span class="activity-mark">${item.action.includes("cancel") ? "×" : item.action.includes("flight") ? "✈" : "✓"}</span><div class="activity-copy"><strong>${esc(item.action)}</strong> · ${esc(item.target)}<small>${esc(item.actor)} · ${elapsed(item.at)}</small></div></div>`).join("")}</div>`;
  }
  function flightRow(flight, actions = true) {
    const confirmed = totalBooked(flight.id);
    const load = flight.capacity ? Math.min(100, Math.round((confirmed / flight.capacity) * 100)) : 0;
    const actionsHtml = actions ? `<div class="row-actions"><button class="btn btn-small" data-action="edit-flight" data-id="${esc(flight.id)}">Edit</button>${state.role === "super-admin" && flight.status !== "Cancelled" ? `<button class="btn btn-small btn-danger" data-action="cancel-flight" data-id="${esc(flight.id)}">Cancel</button>` : ""}</div>` : "";
    return `<tr><td><span class="flight-code">${esc(flight.number)}</span><span class="muted-cell">${esc(isoDay(flight.departure))}</span></td><td><span class="route-cell">${esc(flight.originCode)} <span aria-hidden="true">→</span> ${esc(flight.destinationCode)}</span><span class="muted-cell">${esc(flight.origin)} → ${esc(flight.destination)}</span></td><td>${formatAirportTime(flight.departure, flight.timezone)}<span class="muted-cell">Arrives ${formatAirportTime(flight.arrival, flight.destinationTimezone || flight.timezone)}</span></td><td>${statusPill(flight.status)}</td><td><div class="load-number"><span>${confirmed}/${flight.capacity}</span><span class="progress-line" style="width:54px"><span style="width:${load}%"></span></span></div><span class="muted-cell">${load}% load</span></td><td><div class="seat-pills"><span>F ${available(flight, "First")}</span><span>B ${available(flight, "Business")}</span><span>E ${available(flight, "Economy")}</span></div></td>${actions ? `<td>${actionsHtml}</td>` : ""}</tr>`;
  }
  function renderDashboard() {
    const activeFlights = state.flights.filter((flight) => flight.status !== "Cancelled").length;
    const confirmedCount = state.bookings.filter((booking) => booking.status === "Confirmed").reduce((sum, booking) => sum + booking.passengers.length, 0);
    const pending = state.approvals.filter((item) => item.status === "Pending").length;
    const unresolved = state.refunds.filter((refund) => refund.status === "Processing").length;
    const flights = state.flights.filter((flight) => flight.status !== "Cancelled").slice(0, 5);
    main.innerHTML = `${pageHeading("Good morning, Alex", "Here’s what’s happening across your flight operations today.", `<button class="btn btn-primary" data-action="new-flight">＋ Create flight</button>`)}
      <div class="metric-grid">
        <div class="metric-card"><div class="metric-top">Active flights<span class="metric-icon">✈</span></div><strong class="metric-value">${activeFlights}</strong><span class="metric-foot"><span class="positive">${remote.connected ? "PostgreSQL" : "Live"}</span> · ${remote.connected ? "database-backed" : "across 4 routes"}</span></div>
        <div class="metric-card"><div class="metric-top">Confirmed passengers<span class="metric-icon">♙</span></div><strong class="metric-value">${confirmedCount}</strong><span class="metric-foot"><span class="positive">+12%</span> · compared to last week</span></div>
        <div class="metric-card"><div class="metric-top">Awaiting approval<span class="metric-icon">✓</span></div><strong class="metric-value">${pending}</strong><span class="metric-foot">${pending ? "Needs a human decision" : "All caught up"}</span></div>
        <div class="metric-card"><div class="metric-top">Refunds in progress<span class="metric-icon">↗</span></div><strong class="metric-value">${unresolved}</strong><span class="metric-foot">${state.refunds.filter((r) => r.status === "Processing" && Date.now() - r.createdAt > 3 * 86400000).length} past 3-day escalation threshold</span></div>
      </div>
      <div class="dashboard-grid">
        <section class="card"><div class="card-head"><div><h2>Upcoming flights</h2><p>Inventory and booking load · local demo data</p></div><button class="btn btn-small" data-view="flights">All flights →</button></div><div class="table-wrap"><table><thead><tr><th>Flight</th><th>Route</th><th>Departure</th><th>Status</th><th>Load</th><th>Available</th><th></th></tr></thead><tbody>${flights.length ? flights.map((flight) => flightRow(flight)).join("") : tableEmpty(7, "Create a flight to get started.")}</tbody></table></div></section>
        <section class="card"><div class="card-head"><div><h2>Recent activity</h2><p>Auditable changes and decisions</p></div><button class="btn btn-small btn-quiet" data-view="audit">View all →</button></div><div class="card-body">${activityMarkup(state.audit.slice(0, 5))}</div></section>
      </div>
      <div class="notice ${remote.connected ? "success" : ""}" style="margin-top:16px"><span>ⓘ</span><span>${remote.connected ? `<strong>Connected to the live API.</strong> Flight, booking, inventory, and audit data load from PostgreSQL. Scheduled n8n/Gmail/Pinecone services remain separate integrations.` : `<strong>Prototype, not a live airline system.</strong> Changes persist in this browser only until you connect the FastAPI/PostgreSQL service.`}</span></div>`;
  }
  function renderFlights() {
    const filtered = state.flights.filter((flight) => `${flight.number} ${flight.origin} ${flight.destination} ${flight.originCode} ${flight.destinationCode}`.toLowerCase().includes(flightsFilter.toLowerCase()));
    main.innerHTML = `${pageHeading("Flight management", "Create flights, manage seat inventory, and keep schedule changes auditable.", `${state.role === "super-admin" ? `<button class="btn btn-primary" data-action="new-flight">＋ Create flight</button>` : `<span class="notice">Operations agents may edit schedules, but only super-admins may create flights or change inventory.</span>`}`)}
      <div class="notice" style="margin-bottom:14px"><span>⌁</span><span><strong>Inventory rule:</strong> class capacities must be positive integers and sum to aircraft capacity. Confirmed bookings and active holds cannot be oversold; class allocation cannot fall below booked count. ${remote.connected ? "Writes commit to PostgreSQL with row locks and DB constraints." : "Demo changes stay in localStorage."}</span></div>
      <div class="toolbar-row"><div class="filter-group"><input class="field search-field" id="flight-filter" placeholder="Search flight or route…" value="${esc(flightsFilter)}"><select class="select" id="flight-status-filter"><option value="all">All statuses</option><option value="Scheduled">Scheduled</option><option value="Boarding">Boarding</option><option value="Cancelled">Cancelled</option></select></div><span class="heading-subtitle">${state.flights.length} flights · ${state.role === "super-admin" ? "Super-admin permissions" : "Operations agent permissions"}</span></div>
      <section class="card"><div class="table-wrap"><table class="flight-table"><thead><tr><th>Flight</th><th>Route</th><th>Schedule</th><th>Status</th><th>Load</th><th>Available seats</th><th>Actions</th></tr></thead><tbody id="flights-table">${filtered.length ? filtered.map((flight) => flightRow(flight)).join("") : tableEmpty(7, "Try a different search or create a flight.")}</tbody></table></div></section>
      <section class="card" style="margin-top:16px"><div class="card-head"><div><h2>Physical seat layout</h2><p>Seat assignments map to First, Business, and Economy cabins.</p></div><select class="select" id="seat-map-flight">${state.flights.map((flight) => `<option value="${esc(flight.id)}">${esc(flight.number)} · ${esc(flight.originCode)} → ${esc(flight.destinationCode)}</option>`).join("")}</select></div><div id="seat-map-container"></div></section>`;
    drawSeatMap();
    const statusFilter = document.querySelector("#flight-status-filter");
    if (statusFilter) statusFilter.addEventListener("change", () => {
      const status = statusFilter.value;
      const search = document.querySelector("#flight-filter").value.toLowerCase();
      const rows = state.flights.filter((flight) => `${flight.number} ${flight.origin} ${flight.destination} ${flight.originCode} ${flight.destinationCode}`.toLowerCase().includes(search) && (status === "all" || flight.status === status));
      document.querySelector("#flights-table").innerHTML = rows.length ? rows.map((flight) => flightRow(flight)).join("") : tableEmpty(7, "No flights match these filters.");
    });
  }
  function drawSeatMap() {
    const container = document.querySelector("#seat-map-container");
    if (!container) return;
    const flight = flightById(document.querySelector("#seat-map-flight")?.value || state.flights[0]?.id);
    if (!flight) { container.innerHTML = `<div class="empty-state">Create a flight to see its seat map.</div>`; return; }
    if (remote.connected) {
      container.innerHTML = `<div class="empty-state">Loading physical seat layout…</div>`;
      apiRequest(`/api/flights/${encodeURIComponent(flight.id)}/seats`).then((result) => {
        if (!document.querySelector("#seat-map-container")) return;
        const seats = result.layout.map((seat) => `<span class="seat ${seat.cabin.toLowerCase()}" title="${esc(seat.cabin)} · ${esc(seat.status)}">${esc(seat.seat_number)}</span>`).join("");
        container.innerHTML = `<div class="seat-map">${seats}</div><div class="seat-legend"><span><i class="legend-swatch first"></i>First · ${flight.seats.First}</span><span><i class="legend-swatch business"></i>Business · ${flight.seats.Business}</span><span><i class="legend-swatch economy"></i>Economy · ${flight.seats.Economy}</span></div><p class="heading-subtitle" style="padding:10px 18px 0;text-align:center">Physical seat records from PostgreSQL · booked and held seats are marked in the tooltip.</p>`;
      }).catch((error) => { container.innerHTML = `<div class="empty-state">${esc(error.message)}</div>`; });
      return;
    }
    const blocks = [["First", "first"], ["Business", "business"], ["Economy", "economy"]];
    let row = 1;
    const seats = blocks.map(([name, className]) => {
      const count = Math.min(Number(flight.seats[name]) || 0, 48);
      const out = Array.from({ length: count }, () => `<span class="seat ${className}" title="${name} cabin">` + `${row}${String.fromCharCode(65 + ((row + count) % 6))}` + `</span>`).join("");
      row += Math.ceil(count / 8);
      return out;
    }).join("");
    container.innerHTML = `<div class="seat-map">${seats}</div><div class="seat-legend"><span><i class="legend-swatch first"></i>First · ${flight.seats.First}</span><span><i class="legend-swatch business"></i>Business · ${flight.seats.Business}</span><span><i class="legend-swatch economy"></i>Economy · ${flight.seats.Economy}</span></div><p class="heading-subtitle" style="padding:10px 18px 0;text-align:center">Illustrative layout only · unassigned physical seats are not persisted in the demo.</p>`;
  }
  function cabinOptions(selected = "Economy") {
    return ["First", "Business", "Economy"].map((cabin) => `<option value="${cabin}" ${cabin === selected ? "selected" : ""}>${cabin}</option>`).join("");
  }
  function openModal(title, subtitle, content, onReady) {
    modal.innerHTML = `<div class="modal-header"><div><h2 id="modal-title">${title}</h2><p>${subtitle}</p></div><button class="modal-close" data-action="close-modal" aria-label="Close">×</button></div><div class="modal-content">${content}</div>`;
    modalBackdrop.hidden = false;
    if (onReady) onReady();
    modal.querySelector("input,select,button")?.focus();
  }
  function closeModal() {
    modalBackdrop.hidden = true;
    modal.innerHTML = "";
  }
  function flightForm(flight) {
    const editing = Boolean(flight);
    const canEditCapacity = !editing || state.role === "super-admin";
    const active = flight ? totalBooked(flight.id) : 0;
    openModal(editing ? `Edit ${esc(flight.number)}` : "Create a flight", editing ? "Schedule changes are cascaded to existing bookings and recorded in the audit trail." : "Define a route, schedule, and positive seat allocation for each cabin.", `
      <form id="flight-form" class="form-grid">
        <label class="form-field">Flight number<input name="number" required maxlength="12" pattern="[A-Za-z0-9\\-]+" value="${esc(flight?.number || "")}" placeholder="NS204"></label>
        <label class="form-field">Aircraft capacity<input name="capacity" type="number" min="3" step="1" required value="${esc(flight?.capacity || 100)}" ${canEditCapacity ? "" : "readonly"}></label>
        <label class="form-field">Origin<input name="origin" required value="${esc(flight?.origin || "")}" placeholder="London (LHR)"></label>
        <label class="form-field">Destination<input name="destination" required value="${esc(flight?.destination || "")}" placeholder="Dubai (DXB)"></label>
        <label class="form-field">Origin code<input name="originCode" required maxlength="3" pattern="[A-Za-z]{3}" value="${esc(flight?.originCode || "")}" placeholder="LHR"></label>
        <label class="form-field">Destination code<input name="destinationCode" required maxlength="3" pattern="[A-Za-z]{3}" value="${esc(flight?.destinationCode || "")}" placeholder="DXB"></label>
        <label class="form-field">Origin timezone<input name="origin_timezone" required value="${esc(flight?.timezone || "UTC")}" placeholder="Europe/London"></label>
        <label class="form-field">Destination timezone<input name="destination_timezone" required value="${esc(flight?.destinationTimezone || "UTC")}" placeholder="Asia/Dubai"></label>
        <label class="form-field">Departure date &amp; time (${esc(flight?.timezone || "origin local time")})<input name="departure" type="datetime-local" required value="${esc(flight ? flight.departure : localDate(1, 9))}"></label>
        <label class="form-field">Arrival date &amp; time (${esc(flight?.destinationTimezone || "destination local time")})<input name="arrival" type="datetime-local" required value="${esc(flight ? flight.arrival : localDate(1, 19))}"></label>
        <div class="form-section">Cabin inventory ${editing ? `· ${active} confirmed passengers` : ""}</div>
        <label class="form-field">First seats<input name="first" type="number" min="1" step="1" required value="${esc(flight?.seats.First || 20)}" ${canEditCapacity ? "" : "readonly"}></label>
        <label class="form-field">Business seats<input name="business" type="number" min="1" step="1" required value="${esc(flight?.seats.Business || 30)}" ${canEditCapacity ? "" : "readonly"}></label>
        <label class="form-field">Economy seats<input name="economy" type="number" min="1" step="1" required value="${esc(flight?.seats.Economy || 50)}" ${canEditCapacity ? "" : "readonly"}></label>
        <label class="form-field">First fare · ${esc(state.currency)}<input name="firstPrice" type="number" min="1" step="1" required value="${esc(flight?.prices.First || 1840)}"></label>
        <label class="form-field">Business fare · ${esc(state.currency)}<input name="businessPrice" type="number" min="1" step="1" required value="${esc(flight?.prices.Business || 980)}"></label>
        <label class="form-field">Economy fare · ${esc(state.currency)}<input name="economyPrice" type="number" min="1" step="1" required value="${esc(flight?.prices.Economy || 420)}"></label>
        <label class="form-field">Airline-initiated change<input name="airline_initiated" type="checkbox" value="true" ${remote.connected ? "" : "disabled"}><small>Enable automatic rebooking outbox and fare-policy override.</small></label>
        <div class="notice form-full">${canEditCapacity ? "Class seats must total exactly to aircraft capacity; every class must have at least one seat." : "Operations agents can update flight schedule and route only. Cabin inventory remains super-admin controlled."}</div>
        <div class="form-actions form-full"><button type="button" class="btn" data-action="close-modal">Cancel</button><button class="btn btn-primary" type="submit">${editing ? "Save changes" : "Create flight"}</button></div>
      </form>`);
    document.querySelector("#flight-form").dataset.flightId = flight?.id || "";
  }
  async function processFlightForm(form) {
    const data = new FormData(form);
    const number = String(data.get("number")).trim().toUpperCase();
    const originCode = String(data.get("originCode")).trim().toUpperCase();
    const destinationCode = String(data.get("destinationCode")).trim().toUpperCase();
    const departure = String(data.get("departure"));
    const arrival = String(data.get("arrival"));
    const capacity = Number(data.get("capacity"));
    const seats = { First: Number(data.get("first")), Business: Number(data.get("business")), Economy: Number(data.get("economy")) };
    const flightId = form.dataset.flightId;
    const existing = flightId ? flightById(flightId) : null;
    if (state.role !== "super-admin" && !existing) return toast("Only a super-admin can create flights.", true);
    if (existing && state.role !== "super-admin" && (seats.First !== existing.seats.First || seats.Business !== existing.seats.Business || seats.Economy !== existing.seats.Economy || capacity !== existing.capacity)) return toast("Operations agents cannot change seat allocation or capacity.", true);
    if (!Number.isInteger(capacity) || capacity < 3 || Object.values(seats).some((value) => !Number.isInteger(value) || value <= 0)) return toast("Capacity and cabin seat counts must be positive whole numbers.", true);
    if (Object.values(seats).reduce((sum, value) => sum + value, 0) !== capacity) return toast("First + Business + Economy must equal aircraft capacity.", true);
    if (new Date(arrival) <= new Date(departure)) return toast("Arrival must be after departure.", true);
    if (!originCode.match(/^[A-Z]{3}$/) || !destinationCode.match(/^[A-Z]{3}$/) || originCode === destinationCode) return toast("Enter distinct three-letter airport codes.", true);
    if (remote.connected) {
      const body = {
        flight_number: number,
        origin: String(data.get("origin")).trim(),
        destination: String(data.get("destination")).trim(),
        origin_code: originCode,
        destination_code: destinationCode,
        origin_timezone: String(data.get("origin_timezone") || "UTC"),
        destination_timezone: String(data.get("destination_timezone") || "UTC"),
      };
      try {
        body.departure_at = airportInputToUtc(departure, body.origin_timezone);
        body.arrival_at = airportInputToUtc(arrival, body.destination_timezone);
        if (canEditCapacity) Object.assign(body, {
          capacity,
          first_seats: seats.First,
          business_seats: seats.Business,
          economy_seats: seats.Economy,
          first_price: Number(data.get("firstPrice")) || 1840,
          business_price: Number(data.get("businessPrice")) || 980,
          economy_price: Number(data.get("economyPrice")) || 420,
          currency: state.currency,
        });
      } catch (error) { return toast(error.message, true); }
      try {
        if (flightId) {
          await apiRequest(`/api/flights/${encodeURIComponent(flightId)}`, { method: "PATCH", body: { ...body, airline_initiated: form.querySelector('[name="airline_initiated"]')?.checked || false } });
        } else {
          await apiRequest("/api/flights", { method: "POST", body });
        }
        closeModal();
        await refreshRemote({ keepMessage: true });
        toast(flightId ? "Flight updated in PostgreSQL." : `${number} created in PostgreSQL.`);
      } catch (error) { toast(error.message, true); }
      return;
    }
    const duplicate = state.flights.find((item) => item.id !== flightId && item.number.toUpperCase() === number && isoDay(item.departure) === isoDay(departure) && item.originCode === originCode && item.destinationCode === destinationCode);
    if (duplicate) return toast("This flight number already exists for that day and route.", true);
    if (existing) {
      for (const cabin of ["First", "Business", "Economy"]) {
        if (seats[cabin] < activeCount(existing.id, cabin)) return toast(`${cabin} cannot be reduced below its confirmed, held, or promoted seat count (${activeCount(existing.id, cabin)}).`, true);
      }
      const oldRoute = `${existing.originCode} → ${existing.destinationCode}`;
      const oldSchedule = `${existing.departure} / ${existing.arrival}`;
      Object.assign(existing, {
        number, origin: String(data.get("origin")).trim(), destination: String(data.get("destination")).trim(), originCode, destinationCode, departure, arrival,
        capacity, seats, prices: { ...existing.prices, Economy: Number(data.get("economyPrice")) || existing.prices.Economy },
      });
      const changedRoute = oldRoute !== `${originCode} → ${destinationCode}`;
      const changedSchedule = oldSchedule !== `${departure} / ${arrival}`;
      state.bookings.filter((booking) => booking.flightId === existing.id && booking.status === "Confirmed").forEach((booking) => { booking.changeNotice = changedRoute || changedSchedule ? `Updated route/schedule · ${formatDate(departure)} ${formatTime(departure)}` : booking.changeNotice; });
      log("Updated flight schedule / inventory", `${number} · ${oldRoute} → ${originCode} → ${destinationCode}`, `Schedule ${oldSchedule} → ${departure} / ${arrival}; booking records retained and affected passengers flagged for notification.${changedRoute ? " Route change cascaded to all linked bookings." : ""}`);
      toast("Flight updated; linked bookings retained and audited.");
    } else {
      const flight = { id: uid("FL"), number, origin: String(data.get("origin")).trim(), destination: String(data.get("destination")).trim(), originCode, destinationCode, departure, arrival, capacity, seats, prices: { First: 1800, Business: 900, Economy: Number(data.get("economyPrice")) || 420 }, status: "Scheduled", overbooking: { First: 0, Business: 0, Economy: 0 }, cutoffs: { First: 2, Business: 3, Economy: 6 }, timezone: "UTC" };
      state.flights.push(flight);
      log("Created flight", `${number} · ${originCode} → ${destinationCode}`, `Capacity ${capacity}; allocation First ${seats.First}, Business ${seats.Business}, Economy ${seats.Economy}. Seat map generated from the cabin layout.`);
      toast(`${number} created successfully.`);
    }
    save(); closeModal(); render();
  }
  function cancelFlight(id) {
    const flight = flightById(id);
    if (!flight || state.role !== "super-admin") return toast("Only a super-admin may cancel a flight.", true);
    openModal(`Cancel ${esc(flight.number)}?`, "Choose how confirmed passengers should be processed. This demo records the decision; it does not issue money or send messages.", `
      <form id="cancel-flight-form" class="form-grid"><label class="form-field form-full">Passenger resolution<select name="resolution" required><option value="Refund">Refund to original payment</option><option value="Rebooking">Rebook on next available flight</option><option value="Travel credit">Issue travel credit (12-month expiry)</option></select></label>
      <div class="notice warn form-full">${totalBooked(flight.id)} confirmed passenger(s) will be marked for downstream processing. Refunds/rebooking/credits are simulated only.</div>
      <div class="form-actions form-full"><button type="button" class="btn" data-action="close-modal">Keep flight</button><button class="btn btn-danger" type="submit">Cancel flight</button></div></form>`);
    document.querySelector("#cancel-flight-form").dataset.flightId = id;
  }
  async function processCancelFlight(form) {
    const flight = flightById(form.dataset.flightId);
    if (!flight || state.role !== "super-admin") return toast("Cancellation permission denied.", true);
    const resolution = new FormData(form).get("resolution");
    if (remote.connected) {
      try {
        await apiRequest(`/api/flights/${encodeURIComponent(id)}/cancel`, {
          method: "POST",
          body: { resolution: resolution === "Refund" ? "refund" : resolution === "Rebooking" ? "rebooking" : "travel_credit" },
        });
        closeModal(); await refreshRemote({ keepMessage: true });
        toast(`${flight.number} cancelled in PostgreSQL.`);
      } catch (error) { toast(error.message, true); }
      return;
    }
    flight.status = "Cancelled";
    const affected = state.bookings.filter((booking) => booking.flightId === flight.id && booking.status === "Confirmed");
    affected.forEach((booking) => {
      booking.status = resolution === "Rebooking" ? "Rebooking required" : resolution === "Travel credit" ? "Credit issued" : "Refund processing";
      booking.resolution = resolution;
      if (resolution === "Refund") state.refunds.unshift({ id: uid("RF"), bookingId: booking.id, passenger: booking.passenger, amount: booking.farePrice * booking.passengers.length, status: "Processing", createdAt: Date.now() });
      if (resolution === "Travel credit") booking.creditExpires = new Date(Date.now() + 365 * 86400000).toISOString();
    });
    state.holds = state.holds.filter((hold) => hold.flightId !== flight.id);
    log("Cancelled flight", `${flight.number} · ${flight.originCode} → ${flight.destinationCode}`, `Resolution selected: ${resolution}. ${affected.length} booking(s) queued for follow-up; cancellation takes precedence over any pending seat promotion.`);
    toast(`${flight.number} cancelled. ${affected.length} booking(s) flagged for ${resolution.toLowerCase()}.`);
    save(); closeModal(); render();
  }
  function renderSearch() {
    const originOptions = [...new Set(state.flights.map((flight) => flight.originCode))];
    const destinationOptions = [...new Set(state.flights.map((flight) => flight.destinationCode))];
    const matching = apiSearchResults || state.flights.filter((flight) => flight.status !== "Cancelled" && isoDay(flight.departure) === flightSearch.date && (!flightSearch.origin || flight.originCode === flightSearch.origin) && (!flightSearch.destination || flight.destinationCode === flightSearch.destination));
    const resultsMarkup = remote.connected && flightSearch.itinerary
      ? (apiItineraryResults?.length ? apiItineraryResults.map((itinerary) => {
        const legs = itinerary.legs;
        const availableSeats = Math.min(...legs.map((leg) => available(leg, flightSearch.cabin)));
        const price = legs.reduce((total, leg) => total + Number(leg.prices[flightSearch.cabin] || 0), 0);
        const holdButton = legs.length > 1
          ? `<button class="btn btn-primary" data-action="hold-itinerary" data-legs="${legs.map((leg) => esc(leg.id)).join(",")}" data-class="${esc(flightSearch.cabin)}" ${availableSeats < flightSearch.passengers ? "disabled" : ""}>Hold itinerary</button>`
          : `<button class="btn btn-primary" data-action="hold-seat" data-flight="${esc(legs[0].id)}" data-class="${esc(flightSearch.cabin)}" ${availableSeats < flightSearch.passengers ? "disabled" : ""}>Hold flight</button>`;
        return `<section class="card" style="margin-bottom:12px"><div class="card-head"><div><h2>${esc(legs[0].originCode)} → ${esc(legs[legs.length - 1].destinationCode)} · ${legs.length === 1 ? "Direct" : `Connects in ${itinerary.connectionMinutes} min`}</h2><p>${legs.map((leg) => `${esc(leg.number)} · ${formatAirportTime(leg.departure, leg.timezone)}`).join(" → ")}</p></div><span class="integration-status">${availableSeats} ${esc(flightSearch.cabin)} seats</span></div><div class="card-body"><div class="meta-grid">${legs.map((leg, index) => `<div class="meta-box"><small>Leg ${index + 1} · ${esc(leg.number)}</small><strong>${esc(leg.originCode)} → ${esc(leg.destinationCode)}</strong><span class="muted-cell">${formatAirportTime(leg.departure, leg.timezone)} — ${formatAirportTime(leg.arrival, leg.destinationTimezone)}</span></div>`).join("")}</div><div class="fare-card" style="margin-top:12px"><h3>${esc(flightSearch.cabin)} · Flexible</h3><span class="fare-price">${money(price, legs[0].currency)}</span><p>Combined fare across ${legs.length} leg(s); each leg is revalidated and held atomically.</p>${holdButton}</div></div></section>`;
      }).join("") || `<section class="card"><div class="empty-state"><strong>No suitable itinerary found</strong>Try another date, route, or cabin.</div></section>`)
      : (matching.length ? matching.map((flight) => `<section class="card" style="margin-bottom:12px"><div class="card-head"><div><h2><span class="flight-code">${esc(flight.number)}</span> <span class="route-cell">${esc(flight.originCode)} → ${esc(flight.destinationCode)}</span></h2><p>${esc(flight.origin)} to ${esc(flight.destination)} · ${formatDate(flight.departure, { year: "numeric" })}</p></div>${statusPill(flight.status)}</div><div class="card-body"><div class="meta-grid"><div class="meta-box"><small>Departure · arrival (airport local time)</small><strong>${formatAirportTime(flight.departure, flight.timezone)} — ${formatAirportTime(flight.arrival, flight.destinationTimezone || flight.timezone)}</strong></div><div class="meta-box"><small>Estimated connection</small><strong>Direct · local times shown</strong></div></div><div class="availability-grid">${["First", "Business", "Economy"].map((cabin) => `<div class="fare-card"><h3>${cabin}</h3><span class="fare-price">${money(flight.prices[cabin], flight.currency || state.currency)}</span><p>${available(flight, cabin)} seats available</p><ul>${cabin === "Economy" ? "<li>Basic Economy: no changes, no seat choice</li><li>Flexible: changes allowed per fare terms</li>" : "<li>Flexible fare conditions apply</li><li>Class-specific cutoff applies</li>"}</ul><button class="btn btn-primary" data-action="hold-seat" data-flight="${esc(flight.id)}" data-class="${cabin}" ${available(flight, cabin) <= 0 ? "disabled" : ""}>Hold ${Math.min(flightSearch.passengers, available(flight, cabin)) || 0} seat${flightSearch.passengers > 1 ? "s" : ""}</button><button class="btn btn-small" data-action="price-alert" data-flight="${esc(flight.id)}" data-class="${cabin}">Price alert</button></div>`).join("")}</div></div></section>`).join("") : `<section class="card"><div class="empty-state"><strong>No flights found for these search options</strong>Choose another date or route, or create a flight in Flight management.</div></section>`);
    main.innerHTML = `${pageHeading("Search & book", "Search route inventory, compare fare rules, and simulate a seat hold.", `<button class="btn" data-action="currency">Currency: ${esc(state.currency)} ↻</button>`)}
      <section class="card"><div class="card-head"><div><h2>Find a flight</h2><p>Search results reflect current confirmed bookings, checkout holds, and waitlist claims.</p></div></div><div class="card-body"><form id="search-form" class="inline-form">
        <label class="form-field">From<select class="select" name="origin"><option value="">Any origin</option>${originOptions.map((value) => `<option value="${esc(value)}" ${flightSearch.origin === value ? "selected" : ""}>${esc(value)}</option>`).join("")}</select></label>
        <label class="form-field">To<select class="select" name="destination"><option value="">Any destination</option>${destinationOptions.map((value) => `<option value="${esc(value)}" ${flightSearch.destination === value ? "selected" : ""}>${esc(value)}</option>`).join("")}</select></label>
        <label class="form-field">Departure date<input class="field" type="date" name="date" value="${esc(flightSearch.date)}" required></label>
        <label class="form-field">Passengers<input class="field" type="number" name="passengers" min="1" max="9" value="${esc(flightSearch.passengers)}" required></label>
        <label class="form-field">Trip type<select class="select" name="itinerary"><option value="direct" ${flightSearch.itinerary ? "" : "selected"}>Direct flight</option><option value="connecting" ${flightSearch.itinerary ? "selected" : ""}>Direct or connecting</option></select></label>
        ${flightSearch.itinerary ? `<label class="form-field">Cabin for all legs<select class="select" name="cabin">${["First", "Business", "Economy"].map((cabin) => `<option ${flightSearch.cabin === cabin ? "selected" : ""}>${cabin}</option>`).join("")}</select></label>` : ""}
        <button type="submit" class="btn btn-primary">Search flights</button>
      </form></div></section>
      <div class="notice" style="margin:14px 0"><span>◷</span><span><strong>Price hold:</strong> fares are held for ${remote.policy?.price_hold_minutes || 15} minutes at checkout. ${remote.connected ? "Connecting legs can be reserved atomically through the itinerary API." : "Connect the API for transactional all-legs-or-none itinerary holds."}</span></div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin:20px 0 10px"><div><h2 style="margin:0 0 4px;font:700 15px Manrope">Available flights</h2><p class="heading-subtitle">${matching.length} result${matching.length === 1 ? "" : "s"} · ${esc(flightSearch.date)}</p></div></div>
      ${resultsMarkup}
      <section class="card" style="margin-top:15px"><div class="card-head"><div><h2>Fare rules &amp; decision boundaries</h2><p>Specific fare purchased—not generic policy matches—governs customer answers.</p></div></div><div class="card-body"><div class="flow-grid"><div class="flow-card"><span class="flow-icon">◇</span><h3>Basic Economy</h3><p>No voluntary changes or advance seat choice. Cancellation generally non-refundable; exact terms follow the selected offer.</p></div><div class="flow-card"><span class="flow-icon">↗</span><h3>Flexible</h3><p>Changes allowed subject to fare difference. Standard in-policy refunds may be auto-approved; exceptions require review.</p></div><div class="flow-card"><span class="flow-icon">✓</span><h3>Human sign-off</h3><p>Schedule-change and denied-boarding compensation require a human approval before customer communication.</p></div></div></div></section>`;
  }
  async function processSearch(form) {
    const data = new FormData(form);
    flightSearch = {
      origin: String(data.get("origin")),
      destination: String(data.get("destination")),
      date: String(data.get("date")),
      passengers: Math.min(9, Math.max(1, Number(data.get("passengers")) || 1)),
      itinerary: String(data.get("itinerary")) === "connecting",
      cabin: String(data.get("cabin") || "Economy"),
    };
    if (remote.connected) {
      if (!flightSearch.origin || !flightSearch.destination) return toast("Select both an origin and destination for a database search.", true);
      try {
        const mapFlight = (flight) => ({
          id: String(flight.id), number: flight.flight_number, origin: flight.origin, destination: flight.destination,
          originCode: flight.origin_code, destinationCode: flight.destination_code,
          departure: flight.departure_at, arrival: flight.arrival_at, timezone: flight.origin_timezone,
          destinationTimezone: flight.destination_timezone, capacity: flight.capacity, status: uiStatus(flight.status),
          currency: flight.currency, prices: flight.prices, seats: flight.seats_by_class,
          available: flight.available_by_class, overbooking: { First: 0, Business: 0, Economy: 0 },
        });
        if (flightSearch.itinerary) {
          const query = new URLSearchParams({
            origin: flightSearch.origin, destination: flightSearch.destination, travel_date: flightSearch.date,
            cabin: flightSearch.cabin, passengers: String(flightSearch.passengers),
          });
          const result = await apiRequest(`/api/itineraries/search?${query}`);
          apiItineraryResults = result.results.map((itinerary) => ({
            connectionMinutes: itinerary.connection_minutes,
            legs: itinerary.legs.map(mapFlight),
          }));
          apiSearchResults = [];
        } else {
          const query = new URLSearchParams({ origin: flightSearch.origin, destination: flightSearch.destination, travel_date: flightSearch.date, passengers: String(flightSearch.passengers), currency: state.currency });
          const result = await apiRequest(`/api/flights/search?${query}`);
          apiSearchResults = result.results.map(mapFlight);
          apiItineraryResults = null;
        }
      } catch (error) { return toast(error.message, true); }
    } else {
      apiSearchResults = null;
      apiItineraryResults = null;
    }
    renderSearch();
  }
  function holdItinerary(button) {
    const flightIds = button.dataset.legs.split(",").filter(Boolean);
    if (!remote.connected || flightIds.length < 2) return toast("Connect to the PostgreSQL API to hold a connecting itinerary.", true);
    const passengerNames = Array.from({ length: flightSearch.passengers }, (_, index) => `Passenger ${index + 1}`).join("\n");
    openModal("Hold connecting itinerary", "All flight legs are reserved in one transaction. If any leg is unavailable, none will be held.", `
      <form id="itinerary-hold-form" data-flight-ids="${esc(flightIds.join(","))}" data-class="${esc(button.dataset.class)}">
        <label class="form-field" style="margin:10px 0">Fare rule<select name="fare" class="select"><option>Flexible</option><option>Basic Economy</option><option>Refundable</option><option>Credit-only</option><option>Non-refundable</option></select></label>
        <label class="form-field" style="margin:10px 0">Contact email<input name="email" type="email" required value="${esc(remote.user?.email || "")}" placeholder="traveler@example.com"></label>
        <label class="form-field" style="margin:10px 0">Passenger names · one per line<textarea name="passengers" class="field" rows="3" style="height:auto;padding:9px" required>${esc(passengerNames)}</textarea></label>
        <div class="form-actions"><button type="button" class="btn" data-action="close-modal">Cancel</button><button class="btn btn-primary" type="submit">Hold all legs</button></div>
      </form>`);
  }
  async function processItineraryHold(form) {
    const flightIds = form.dataset.flightIds.split(",").map(Number);
    const data = new FormData(form);
    const passengers = String(data.get("passengers")).split(/\r?\n/).map((name) => name.trim()).filter(Boolean);
    if (passengers.length !== flightSearch.passengers) return toast(`Enter exactly ${flightSearch.passengers} passenger name(s).`, true);
    if (new Set(passengers.map((name) => name.toLowerCase())).size !== passengers.length) return toast("Passenger names must be unique.", true);
    try {
      const result = await apiRequest("/api/itineraries/holds", {
        method: "POST",
        body: {
          flight_ids: flightIds,
          cabin: form.dataset.class,
          fare_rule: apiFare(String(data.get("fare"))),
          passengers: passengers.map((name) => ({ name })),
          email: String(data.get("email")),
        },
      });
      closeModal(); await refreshRemote({ keepMessage: true });
      toast(`All ${result.holds.length} leg(s) held in PostgreSQL until ${formatTime(result.holds[0].expires_at)}.`);
      currentView = "bookings"; render();
    } catch (error) { toast(error.message, true); }
  }
  function makeHold(flightId, cabin) {
    const flight = flightById(flightId);
    if (!flight || flight.status === "Cancelled") return toast("This flight is no longer available.", true);
    const requested = flightSearch.passengers;
    const count = available(flight, cabin);
    if (!count) return toast("No seats remain in this class.", true);
    const defaultNames = Array.from({ length: requested }, (_, index) => `Passenger ${index + 1}`).join("\n");
    openModal("Choose group booking behavior", `There are ${count} ${cabin} seat(s) for ${requested} passenger(s) on ${flight.number}.`, `
      <div class="notice">${requested <= count ? "All requested passengers can be held." : `Only ${count} of the ${requested} requested seats are available. Choose whether to take the partial hold or fail the full group.`}</div>
      <label class="form-field" style="margin:14px 0">Fare rule<select id="hold-fare" class="select"><option>Flexible</option><option>Basic Economy</option><option>Refundable</option><option>Credit-only</option><option>Non-refundable</option></select></label>
      <label class="form-field" style="margin:10px 0">Contact email<input id="hold-email" type="email" required value="${esc(remote.user?.email || "")}" placeholder="traveler@example.com"></label>
      <label class="form-field" style="margin:10px 0">Passenger names · one per line<textarea id="hold-passengers" class="field" rows="3" style="height:auto;padding:9px" required>${esc(defaultNames)}</textarea></label>
      <div class="button-row" style="justify-content:flex-end"><button class="btn" data-action="close-modal">Full failure</button><button class="btn btn-primary" data-action="confirm-hold" data-flight="${esc(flightId)}" data-class="${cabin}" data-count="${Math.min(requested, count)}">${requested > count ? `Hold partial group (${count})` : `Hold ${requested} seat${requested > 1 ? "s" : ""}`}</button></div>`);
  }
  async function confirmHold(button) {
    const flight = flightById(button.dataset.flight);
    const cabin = button.dataset.class;
    const count = Number(button.dataset.count);
    if (!flight || available(flight, cabin) < count) { closeModal(); return toast("Inventory changed before hold; search again.", true); }
    const fare = document.querySelector("#hold-fare")?.value || "Flexible";
    const email = document.querySelector("#hold-email")?.value.trim();
    const passengers = document.querySelector("#hold-passengers")?.value.split(/\r?\n/).map((name) => name.trim()).filter(Boolean) || [];
    if (!email || passengers.length < count) return toast(`Enter a contact email and at least ${count} distinct passenger name(s).`, true);
    if (new Set(passengers.slice(0, count).map((name) => name.toLowerCase())).size !== count) return toast("Passenger names must be unique.", true);
    if (remote.connected) {
      try {
        const response = await apiRequest("/api/holds", {
          method: "POST",
          body: {
            flight_id: Number(flight.id),
            cabin,
            fare_rule: apiFare(fare),
            passengers: passengers.slice(0, count).map((name) => ({ name })),
            email,
            group_behavior: button.dataset.count < flightSearch.passengers ? "partial" : "all_or_nothing",
          },
        });
        closeModal(); await refreshRemote({ keepMessage: true });
        toast(`Seats held in PostgreSQL until ${formatTime(response.expires_at)}; continue to secure payment.`);
      } catch (error) { toast(error.message, true); }
      return;
    }
    const idempotencyKey = uid("IDEM");
    const existingKey = state.holds.find((hold) => hold.idempotencyKey === idempotencyKey);
    if (existingKey) return toast(`Duplicate request safely ignored (${existingKey.id}).`);
    const price = flight.prices[cabin];
    const selectedPassengers = passengers.slice(0, count);
    const hold = { id: uid("HD"), flightId: flight.id, passenger: selectedPassengers[0], passengers: selectedPassengers, email, class: cabin, fare, status: "Held", amount: price * count, priceEach: price, idempotencyKey, expiresAt: Date.now() + 15 * 60 * 1000 };
    state.holds.unshift(hold);
    log("Created seat and price hold", `${flight.number} · ${cabin}`, `${count} seat(s), ${fare}, ${money(hold.amount)} held for 15 minutes. Idempotency key ${idempotencyKey}; inventory reserved atomically in this browser demo.`);
    save(); closeModal(); toast(`${count} seat(s) held for 15 minutes.`);
    currentView = "bookings"; render();
  }
  function renderBookings() {
    const list = state.bookings.filter((booking) => `${booking.id} ${booking.passenger} ${booking.email}`.toLowerCase().includes(bookingsFilter.toLowerCase()));
    const holdRows = state.holds.filter((hold) => hold.status === "Held");
    main.innerHTML = `${pageHeading("Bookings & checkout", "Manage confirmed passengers, active price holds, refunds, and fare-aware cancellations.", `<button class="btn" data-view="search">⌕ Search flights</button>`)}
      <section class="card" style="margin-bottom:15px"><div class="card-head"><div><h2>Active checkout holds</h2><p>15-minute holds protect both inventory and quoted fare until payment is confirmed.</p></div><span class="integration-status">Payment gateway not connected</span></div><div class="table-wrap"><table><thead><tr><th>Hold</th><th>Passenger(s)</th><th>Flight / class</th><th>Fare held</th><th>Expires</th><th>Action</th></tr></thead><tbody>${holdRows.length ? holdRows.map((hold) => { const flight = flightById(hold.flightId); const left = Math.max(0, Math.ceil((hold.expiresAt - Date.now()) / 60000)); return `<tr><td class="flight-code">${esc(hold.id)}</td><td>${esc(hold.passengers.join(", "))}<span class="muted-cell">${hold.passengers.length} passenger(s)</span></td><td>${esc(flight?.number || "Flight removed")} · ${esc(hold.class)}</td><td>${money(hold.amount)}<span class="muted-cell">${esc(hold.fare)} · price held</span></td><td>${left ? `${left} min` : "Expired"}</td><td><div class="row-actions"><button class="btn btn-small btn-primary" data-action="confirm-payment" data-id="${esc(hold.id)}" ${hold.expiresAt <= Date.now() ? "disabled" : ""}>Confirm payment</button><button class="btn btn-small btn-danger" data-action="release-hold" data-id="${esc(hold.id)}">Release</button></div></td></tr>`; }).join("") : tableEmpty(6, "Search for a flight to create a checkout hold.")}</tbody></table></div></section>
      <div class="toolbar-row"><div><h2 style="margin:0;font:700 15px Manrope">Passenger bookings</h2><p class="heading-subtitle">Partial cancellation re-prices remaining passengers and applies the booked fare rule.</p></div><input class="field search-field" id="booking-filter" placeholder="Search booking or passenger…" value="${esc(bookingsFilter)}"></div>
      <section class="card"><div class="table-wrap"><table><thead><tr><th>Booking</th><th>Passenger(s)</th><th>Flight</th><th>Class / fare</th><th>Status</th><th>Amount</th><th>Actions</th></tr></thead><tbody>${list.length ? list.map((booking) => { const flight = flightById(booking.flightId); return `<tr><td class="flight-code">${esc(booking.id)}<span class="muted-cell">${formatDate(booking.createdAt, { year: "numeric" })}</span></td><td>${esc(booking.passenger)}<span class="muted-cell">${booking.passengers.length} passenger(s)</span></td><td>${esc(flight?.number || "Flight unavailable")}<span class="muted-cell">${esc(flight?.originCode || "")} → ${esc(flight?.destinationCode || "")}</span></td><td>${esc(booking.class)}<span class="muted-cell">${esc(booking.fare)}</span></td><td>${statusPill(booking.status)}${booking.changeNotice ? `<span class="muted-cell">${esc(booking.changeNotice)}</span>` : ""}</td><td>${money(booking.farePrice * booking.passengers.length)}${booking.creditExpires ? `<span class="muted-cell">Credit expires ${formatDate(booking.creditExpires, { year: "numeric" })}</span>` : ""}</td><td>${booking.status === "Confirmed" ? `<button class="btn btn-small" data-action="policy-answer" data-id="${esc(booking.id)}">Draft policy answer</button> <button class="btn btn-small btn-danger" data-action="cancel-booking" data-id="${esc(booking.id)}">Cancel passenger(s)</button>` : booking.status === "Rebooking required" ? `<button class="btn btn-small" data-action="resolve-rebooking" data-id="${esc(booking.id)}">Resolve rebooking</button>` : "—"}</td></tr>`; }).join("") : tableEmpty(7, "No bookings match this search.")}</tbody></table></div></section>
      <section class="card" style="margin-top:15px"><div class="card-head"><div><h2>Refund queue</h2><p>${remote.connected ? "Update payment-provider outcomes and retain the resolution reason in PostgreSQL audit history." : "Escalation after 3 days in this demo; scheduled Gmail delivery is simulated."}</p></div><button class="btn btn-small" data-action="run-automation" data-job="refunds">Run escalation check</button></div><div class="table-wrap"><table><thead><tr><th>Refund</th><th>Booking</th><th>Passenger</th><th>Amount</th><th>Created</th><th>Status</th><th>Resolution</th></tr></thead><tbody>${state.refunds.length ? state.refunds.map((refund) => `<tr><td class="flight-code">${esc(refund.id)}</td><td>${esc(refund.bookingId)}</td><td>${esc(refund.passenger)}</td><td>${money(refund.amount)}</td><td>${elapsed(refund.createdAt)}</td><td>${statusPill(refund.status)}</td><td>${["Processing", "Pending"].includes(refund.status) ? `<button class="btn btn-small" data-action="resolve-refund" data-id="${esc(refund.id)}" data-status="succeeded">Mark paid</button> <button class="btn btn-small btn-danger" data-action="resolve-refund" data-id="${esc(refund.id)}" data-status="failed">Mark failed</button>` : "—"}</td></tr>`).join("") : tableEmpty(7, "No refunds to process.")}</tbody></table></div></section>`;
  }
  function cancelBooking(id) {
    const booking = state.bookings.find((item) => item.id === id);
    if (!booking || booking.status !== "Confirmed") return toast("Booking is no longer cancellable.", true);
    openModal(`Cancel passengers · ${esc(booking.id)}`, "Cancellation terms are applied to the actual fare purchased. This demo does not issue payment refunds.", `
      <form id="cancel-booking-form"><p class="heading-subtitle">Fare purchased: <strong>${esc(booking.fare)}</strong> · ${money(booking.farePrice)} per passenger · ${booking.passengers.length} passenger(s)</p>
      <div class="passenger-checks">${booking.passengers.map((passenger, index) => `<label class="passenger-check"><input type="checkbox" name="passengers" value="${index}" checked> ${esc(passenger)}</label>`).join("")}</div>
      <label class="form-field">Cancellation treatment<select name="treatment"><option value="auto">Apply fare policy</option><option value="refund">Refund exception (human approval)</option><option value="credit">Travel credit (12-month expiry)</option></select></label>
      <div class="notice" style="margin-top:12px">Refundable: prorated refund. Credit-only: credit with expiry. Non-refundable / Basic Economy: no voluntary refund. Remaining fare is repriced after partial cancellation.</div>
      <div class="form-actions"><button type="button" class="btn" data-action="close-modal">Keep booking</button><button class="btn btn-danger" type="submit">Cancel selected</button></div></form>`);
    document.querySelector("#cancel-booking-form").dataset.bookingId = id;
  }
  async function processCancelBooking(form) {
    const booking = state.bookings.find((item) => item.id === form.dataset.bookingId);
    if (!booking) return toast("Booking could not be found.", true);
    const indexes = [...form.querySelectorAll('input[name="passengers"]:checked')].map((item) => Number(item.value));
    if (!indexes.length) return toast("Select at least one passenger to cancel.", true);
    const selected = indexes.map((index) => booking.passengers[index]).filter(Boolean);
    if (!selected.length) return toast("The selected passengers are no longer on this booking.", true);
    const treatment = new FormData(form).get("treatment");
    if (remote.connected) {
      try {
        const treatmentMap = { auto: "apply_fare_rule", refund: "refund_exception", credit: "travel_credit" };
        const result = await apiRequest(`/api/bookings/${encodeURIComponent(booking.id)}/cancel`, {
          method: "POST",
          body: { passenger_names: selected, treatment: treatmentMap[treatment] },
        });
        closeModal(); await refreshRemote({ keepMessage: true });
        toast(`${selected.length} passenger(s) cancelled · ${result.resolution}.`);
      } catch (error) { toast(error.message, true); }
      return;
    }
    let refund = 0;
    let decision = "No voluntary refund under purchased fare rule";
    if (treatment === "refund") {
      state.approvals.unshift({ id: uid("AP"), type: "Refund exception", subject: `Booking ${booking.id} · ${booking.passenger}`, detail: "Refund exception requested; human review required.", amount: booking.farePrice * selected.length, status: "Pending", createdAt: Date.now(), source: "Booking cancellation" });
      decision = "Refund exception sent for human approval";
    } else if (treatment === "credit" || booking.fare === "Credit-only") {
      booking.creditAmount = booking.farePrice * selected.length;
      booking.creditExpires = new Date(Date.now() + 365 * 86400000).toISOString();
      decision = "Travel credit issued · expires in 12 months";
    } else if (booking.fare === "Refundable" || booking.fare === "Flexible") {
      refund = booking.farePrice * selected.length;
      state.refunds.unshift({ id: uid("RF"), bookingId: booking.id, passenger: selected.join(", "), amount: refund, status: "Processing", createdAt: Date.now() });
      decision = "Standard in-policy refund auto-approved";
    }
    booking.passengers = booking.passengers.filter((name) => !selected.includes(name));
    booking.passenger = booking.passengers[0] || selected[0];
    booking.status = booking.passengers.length ? "Confirmed" : "Cancelled";
    booking.refundDecision = decision;
    booking.farePrice = Math.round(booking.farePrice * (booking.passengers.length ? 1.02 : 1) * 100) / 100;
    log(refund ? "Auto-approved in-policy refund" : "Processed passenger cancellation", `${booking.id} · ${selected.join(", ")}`, `${decision}. ${selected.length} of original passengers cancelled; remaining booking re-priced to ${money(booking.farePrice)} per passenger.`);
    save(); closeModal(); toast(refund ? `${money(refund)} refund queued (demo).` : decision); render();
  }
  async function confirmPayment(holdId) {
    const hold = state.holds.find((item) => item.id === holdId && item.status === "Held");
    if (!hold) return toast("Hold not found or already used.", true);
    if (hold.expiresAt <= Date.now()) { hold.status = "Expired"; save(); render(); return toast("The price hold expired; search and book again.", true); }
    if (remote.connected) {
      try {
        const checkout = await apiRequest(`/api/holds/${encodeURIComponent(hold.id)}/checkout`, { method: "POST", body: {} });
        window.location.assign(checkout.checkout_url);
      } catch (error) { toast(error.message, true); }
      return;
    }
    const flight = flightById(hold.flightId);
    if (!flight || flight.status === "Cancelled" || available(flight, hold.class) + hold.passengers.length < hold.passengers.length) return toast("Flight or inventory changed; hold cannot be confirmed.", true);
    const existing = state.bookings.find((booking) => booking.idempotencyKey === hold.idempotencyKey);
    if (existing) { hold.status = "Confirmed"; save(); return toast(`Retry safely returned existing booking ${existing.id}.`); }
    const booking = { id: uid("BK"), flightId: hold.flightId, passenger: hold.passengers[0], email: hold.email, passengers: [...hold.passengers], class: hold.class, fare: hold.fare, status: "Confirmed", createdAt: Date.now(), farePrice: hold.priceEach, idempotencyKey: hold.idempotencyKey };
    state.bookings.unshift(booking);
    hold.status = "Confirmed";
    log("Confirmed booking", `${booking.id} · ${flight.number}`, `${booking.passengers.length} seat(s), ${booking.fare} fare, ${money(booking.farePrice * booking.passengers.length)}. Same idempotency key returns this booking. Transactional Gmail confirmation is not connected.`);
    save(); render(); toast(`Booking ${booking.id} confirmed (demo).`);
  }
  function renderWaitlist() {
    const rows = state.waitlist.slice().sort((a, b) => {
      const loyalty = { Platinum: 3, Gold: 2, Silver: 1, Standard: 0 };
      return (loyalty[b.loyalty] - loyalty[a.loyalty]) || (a.joinedAt - b.joinedAt);
    });
    main.innerHTML = `${pageHeading("Waitlist & standby", "Manage priority, claim windows, and safe promotion when seats become available.", `<button class="btn btn-primary" data-action="add-waitlist">＋ Add passenger</button>`)}
      <div class="notice" style="margin-bottom:14px"><span>⇄</span><span><strong>Priority:</strong> loyalty tier (Platinum → Gold → Silver → Standard), then earliest join time. Promotion creates a 30-minute claim window; on expiry, the seat is released to the next eligible passenger. Seat assignment is atomic in this single-user demo.</span></div>
      <div class="toolbar-row"><span class="heading-subtitle">${rows.filter((row) => row.status === "Waiting").length} waiting · ${rows.filter((row) => row.status === "Claim window").length} in claim window</span><button class="btn" data-action="promote-waitlist">⇧ Promote next eligible</button></div>
      <section class="card"><div class="table-wrap"><table><thead><tr><th>Priority</th><th>Passenger</th><th>Flight / class</th><th>Loyalty</th><th>Joined</th><th>Status</th><th>Claim deadline</th><th>Action</th></tr></thead><tbody>${rows.length ? rows.map((entry, index) => { const flight = flightById(entry.flightId); const canPromote = entry.status === "Waiting" && available(flight, entry.class) > 0; return `<tr><td><span class="waitlist-rank">${index + 1}</span></td><td>${esc(entry.passenger)}</td><td>${esc(flight?.number || "Flight removed")} · ${esc(entry.class)}</td><td>${esc(entry.loyalty)}</td><td>${elapsed(entry.joinedAt)}</td><td>${statusPill(entry.status)}</td><td>${entry.status === "Claim window" ? `${Math.max(0, Math.ceil((entry.claimUntil - Date.now()) / 60000))} min left` : "—"}</td><td>${entry.status === "Claim window" ? `<button class="btn btn-small btn-primary" data-action="claim-seat" data-id="${esc(entry.id)}">Claim seat</button>` : canPromote ? `<button class="btn btn-small" data-action="promote-one" data-id="${esc(entry.id)}">Promote</button>` : entry.status === "Waiting" ? `<span class="muted-cell">Awaiting seat</span>` : "—"}</td></tr>`; }).join("") : tableEmpty(8, "No passengers are waiting.")}</tbody></table></div></section>
      <section class="card" style="margin-top:15px"><div class="card-head"><div><h2>Promotion policy</h2><p>n8n scheduled promotions are represented by the manual demo trigger above.</p></div><span class="integration-status">${remote.connected ? "FastAPI database" : "n8n not connected"}</span></div><div class="card-body"><div class="flow-grid"><div class="flow-card"><span class="flow-icon">1</span><h3>Detect freed seat</h3><p>Read inventory from the ledger; canceled flight always blocks promotion.</p></div><div class="flow-card"><span class="flow-icon">2</span><h3>Lock &amp; offer</h3><p>Lock the waitlist row and seat in one transaction; SKIP LOCKED prevents double assignment.</p></div><div class="flow-card"><span class="flow-icon">3</span><h3>Claim or release</h3><p>Notify passenger, honor 30-minute window, then expire and offer the next eligible passenger.</p></div></div></div></section>`;
  }
  function addWaitlist() {
    const choices = state.flights.filter((flight) => flight.status !== "Cancelled");
    openModal("Add passenger to waitlist", "Join the cabin queue when a class is full or nearly full.", `<form id="waitlist-form" class="form-grid">
      <label class="form-field">Passenger name<input name="passenger" required placeholder="Taylor Morgan"></label><label class="form-field">Email<input name="email" type="email" required placeholder="traveler@example.com"></label>
      <label class="form-field">Flight<select name="flightId" required>${choices.map((flight) => `<option value="${esc(flight.id)}">${esc(flight.number)} · ${esc(flight.originCode)} → ${esc(flight.destinationCode)}</option>`).join("")}</select></label>
      <label class="form-field">Cabin<select name="class">${cabinOptions()}</select></label>
      <label class="form-field">Loyalty tier<select name="loyalty"><option>Standard</option><option>Silver</option><option>Gold</option><option>Platinum</option></select></label>
      <label class="form-field">Fare preference<select name="fare"><option>Flexible</option><option>Basic Economy</option><option>Refundable</option></select></label>
      <div class="form-actions form-full"><button type="button" class="btn" data-action="close-modal">Cancel</button><button class="btn btn-primary" type="submit">Join waitlist</button></div>
    </form>`);
  }
  function promoteEntry(entry) {
    if (!entry || entry.status !== "Waiting") return toast("This waitlist entry is no longer eligible.", true);
    const flight = flightById(entry.flightId);
    if (!flight || flight.status === "Cancelled" || available(flight, entry.class) <= 0) return toast("No seat is available; the passenger remains on the waitlist.", true);
    entry.status = "Claim window";
    entry.claimUntil = Date.now() + 30 * 60 * 1000;
    entry.promotedAt = Date.now();
    log("Waitlist seat offered", `${entry.passenger} · ${flight.number} ${entry.class}`, "Seat reserved for a 30-minute notification/claim window. Single-writer seat check prevents gate-agent / automation double assignment.");
    save(); render(); toast(`Seat offer sent to ${entry.passenger} (simulated).`);
  }
  async function claimSeat(id) {
    const entry = state.waitlist.find((item) => item.id === id && item.status === "Claim window");
    const flight = entry && flightById(entry.flightId);
    if (!entry || entry.claimUntil <= Date.now() || !flight || flight.status === "Cancelled") return toast("Claim window expired or the flight was cancelled.", true);
    if (remote.connected) {
      try {
        const result = await apiRequest(`/api/waitlist/${encodeURIComponent(entry.id)}/claim`, { method: "POST", body: {} });
        await refreshRemote({ keepMessage: true });
        toast(`Seat claimed; booking ${result.booking.reference} created.`);
      } catch (error) { toast(error.message, true); }
      return;
    }
    if (available(flight, entry.class) + 1 <= 0) return toast("Seat is no longer available; contact operations.", true);
    const booking = { id: uid("BK"), flightId: entry.flightId, passenger: entry.passenger, email: entry.email, passengers: [entry.passenger], class: entry.class, fare: entry.fare, status: "Confirmed", createdAt: Date.now(), farePrice: flight.prices[entry.class], idempotencyKey: `waitlist-${entry.id}` };
    state.bookings.unshift(booking);
    entry.status = "Claimed";
    entry.bookingId = booking.id;
    log("Waitlist promotion claimed", `${entry.passenger} · ${flight.number}`, `Booking ${booking.id} created; fare ${entry.fare}; idempotency key prevents duplicate promotion.`);
    save(); render(); toast(`Seat claimed; booking ${booking.id} created.`);
  }
  function expireTimedItems() {
    let changed = false;
    for (const hold of state.holds) if (hold.status === "Held" && hold.expiresAt <= Date.now()) { hold.status = "Expired"; changed = true; }
    for (const entry of state.waitlist) if (entry.status === "Claim window" && entry.claimUntil <= Date.now()) { entry.status = "Waiting"; entry.claimUntil = null; changed = true; log("Waitlist claim window expired", `${entry.passenger} · ${flightById(entry.flightId)?.number || entry.flightId}`, "Seat released to the next waitlisted passenger; scheduled customer notice simulated."); }
    if (changed) { save(); if (currentView === "bookings" || currentView === "waitlist") render(); }
  }
  function renderApprovals() {
    const items = [...state.approvals].sort((a, b) => (a.status === "Pending" ? -1 : 1) - (b.status === "Pending" ? -1 : 1));
    main.innerHTML = `${pageHeading("Approval center", "A clear boundary between routine automation and decisions that need human judgment.", "")}
      <div class="dashboard-grid"><section class="card"><div class="card-head"><div><h2>Human sign-off queue</h2><p>${items.filter((item) => item.status === "Pending").length} decisions awaiting review · no customer email sent before approval</p></div></div><div class="card-body">${items.length ? items.map((item) => `<div class="booking-detail"><div><strong>${esc(item.type)}</strong><p class="heading-subtitle" style="margin:4px 0">${esc(item.subject)}</p><p class="heading-subtitle">${esc(item.detail)}</p><small class="muted-cell">${esc(item.source)} · ${elapsed(item.createdAt)} ${item.amount ? `· ${money(item.amount)}` : ""}</small></div><div>${statusPill(item.status)}${item.status === "Pending" ? `<div class="button-row" style="margin-top:8px"><button class="btn btn-small btn-primary" data-action="approve-item" data-id="${esc(item.id)}">Approve</button><button class="btn btn-small btn-danger" data-action="reject-item" data-id="${esc(item.id)}">Reject</button></div>` : ""}</div></div>`).join("") : `<div class="empty-state">No approval cases yet.</div>`}</div></section>
      <section class="card"><div class="card-head"><div><h2>Approval boundaries</h2><p>Decision lists are explicit and auditable.</p></div></div><div class="card-body"><h3 style="font-size:11px;color:var(--green)">Auto-approved (within policy)</h3><div class="activity-list"><div class="activity-item"><span class="activity-mark">✓</span><div class="activity-copy"><strong>Check-in reminders</strong><small>Scheduled notice only; cancelled flights suppressed.</small></div></div><div class="activity-item"><span class="activity-mark">✓</span><div class="activity-copy"><strong>Standard in-policy refunds</strong><small>Fare rules verified; record rationale and amount.</small></div></div><div class="activity-item"><span class="activity-mark">✓</span><div class="activity-copy"><strong>Waitlist notices</strong><small>Offer is temporary; promotion is recorded.</small></div></div></div><div class="divider"></div><h3 style="font-size:11px;color:var(--amber)">Human approval required</h3><div class="activity-list"><div class="activity-item"><span class="activity-mark">!</span><div class="activity-copy"><strong>Schedule-change compensation</strong><small>Review disruption, eligibility, and fare-policy overrides.</small></div></div><div class="activity-item"><span class="activity-mark">!</span><div class="activity-copy"><strong>Denied-boarding compensation</strong><small>Verify incident evidence and applicable regulation.</small></div></div><div class="activity-item"><span class="activity-mark">!</span><div class="activity-copy"><strong>RAG-drafted policy answers</strong><small>Human review required before Gmail delivery.</small></div></div></div></div></section></div>`;
  }
  function renderAutomations() {
    const jobs = [
      ["Check-in reminders", "Send timezone-correct reminders using origin airport local time; suppress cancelled flights.", "reminders", "◷"],
      ["Price-drop alerts", "Compare against a material threshold, then deduplicate by passenger, route, and offer.", "prices", "↓"],
      ["Daily operations report", "Calculate load factor and revenue per flight from the booking ledger.", "report", "▤"],
      ["Refund escalation", "Escalate unresolved refunds after the configurable 3-day threshold.", "refunds", "↗"],
      ["Recent booking fraud scan", "Score recent bookings for bot / mass-booking signals; flag for investigator review.", "fraud-recent", "⌕"],
      ["Historical fraud batch", "Review past bookings missed by real-time scoring; produce review cases.", "fraud-history", "▦"],
      ["Policy document ingestion", "Detect updated policy docs and schedule embeddings for the policy index.", "ingest", "⌁"],
      ["Waitlist promotion", "Find freed seats, lock eligible waitlist rows, and open a timed claim window.", "waitlist", "⇧"],
    ];
    main.innerHTML = `${pageHeading("Scheduled automations", "Workflow catalog and manual triggers for exploring scheduled n8n-style behavior.", `<span class="integration-status">n8n not connected</span>`)}
      <div class="notice warn" style="margin-bottom:15px"><span>ⓘ</span><span>Triggers below write demo records to this browser only. No Gmail messages, PostgreSQL queries, fraud scores, or Pinecone embeddings are actually executed.</span></div>
      <div class="flow-grid">${jobs.map(([title, description, job, icon]) => `<article class="flow-card"><span class="flow-icon">${icon}</span><h3>${title}</h3><p>${description}</p><div class="divider"></div><div style="display:flex;align-items:center;justify-content:space-between;gap:8px"><span class="integration-status">Simulated</span><button class="btn btn-small" data-action="run-automation" data-job="${job}">Run demo job</button></div></article>`).join("")}</div>
      <section class="card" style="margin-top:16px"><div class="card-head"><div><h2>Most recent run</h2><p>${state.lastAutomation ? `${esc(state.lastAutomation.name)} · ${elapsed(state.lastAutomation.at)}` : "No jobs have been triggered this session."}</p></div></div><div class="card-body">${state.lastAutomation ? `<div class="notice success"><span>✓</span><span>${esc(state.lastAutomation.result)}<br><small>${esc(state.lastAutomation.note)}</small></span></div>` : `<div class="empty-state">Choose a job above to simulate a scheduled run.</div>`}</div></section>`;
  }
  async function runAutomation(job) {
    if (remote.connected) {
      const workflows = {
        reminders: "checkin_reminders",
        prices: "price_drop_alerts",
        report: "operations_report",
        refunds: "refund_escalation",
        "fraud-recent": "fraud_recent",
        "fraud-history": "fraud_historical",
        ingest: "policy_ingestion",
        waitlist: "waitlist_promotion",
      };
      try {
        const result = await apiRequest(`/api/automations/${workflows[job]}`, { method: "POST", body: {} });
        await refreshRemote({ keepMessage: true });
        toast(`${result.workflow} completed; ${result.processed} item(s) processed.`);
      } catch (error) { toast(error.message, true); }
      return;
    }
    const now = Date.now();
    let name = "Automation job";
    let result = "Completed simulated workflow.";
    let note = "No external system was called.";
    if (job === "reminders") {
      name = "Check-in reminders";
      const eligible = state.bookings.filter((booking) => booking.status === "Confirmed" && flightById(booking.flightId)?.status !== "Cancelled");
      result = `${eligible.length} active booking(s) evaluated; cancelled flights suppressed.`;
      note = "Reminder timing uses departure date and origin timezone; email delivery is not connected.";
    } else if (job === "prices") {
      name = "Price-drop alerts";
      const candidates = state.flights.filter((flight) => flight.status !== "Cancelled");
      const threshold = 10;
      let sent = 0;
      candidates.forEach((flight) => {
        for (const cabin of ["First", "Business", "Economy"]) {
          const key = `${flight.id}:${cabin}`;
          const prior = state.priceAlerts.find((alert) => alert.key === key);
          if (prior && prior.lastPrice - flight.prices[cabin] >= threshold && prior.lastNotifiedPrice !== flight.prices[cabin]) {
            prior.lastNotifiedPrice = flight.prices[cabin]; prior.lastSentAt = now; sent += 1;
          } else if (!prior) state.priceAlerts.push({ key, lastPrice: flight.prices[cabin], lastNotifiedPrice: flight.prices[cabin], lastSentAt: now });
          else prior.lastPrice = flight.prices[cabin];
        }
      });
      result = `${sent} material price-drop alert(s) simulated; changes below ${money(threshold)} are deduplicated.`;
      note = "Alerts are keyed by flight/cabin and notification price; no Gmail message sent.";
    } else if (job === "report") {
      name = "Daily operations report";
      const totals = state.flights.filter((flight) => flight.status !== "Cancelled").map((flight) => {
        const passengers = totalBooked(flight.id);
        const revenue = state.bookings.filter((booking) => booking.flightId === flight.id && booking.status === "Confirmed").reduce((sum, booking) => sum + booking.farePrice * booking.passengers.length, 0);
        return `${flight.number}: ${Math.round(passengers / flight.capacity * 100)}% load, ${money(revenue)} revenue`;
      });
      result = totals.join(" · ") || "No active flights to report.";
      note = "Report data is derived from the local booking and flight ledger; PostgreSQL is not connected.";
    } else if (job === "refunds") {
      name = "Stuck-refund escalation";
      const stuck = state.refunds.filter((refund) => refund.status === "Processing" && now - refund.createdAt >= 3 * 86400000);
      result = `${stuck.length} unresolved refund(s) exceed the 3-day threshold${stuck.length ? `: ${stuck.map((item) => item.id).join(", ")}` : ""}.`;
      note = "Escalation notification is logged, not emailed.";
      if (stuck.length) log("Refund escalation triggered", stuck.map((item) => item.id).join(", "), "Unresolved beyond configurable 3-day threshold; n8n Gmail notification simulated.");
    } else if (job === "fraud-recent" || job === "fraud-history") {
      name = job === "fraud-recent" ? "Recent booking fraud scan" : "Historical fraud batch review";
      const rows = job === "fraud-recent" ? state.bookings.filter((booking) => now - booking.createdAt < 7 * 86400000) : state.bookings;
      const flagged = rows.filter((booking) => booking.passengers.length >= 5 || /test|bot/i.test(booking.email || ""));
      result = `${rows.length} booking(s) scanned; ${flagged.length} potential risk signal(s) flagged for human review.`;
      note = "Sample heuristic only—not a fraud decision or real model score. Pinecone is not connected.";
    } else if (job === "ingest") {
      name = "Policy document ingestion";
      result = "No policy documents configured; ingestion is ready for a document source.";
      note = "A scheduled pipeline would version documents and upsert embeddings to Pinecone; no embedding was created.";
    } else if (job === "waitlist") {
      name = "Waitlist promotion";
      const entry = sortedWaitingEntry();
      if (entry) { promoteEntry(entry); return; }
      result = "No waiting passenger currently has an available seat.";
      note = "Promotion claim window is 30 minutes; PostgreSQL SKIP LOCKED is documented but not implemented in this browser demo.";
    }
    state.lastAutomation = { name, result, note, at: now };
    log("Simulated automation run", name, `${result} ${note}`);
    save(); render(); toast(`${name} completed in demo mode.`);
  }
  function sortedWaitingEntry() {
    const loyalty = { Platinum: 3, Gold: 2, Silver: 1, Standard: 0 };
    return state.waitlist.filter((entry) => entry.status === "Waiting" && available(flightById(entry.flightId), entry.class) > 0).sort((a, b) => (loyalty[b.loyalty] - loyalty[a.loyalty]) || (a.joinedAt - b.joinedAt))[0];
  }
  const requirementGroups = [
    ["Admin & flight management", ["Create a flight with route, flight number, and departure/arrival.", "Allocate First, Business, and Economy seats.", "Validate cabin total equals aircraft capacity.", "Reject negative, zero, fractional cabin counts.", "Edit route/schedule and cascade booking notices.", "Cancel a flight and choose refund, rebooking, or credit.", "Generate a class-specific illustrative physical seat map.", "Prevent reducing cabin capacity below booked / held count.", "Detect duplicate flight number for same date and route.", "Separate super-admin and operations-agent permissions.", "Audit every flight change with actor, action, detail, and timestamp."]],
    ["Search & fare rules", ["Search route/date and show available seats by cabin.", "Display fare rules for Basic Economy and flexible fares.", "Hold quoted price for 15 minutes at checkout.", "Define atomic all-legs-or-none itinerary holds as a backend requirement.", "Format displayed prices with selectable currency and locale."]],
    ["Seat holds & booking", ["Temporarily hold group inventory; expire after 15 minutes.", "Explicit auto-approval list: reminders, standard in-policy refunds, waitlist notices.", "Explicit human sign-off list: schedule changes, denied boarding, RAG responses."]],
    ["Approval & audit boundaries", ["Audit decision rationale, actor, time, fare rule, evidence, amount, and workflow for review."]],
    ["Shared database architecture", ["Define sole-writer ownership by table and system.", "Specify PostgreSQL CHECK, FK, enum, and row-lock constraints.", "Use n8n polling/outbox status to detect work; prefer durable polling over ephemeral notifications.", "Claim jobs using FOR UPDATE SKIP LOCKED and short transactions.", "Run reconciliation for failed and partial workflow writes.", "Resolve cancellation vs. promotion by transactional status/seat lock; cancellation wins."]],
    ["Core infrastructure", ["Type and validate every booking-affecting FastAPI request/response.", "Require an idempotency key for every write and return prior result on retry.", "Supabase PostgreSQL is the sole flight/seat/booking ledger.", "Schedule Pinecone maintenance for policy and fraud embeddings.", "Use n8n Gmail for scheduled notifications.", "Use FastAPI Gmail for request-triggered transactional mail."]],
    ["Booking & inventory concurrency", ["Decrement cabin inventory atomically in PostgreSQL.", "Protect duplicate/retry booking writes with idempotency keys.", "Hard never-oversell policy by cabin; buffer is set to zero.", "Group booking offers explicit partial hold or full failure.", "Apply cabin-specific booking cutoffs."]],
    ["Changes, cancellations & refunds", ["Branch cancellation policy by refundable, credit-only, or non-refundable fare.", "Support selected passengers, proportional refund, and remaining booking re-price.", "Airline schedule changes permit rebooking and fare-policy override review.", "Flight cancellation offers refund, rebooking, or 12-month travel credit.", "Escalate unresolved refunds after a configurable 3 days."]],
    ["Waitlist & standby", ["Add passengers to flight and cabin waitlist.", "Sort by loyalty tier then earliest join time.", "Simulate promotion when a seat is available.", "Open a 30-minute claim window before releasing seat onward.", "Serialize gate-agent and automation seat assignment; database row lock needed in production."]],
    ["Scheduled automations", ["Origin-timezone check-in reminder with cancelled-flight suppression.", "Price-drop alert dedupe with $10 materiality threshold.", "Daily load-factor and revenue-per-flight operations report.", "Suppress reminders for cancelled flights."]],
    ["Fraud, policy & RAG", ["Answer policy using the booking's actual fare rule.", "Human-approve RAG answer before customer Gmail.", "Schedule recent-booking fraud scoring.", "Ingest changed policy docs and update Pinecone.", "Batch review historical bookings for missed fraud signals."]],
  ];
  function renderRequirements() {
    let number = 0;
    main.innerHTML = `${pageHeading("Feature coverage", "The complete 56-point scope, mapped to the working demo and production integration boundaries.", `<button class="btn" data-action="reset-demo">Reset demo data</button>`)}
      <div class="notice warn" style="margin-bottom:15px"><span>ⓘ</span><span>This is a front-end prototype. It demonstrates interactions using localStorage, not a live backend. FastAPI, Supabase PostgreSQL, n8n, Gmail, Pinecone, payment, and production concurrency controls require a separate service implementation.</span></div>
      ${requirementGroups.map(([group, requirements]) => `<details class="card coverage-group" open><summary>${esc(group)} <span class="muted-cell" style="display:inline;margin-left:6px">${requirements.length} items</span></summary><ol>${requirements.map((requirement) => { number += 1; const owner = /n8n|scheduled|Pinecone|Gmail|automation|fraud|RAG/i.test(requirement) ? "n8n" : /audit|PostgreSQL|database|Supabase|row.lock|cancellation vs|decision rationale/i.test(requirement) ? "both" : "FastAPI"; return `<li value="${number}"><span class="tag ${owner}">[${owner}]</span>${esc(requirement)}</li>`; }).join("")}</ol></details>`).join("")}
      <section class="card" style="margin-top:15px"><div class="card-head"><div><h2>Production database ownership contract</h2><p>Reference boundary to carry into the FastAPI + Supabase + n8n implementation.</p></div><span class="integration-status">Architecture proposal</span></div><div class="table-wrap"><table class="ledger-table"><thead><tr><th>Table / domain</th><th>Sole writer</th><th>Other system access</th><th>Conflict / invariant</th></tr></thead><tbody>
      <tr><td>flights, seat_inventory, bookings, booking_passengers, idempotency_keys</td><td>FastAPI</td><td>n8n read-only</td><td>FKs, enums, CHECKs, serializable/row-locked seat updates; cancellation blocks promotion.</td></tr>
      <tr><td>waitlist_entries, seat_holds</td><td>FastAPI owns mutations</td><td>n8n claims promotion job via narrow DB function</td><td>FOR UPDATE SKIP LOCKED; unique active seat/hold; expiry enforced in transaction.</td></tr>
      <tr><td>approvals, audit_events, refunds, travel_credits</td><td>FastAPI owns ledger; n8n writes only workflow outcome via restricted function</td><td>n8n claim/notification flags only</td><td>Append-only audit; status transition checks; request idempotency and reconciliation.</td></tr>
      <tr><td>automation_outbox, automation_runs, notification_jobs</td><td>n8n owns job status; FastAPI writes outbox events</td><td>FastAPI reads status</td><td>Polling with SKIP LOCKED, leases, retry count, dead-letter status; reconcile orphaned work.</td></tr>
      <tr><td>policy_documents, fraud_scores, price_alerts</td><td>n8n owns pipeline records and Pinecone sync metadata</td><td>FastAPI reads approved policy/fraud outcomes</td><td>Versioned upserts; no n8n direct writes to booking/inventory tables.</td></tr>
      </tbody></table></div><div class="card-body"><div class="notice"><span>↔</span><span><strong>Change detection:</strong> FastAPI commits an outbox row in the same transaction as its state change. n8n polls eligible rows, claims with <span class="mono">FOR UPDATE SKIP LOCKED</span>, and uses a lease/retry/dead-letter lifecycle. This is durable across worker restarts; PostgreSQL NOTIFY may wake workers but is not the source of truth.</span></div></div></section>`;
  }
  function renderAudit() {
    main.innerHTML = `${pageHeading("Audit & architecture", "Review who changed what and when; inspect the system-of-record and integration boundary.", `<button class="btn" data-action="export-audit">↓ Export audit CSV</button>`)}
      <div class="metric-grid"><div class="metric-card"><div class="metric-top">Audit events<span class="metric-icon">≡</span></div><strong class="metric-value">${state.audit.length}</strong><span class="metric-foot">append-only in this demo UI</span></div><div class="metric-card"><div class="metric-top">Write idempotency<span class="metric-icon">↻</span></div><strong class="metric-value">On</strong><span class="metric-foot">simulated request keys per operation</span></div><div class="metric-card"><div class="metric-top">Oversell buffer<span class="metric-icon">▣</span></div><strong class="metric-value">0</strong><span class="metric-foot">hard never-oversell policy by class</span></div><div class="metric-card"><div class="metric-top">Data source<span class="metric-icon">⌂</span></div><strong class="metric-value" style="font-size:18px">Browser</strong><span class="metric-foot">not PostgreSQL / Supabase</span></div></div>
      <div class="notice warn" style="margin-bottom:14px"><span>ⓘ</span><span><strong>Architecture honesty:</strong> This prototype does not establish a production audit trail, database-level invariants, distributed row locks, or durable idempotency. Those belong in the FastAPI/PostgreSQL service and restricted n8n database functions.</span></div>
      <section class="card"><div class="card-head"><div><h2>Change &amp; decision history</h2><p>Includes actor, action, target, detail/rationale, and timestamp.</p></div></div><div class="table-wrap"><table class="ledger-table"><thead><tr><th>Timestamp</th><th>Actor</th><th>Action</th><th>Target</th><th>Details / rationale</th></tr></thead><tbody>${state.audit.length ? state.audit.map((item) => `<tr><td>${new Intl.DateTimeFormat(state.locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.at))}</td><td>${esc(item.actor)}</td><td>${esc(item.action)}</td><td>${esc(item.target)}</td><td>${esc(item.detail)}</td></tr>`).join("") : tableEmpty(5, "No audit events yet.")}</tbody></table></div></section>
      <section class="card" style="margin-top:15px"><div class="card-head"><div><h2>Production responsibility map</h2><p>PostgreSQL remains the single ledger for live flights, seats, and bookings.</p></div></div><div class="card-body"><div class="meta-grid"><div class="meta-box"><small>FastAPI sole-writer tables</small><strong>Flights · seat inventory · bookings · holds · refunds · credits · idempotency</strong></div><div class="meta-box"><small>n8n workflow tables</small><strong>Outbox claims · automation runs · notification jobs · Pinecone sync metadata</strong></div><div class="meta-box"><small>n8n change detection</small><strong>Durable outbox polling; NOTIFY only as optional wake-up.</strong></div><div class="meta-box"><small>Concurrent conflict</small><strong>Seat + flight status locked in one transaction; cancellation wins before promotion.</strong></div><div class="meta-box"><small>Reconciliation</small><strong>Compare outbox, booking/refund states, promotion claims, and notification outcomes; alert on drift.</strong></div><div class="meta-box"><small>Transactional vs scheduled mail</small><strong>FastAPI Gmail for request-triggered mail; n8n Gmail for scheduled notices, with approval gate for RAG.</strong></div></div></div></section>`;
  }
  const renderers = { dashboard: renderDashboard, flights: renderFlights, search: renderSearch, bookings: renderBookings, waitlist: renderWaitlist, approvals: renderApprovals, automations: renderAutomations, audit: renderAudit, requirements: renderRequirements };
  const viewNames = { dashboard: "Overview", flights: "Flight management", search: "Search & book", bookings: "Bookings", waitlist: "Waitlist", approvals: "Approvals", automations: "Automations", audit: "Audit & architecture", requirements: "Feature coverage" };
  function render() {
    document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === currentView));
    document.querySelector("#breadcrumb-current").textContent = viewNames[currentView] || "Overview";
    document.querySelector("#role-label").textContent = state.role === "super-admin" ? "Super-admin" : "Operations agent";
    document.querySelector("#role-select").value = state.role;
    const pill = document.querySelector("#connection-pill");
    const connectButton = document.querySelector("#connect-api");
    if (pill) pill.innerHTML = `<i></i> ${remote.connected ? "PostgreSQL API" : "Demo data"}`;
    if (connectButton) connectButton.textContent = remote.connected ? "API connected" : "Connect API";
    if (remote.connected && state.role !== "super-admin" && state.role !== "ops-agent") {
      main.insertAdjacentHTML("afterbegin", `<div class="notice warn" style="margin-bottom:15px">This interface requires an admin account. Customer accounts can use the customer booking endpoints; staff access must be provisioned by a super-admin.</div>`);
    }
    (renderers[currentView] || renderDashboard)();
    updateBadges();
    document.querySelector("#mobile-menu").setAttribute("aria-expanded", String(document.querySelector("#sidebar").classList.contains("open")));
  }
  function navigate(view) {
    if (!renderers[view]) return;
    currentView = view;
    document.querySelector("#sidebar").classList.remove("open");
    render();
  }
  async function createPriceAlert(flightId, cabin) {
    const flight = flightById(flightId);
    if (!flight) return toast("Flight is no longer available.", true);
    const email = window.prompt("Email address for the price alert:");
    if (!email) return;
    const target = Number(window.prompt(`Alert when ${cabin} falls to or below:`, String(flight.prices[cabin] * 0.9)));
    if (!Number.isFinite(target) || target <= 0) return toast("Enter a valid target price.", true);
    if (remote.connected) {
      try {
        await apiRequest("/api/price-alerts", {
          method: "POST",
          body: { email, flight_id: Number(flightId), cabin, target_price: target, materiality_amount: 10 },
        });
        await refreshRemote({ keepMessage: true });
        toast("Price alert saved in PostgreSQL.");
      } catch (error) { toast(error.message, true); }
      return;
    }
    const duplicate = state.priceAlerts.some((alert) => alert.flightId === flightId && alert.cabin === cabin && alert.email.toLowerCase() === email.toLowerCase());
    if (duplicate) return toast("A price alert already exists for this flight and cabin.", true);
    state.priceAlerts.push({ key: `${flightId}:${cabin}:${email.toLowerCase()}`, flightId, cabin, email, targetPrice: target });
    save(); toast("Price alert saved in this browser demo.");
  }
  async function draftPolicyAnswer(id) {
    const booking = state.bookings.find((item) => item.id === id);
    if (!booking) return toast("Booking could not be found.", true);
    const question = window.prompt("What policy question should the answer address?");
    if (!question || question.trim().length < 5) return;
    if (remote.connected) {
      try {
        const result = await apiRequest(`/api/bookings/${encodeURIComponent(id)}/policy-answer?question=${encodeURIComponent(question.trim())}`, { method: "POST", body: {} });
        await refreshRemote({ keepMessage: true });
        toast(`Fare-aware draft created. Approval #${result.approval_id} is required before email.`);
      } catch (error) { toast(error.message, true); }
      return;
    }
    state.approvals.unshift({ id: uid("AP"), type: "RAG response review", subject: `Booking ${booking.id} · policy response`, detail: `Draft prepared for ${booking.fare} fare. Human approval is required before sending. Question: ${question.trim()}`, amount: 0, status: "Pending", createdAt: Date.now(), source: "Policy assistant" });
    log("Fare-aware policy draft created", booking.id, `Draft uses the booking's ${booking.fare} fare rule; human review required before delivery.`);
    save(); render(); toast("Policy draft queued for human approval; no email sent.");
  }
  async function resolveRefund(id, status) {
    const reason = window.prompt(`Reason for marking this refund ${status}:`);
    if (!reason || reason.trim().length < 4) return toast("A resolution reason of at least 4 characters is required.", true);
    if (!remote.connected) return toast("Refund resolution requires the connected PostgreSQL API.", true);
    const providerReference = status === "succeeded" ? window.prompt("Payment provider reference (optional):") : null;
    try {
      await apiRequest(`/api/refunds/${encodeURIComponent(id)}/resolve`, {
        method: "POST",
        body: { status, reason: reason.trim(), provider_reference: providerReference || null },
      });
      await refreshRemote({ keepMessage: true });
      toast(`Refund marked ${status}; resolution was audited.`);
    } catch (error) { toast(error.message, true); }
  }
  function resolveRebooking(id) {
    const booking = state.bookings.find((item) => item.id === id && item.status === "Rebooking required");
    if (!booking) return toast("No rebooking action is pending.", true);
    const oldFlight = flightById(booking.flightId);
    const replacements = state.flights.filter((flight) => flight.status === "Scheduled" && flight.id !== booking.flightId && flight.originCode === oldFlight?.originCode && flight.destinationCode === oldFlight?.destinationCode && flight.departure > localDate(0, 0) && available(flight, booking.class) >= booking.passengers.length);
    if (!replacements.length) return toast("No suitable replacement is available yet; booking remains in rebooking queue.", true);
    openModal(`Resolve rebooking · ${esc(booking.id)}`, "Choose a scheduled flight on the same route with seats for every passenger. The original fare is preserved.", `
      <form id="rebook-form" data-booking-id="${esc(id)}" class="form-grid">
        <label class="form-field form-full">Replacement flight<select name="flightId" required>${replacements.map((flight) => `<option value="${esc(flight.id)}">${esc(flight.number)} · ${esc(flight.originCode)} → ${esc(flight.destinationCode)} · ${formatDate(flight.departure, { year: "numeric" })} · ${available(flight, booking.class)} ${esc(booking.class)} seats</option>`).join("")}</select></label>
        <div class="notice form-full">Airline-initiated rebooking preserves the purchased fare rule and price.</div>
        <div class="form-actions form-full"><button type="button" class="btn" data-action="close-modal">Keep pending</button><button class="btn btn-primary" type="submit">Rebook passengers</button></div>
      </form>`);
  }
  async function processRebooking(form) {
    const bookingId = form.dataset.bookingId;
    const destinationFlightId = String(new FormData(form).get("flightId") || "");
    const booking = state.bookings.find((item) => item.id === bookingId);
    const replacement = flightById(destinationFlightId);
    if (!booking || !replacement) return toast("Booking or replacement flight could not be found.", true);
    if (remote.connected) {
      try {
        await apiRequest(`/api/bookings/${encodeURIComponent(bookingId)}/rebook`, {
          method: "POST",
          body: { destination_flight_id: Number(destinationFlightId), fare_policy_override: true },
        });
        closeModal(); await refreshRemote({ keepMessage: true }); toast(`Rebooked on ${replacement.number}; original fare retained.`);
      } catch (error) { toast(error.message, true); }
      return;
    }
    const oldId = booking.flightId;
    booking.flightId = replacement.id; booking.status = "Confirmed"; booking.airlineChangeOverride = true;
    log("Rebooked after flight cancellation", `${booking.id} · ${oldId} → ${replacement.id}`, "Airline-initiated change; original fare preserved under fare-policy override.");
    save(); closeModal(); render(); toast(`Rebooked on ${replacement.number}; original fare retained.`);
  }
  function downloadAudit() {
    const header = ["Timestamp", "Actor", "Action", "Target", "Details"];
    const rows = state.audit.map((item) => [new Date(item.at).toISOString(), item.actor, item.action, item.target, item.detail]);
    const csv = [header, ...rows].map((row) => row.map((value) => `"${String(value).replace(/"/g, '""')}"`).join(",")).join("\r\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = "northstar-demo-audit.csv"; link.click(); URL.revokeObjectURL(url);
    toast("Audit CSV exported from local demo data.");
  }
  document.addEventListener("click", async (event) => {
    const viewButton = event.target.closest("[data-view]");
    if (viewButton) { event.preventDefault(); navigate(viewButton.dataset.view); return; }
    const action = event.target.closest("[data-action]");
    if (!action) return;
    const { action: name, id, flight, class: cabin, job, status } = action.dataset;
    if (name === "connect-api") connectApiModal();
    else if (name === "disconnect-api") { remote.connected = false; remote.token = ""; remote.user = null; sessionStorage.removeItem("northstar-api-token"); closeModal(); state = initialState(); render(); toast("Disconnected from API; returned to local demo."); }
    else if (name === "new-flight") { if (state.role !== "super-admin") return toast("Only super-admins can create flights.", true); flightForm(null); }
    else if (name === "edit-flight") { const item = flightById(id); if (item) flightForm(item); }
    else if (name === "cancel-flight") cancelFlight(id);
    else if (name === "close-modal") closeModal();
    else if (name === "hold-seat") makeHold(flight, cabin);
    else if (name === "hold-itinerary") holdItinerary(action);
    else if (name === "price-alert") await createPriceAlert(flight, cabin);
    else if (name === "confirm-hold") await confirmHold(action);
    else if (name === "confirm-payment") await confirmPayment(id);
    else if (name === "release-hold") {
      if (remote.connected) {
        try { await apiRequest(`/api/holds/${encodeURIComponent(id)}`, { method: "DELETE", body: {} }); await refreshRemote({ keepMessage: true }); toast("Hold released in PostgreSQL."); }
        catch (error) { toast(error.message, true); }
      } else {
        const hold = state.holds.find((item) => item.id === id && item.status === "Held"); if (hold) { hold.status = "Released"; log("Released checkout hold", hold.id, "Seat inventory and held fare released to availability."); save(); render(); toast("Hold released."); }
      }
    }
    else if (name === "cancel-booking") cancelBooking(id);
    else if (name === "policy-answer") await draftPolicyAnswer(id);
    else if (name === "resolve-refund") await resolveRefund(id, status);
    else if (name === "add-waitlist") addWaitlist();
    else if (name === "promote-one") {
      if (remote.connected) {
        try { await apiRequest("/api/automations/waitlist/promote", { method: "POST", body: {} }); await refreshRemote({ keepMessage: true }); toast("Waitlist promotion processed."); }
        catch (error) { toast(error.message, true); }
      } else promoteEntry(state.waitlist.find((item) => item.id === id));
    }
    else if (name === "promote-waitlist") {
      if (remote.connected) {
        try { const result = await apiRequest("/api/automations/waitlist/promote", { method: "POST", body: {} }); await refreshRemote({ keepMessage: true }); toast(result.promoted ? "Seat offer created; claim window started." : "No eligible passenger has a freed seat."); }
        catch (error) { toast(error.message, true); }
      } else { const entry = sortedWaitingEntry(); entry ? promoteEntry(entry) : toast("No eligible waitlisted passenger has an available seat."); }
    }
    else if (name === "claim-seat") await claimSeat(id);
    else if (name === "run-automation") await runAutomation(job);
    else if (name === "approve-item" || name === "reject-item") {
      if (remote.connected) {
        try {
          await apiRequest(`/api/approvals/${encodeURIComponent(id)}/decision`, {
            method: "POST",
            body: { decision: name === "approve-item" ? "approved" : "rejected", rationale: "Reviewed by an authorized human operator in the operations console." },
          });
          await refreshRemote({ keepMessage: true }); toast("Decision recorded in PostgreSQL audit history.");
        } catch (error) { toast(error.message, true); }
      } else {
        const item = state.approvals.find((approval) => approval.id === id && approval.status === "Pending"); if (item) { item.status = name === "approve-item" ? "Approved" : "Rejected"; item.reviewedAt = Date.now(); item.reviewer = "Alex Morgan"; log(name === "approve-item" ? "Human approval granted" : "Human approval rejected", `${item.id} · ${item.type}`, `${item.subject}. ${item.detail} Reviewer: Alex Morgan. Human decision recorded before any customer email.`); save(); render(); toast(`Decision ${item.status.toLowerCase()} and audited.`); }
      }
    }
    else if (name === "resolve-rebooking") resolveRebooking(id);
    else if (name === "currency") {
      if (remote.connected) return toast("No exchange-rate provider is configured; live fares stay in each flight's stored currency.");
      const currencies = ["USD", "EUR", "GBP", "AED", "SGD"]; state.currency = currencies[(currencies.indexOf(state.currency) + 1) % currencies.length]; state.locale = ({ USD: "en-US", EUR: "fr-FR", GBP: "en-GB", AED: "en-AE", SGD: "en-SG" })[state.currency]; save(); render();
    }
    else if (name === "export-audit") downloadAudit();
    else if (name === "reset-demo") { if (window.confirm("Reset all browser-saved demo changes and restore sample data?")) { state = initialState(); save(); navigate("dashboard"); toast("Demo data reset."); } }
  });
  document.addEventListener("submit", async (event) => {
    const { id } = event.target;
    if (id === "backend-connect-form") {
      event.preventDefault();
      const data = new FormData(event.target);
      const base = String(data.get("base")).replace(/\/+$/, "");
      try {
        const result = await apiRequest("/api/auth/login", {
          method: "POST",
          base,
          token: "",
          body: { email: String(data.get("email")), password: String(data.get("password")) },
        });
        remote.base = base;
        localStorage.setItem("northstar-api-base", base);
        remote.token = result.access_token;
        sessionStorage.setItem("northstar-api-token", result.access_token);
        const connected = await refreshRemote({ keepMessage: true });
        if (connected) { closeModal(); toast(`Connected as ${remote.user.email}.`); }
      } catch (error) { toast(error.message, true); }
      return;
    }
    if (!["flight-form", "cancel-flight-form", "search-form", "cancel-booking-form", "waitlist-form", "rebook-form", "itinerary-hold-form"].includes(id)) return;
    event.preventDefault();
    if (id === "flight-form") await processFlightForm(event.target);
    else if (id === "cancel-flight-form") await processCancelFlight(event.target);
    else if (id === "search-form") await processSearch(event.target);
    else if (id === "cancel-booking-form") await processCancelBooking(event.target);
    else if (id === "rebook-form") await processRebooking(event.target);
    else if (id === "itinerary-hold-form") await processItineraryHold(event.target);
    else if (id === "waitlist-form") {
      const data = new FormData(event.target);
      const flightId = String(data.get("flightId"));
      const cabin = String(data.get("class"));
      if (remote.connected) {
        try {
          await apiRequest("/api/waitlist", {
            method: "POST",
            body: {
              flight_id: Number(flightId),
              cabin,
              passenger_name: String(data.get("passenger")),
              passenger_email: String(data.get("email")),
              loyalty_tier: String(data.get("loyalty")).toLowerCase(),
              fare_rule: apiFare(String(data.get("fare"))),
            },
          });
          closeModal(); await refreshRemote({ keepMessage: true }); toast("Passenger added to the database waitlist.");
        } catch (error) { toast(error.message, true); }
        return;
      }
      const duplicate = state.waitlist.some((entry) => entry.flightId === flightId && entry.class === cabin && entry.email.toLowerCase() === String(data.get("email")).toLowerCase() && ["Waiting", "Claim window"].includes(entry.status));
      if (duplicate) return toast("This passenger is already in the waitlist for this class.", true);
      const entry = { id: uid("WL"), flightId, passenger: String(data.get("passenger")).trim(), email: String(data.get("email")).trim(), class: cabin, loyalty: String(data.get("loyalty")), fare: String(data.get("fare")), joinedAt: Date.now(), status: "Waiting" };
      state.waitlist.push(entry);
      log("Passenger joined waitlist", `${entry.passenger} · ${flightById(flightId)?.number} ${cabin}`, `Priority tier ${entry.loyalty}; booking time ${new Date(entry.joinedAt).toISOString()}.`);
      save(); closeModal(); render(); toast("Passenger added to waitlist.");
    }
  });
  document.addEventListener("input", (event) => {
    if (event.target.id === "flight-filter") {
      flightsFilter = event.target.value;
      const search = flightsFilter.toLowerCase();
      const status = document.querySelector("#flight-status-filter")?.value || "all";
      const rows = state.flights.filter((item) => `${item.number} ${item.origin} ${item.destination} ${item.originCode} ${item.destinationCode}`.toLowerCase().includes(search) && (status === "all" || item.status === status));
      const table = document.querySelector("#flights-table");
      if (table) table.innerHTML = rows.length ? rows.map((item) => flightRow(item)).join("") : tableEmpty(7, "No flights match this search.");
    } else if (event.target.id === "booking-filter") {
      bookingsFilter = event.target.value;
      const cursor = event.target.selectionStart;
      renderBookings();
      const input = document.querySelector("#booking-filter");
      input.focus(); input.setSelectionRange(cursor, cursor);
    }
  });
  document.addEventListener("change", (event) => {
    if (event.target.id === "seat-map-flight") drawSeatMap();
  });
  document.querySelector("#role-select").addEventListener("change", (event) => {
    state.role = event.target.value;
    log("Changed demo permission role", state.role, "Role switch is for local permission demonstration only.");
    save(); render(); toast(`Switched to ${state.role}.`);
  });
  document.querySelector("#mobile-menu").addEventListener("click", () => {
    document.querySelector("#sidebar").classList.toggle("open");
    render();
  });
  document.querySelector("#help-button").addEventListener("click", () => {
    openModal("About this prototype", "A front-end feature demo for the Northstar Air operations project.", `<div class="notice warn"><span>ⓘ</span><span>Local sample data only. Do not enter real passenger, payment, or credential information.</span></div><div class="meta-grid"><div class="meta-box"><small>Persistence</small><strong>Browser localStorage</strong></div><div class="meta-box"><small>Backend</small><strong>None connected</strong></div><div class="meta-box"><small>Emails / payments</small><strong>Simulated only</strong></div><div class="meta-box"><small>Data reset</small><strong>Feature coverage → Reset demo data</strong></div></div>`);
  });
  modalBackdrop.addEventListener("click", (event) => { if (event.target === modalBackdrop) closeModal(); });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !modalBackdrop.hidden) closeModal(); });
  document.querySelector("#role-select").value = state.role;
  render();
  if (remote.token) refreshRemote({ keepMessage: true });
  const paymentQuery = new URLSearchParams(window.location.search);
  const paymentSession = paymentQuery.get("payment_session_id");
  const paymentHold = paymentQuery.get("hold_id");
  if (paymentSession && paymentHold && remote.token) {
    apiRequest(`/api/holds/${encodeURIComponent(paymentHold)}/confirm`, {
      method: "POST", body: { checkout_session_id: paymentSession },
    }).then(async (result) => {
      history.replaceState({}, document.title, window.location.pathname);
      await refreshRemote({ keepMessage: true });
      toast(`${result.bookings.length} booking(s) confirmed after verified payment.`);
    }).catch((error) => toast(error.message, true));
  } else if (paymentQuery.get("payment_cancelled")) {
    history.replaceState({}, document.title, window.location.pathname);
    toast("Checkout cancelled; the seat remains held until its expiry.");
  }
  window.setInterval(() => { if (remote.connected && currentView !== "dashboard") refreshRemote({ keepMessage: true }); }, 60000);
  window.setInterval(expireTimedItems, 15000);
});
