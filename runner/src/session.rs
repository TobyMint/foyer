use std::io::Write;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use tokio::sync::{mpsc, Semaphore};

use crate::cli::Args;
use crate::record::StepLog;
use crate::tokens::{PromptBuilder, TokenProvider};
use crate::trace::SessionStep;
use crate::util::{prefix_hit_rate, unix_seconds_now};
use crate::backend::{GenerationClient, StepOutcome};

/// Shared, immutable-per-run state handed to every session task.
pub(crate) struct AppState {
    pub(crate) args: Args,
    pub(crate) client: Arc<GenerationClient>,
    pub(crate) token_pool: Arc<Vec<u32>>,
    pub(crate) stats: Arc<Stats>,
    pub(crate) run_start: Instant,
    pub(crate) session_semaphore: Option<Arc<Semaphore>>,
    /// Dynamic admission control: when set, sessions are gated by the integer cap read
    /// from this file (polled, 250 ms cache) instead of the static semaphore.
    pub(crate) cap_file: Option<String>,
    /// Number of sessions currently admitted under the dynamic gate.
    pub(crate) active_sessions: Arc<AtomicUsize>,
    /// (last poll instant, last cap value) cache for cap-file reads.
    pub(crate) cap_cache: Arc<Mutex<Option<(Instant, usize)>>>,
    /// JSONL admission-event sink.
    pub(crate) admission_log: Option<Arc<Mutex<std::io::BufWriter<std::fs::File>>>>,
}

impl AppState {
    /// Current dynamic cap, falling back to --max-active-sessions (or unlimited) until the
    /// cap file yields its first parseable value.
    pub(crate) fn current_cap(&self) -> usize {
        let path = match &self.cap_file {
            Some(path) => path,
            None => return usize::MAX,
        };
        let mut cache = self.cap_cache.lock().unwrap();
        if let Some((at, value)) = *cache {
            if at.elapsed() < Duration::from_millis(250) {
                return value;
            }
        }
        let fallback = self.args.max_active_sessions.unwrap_or(usize::MAX);
        let value = std::fs::read_to_string(path)
            .ok()
            .and_then(|text| text.trim().parse::<usize>().ok())
            .unwrap_or(fallback);
        *cache = Some((Instant::now(), value));
        value
    }

    /// Append one admission event; failures are swallowed (logging must never kill a run).
    pub(crate) fn log_admission(
        &self,
        event: &str,
        session_id: &str,
        session_ordinal: usize,
        cap: usize,
        active: usize,
        waited_since: Instant,
    ) {
        let sink = match &self.admission_log {
            Some(sink) => sink,
            None => return,
        };
        let line = format!(
            "{{\"ts\":{:.3},\"event\":\"{}\",\"session_id\":\"{}\",\"ordinal\":{},\"cap\":{},\"active\":{},\"waited_ms\":{:.1}}}\n",
            unix_seconds_now(),
            event,
            session_id,
            session_ordinal,
            cap,
            active,
            waited_since.elapsed().as_secs_f64() * 1000.0,
        );
        if let Ok(mut writer) = sink.lock() {
            let _ = writer.write_all(line.as_bytes());
            let _ = writer.flush();
        }
    }
}

/// Held for a session's whole lifetime (including tool waits), mirroring the static
/// semaphore's semantics: an "active" session occupies its admission slot even while
/// paused between rounds.
pub(crate) struct AdmissionGate {
    state: Arc<AppState>,
    session_id: String,
    session_ordinal: usize,
    waited_since: Instant,
}

impl AdmissionGate {
    async fn acquire(state: &Arc<AppState>, session_id: &str, session_ordinal: usize) -> Self {
        let waited_since = Instant::now();
        loop {
            let cap = state.current_cap();
            let active = state.active_sessions.load(Ordering::Relaxed);
            if active < cap {
                state.active_sessions.store(active + 1, Ordering::Relaxed);
                state.log_admission(
                    "admit",
                    session_id,
                    session_ordinal,
                    cap,
                    active + 1,
                    waited_since,
                );
                return Self {
                    state: state.clone(),
                    session_id: session_id.to_string(),
                    session_ordinal,
                    waited_since,
                };
            }
            tokio::time::sleep(Duration::from_millis(200)).await;
        }
    }
}

impl Drop for AdmissionGate {
    fn drop(&mut self) {
        let active = self.state.active_sessions.fetch_sub(1, Ordering::Relaxed) - 1;
        let cap = self.state.current_cap();
        self.state.log_admission(
            "release",
            &self.session_id,
            self.session_ordinal,
            cap,
            active,
            self.waited_since,
        );
    }
}

/// One of the two gating mechanisms; kept alive for the session's lifetime.
pub(crate) enum SessionGate {
    None,
    Static(tokio::sync::OwnedSemaphorePermit),
    Dynamic(AdmissionGate),
}

/// Lock-free progress counters shared with the status reporter.
#[derive(Default)]
pub(crate) struct Stats {
    submitted: AtomicUsize,
    completed: AtomicUsize,
    failed: AtomicUsize,
    finished_sessions: AtomicUsize,
}

impl Stats {
    pub(crate) fn record_submit(&self) {
        self.submitted.fetch_add(1, Ordering::Relaxed);
    }

    pub(crate) fn record_result(&self, success: bool) {
        if success {
            self.completed.fetch_add(1, Ordering::Relaxed);
        } else {
            self.failed.fetch_add(1, Ordering::Relaxed);
        }
    }

    pub(crate) fn record_session_done(&self) {
        self.finished_sessions.fetch_add(1, Ordering::Relaxed);
    }
}

/// Replay one session as an ordered, closed-loop chain of rounds.
pub(crate) async fn run_session(
    state: Arc<AppState>,
    log_tx: mpsc::Sender<StepLog>,
    session_ordinal: usize,
    session_id: String,
    steps: Vec<SessionStep>,
) {
    wait_for_session_arrival(&state, &steps).await;
    let _session_gate = if state.cap_file.is_some() {
        SessionGate::Dynamic(AdmissionGate::acquire(&state, &session_id, session_ordinal).await)
    } else {
        match &state.session_semaphore {
            Some(semaphore) => match semaphore.clone().acquire_owned().await.ok() {
                Some(permit) => SessionGate::Static(permit),
                None => SessionGate::None,
            },
            None => SessionGate::None,
        }
    };

    let token_provider = match TokenProvider::new(
        state.token_pool.clone(),
        session_ordinal.wrapping_mul(9_973),
    ) {
        Ok(provider) => provider,
        Err(err) => {
            eprintln!("session {session_id}: {err}");
            return;
        }
    };
    let mut prompt_builder = PromptBuilder::new(token_provider);

    for step in steps {
        let prompt_ids = prompt_builder.build_prompt(&step);
        let request_id = format!("{}_round_{:06}", session_id, step.round_idx);
        state.stats.record_submit();
        let outcome = if should_skip_context_overflow(&state.args, prompt_ids.len()) {
            StepOutcome {
                log: context_overflow_log(
                    &step,
                    request_id,
                    prompt_ids.len(),
                    state.args.max_model_len,
                ),
                output_ids: Vec::new(),
            }
        } else {
            state.client.run_step(&step, request_id, &prompt_ids).await
        };
        let StepOutcome { log, output_ids } = outcome;
        let success = log.status == "SUCCESS";
        let _ = log_tx.send(log).await;

        state.stats.record_result(success);
        if !success && state.args.stop_session_on_error {
            break;
        }

        // Carry the model's real output tokens forward (not synthetic) so the previous-output
        // region of the next prefix matches what the server cached and stays cache-hittable.
        prompt_builder.commit_output(prompt_ids, output_ids);

        if step.tool_wait_after_ms > 0.0 {
            tokio::time::sleep(Duration::from_secs_f64(step.tool_wait_after_ms / 1000.0)).await;
        }
    }

    state.stats.record_session_done();
}

fn should_skip_context_overflow(args: &Args, prompt_len: usize) -> bool {
    args.fail_on_context_overflow
        && args
            .max_model_len
            .map(|limit| prompt_len > limit)
            .unwrap_or(false)
}

fn context_overflow_log(
    step: &SessionStep,
    request_id: String,
    prompt_len: usize,
    max_model_len: Option<usize>,
) -> StepLog {
    let limit = max_model_len
        .map(|value| value.to_string())
        .unwrap_or_else(|| "unknown".to_string());
    StepLog {
        session_id: step.session_id.clone(),
        round_idx: step.round_idx,
        request_id,
        prefix_len: step.prefix_len,
        input_len: step.input_len,
        prompt_len,
        planned_prefix_hit_rate: prefix_hit_rate(step.prefix_len, prompt_len),
        output_len_target: step.output_len,
        output_len_actual: 0,
        output_len_text_tokens: 0,
        server_prompt_tokens: None,
        server_completion_tokens: None,
        server_total_tokens: None,
        server_cached_prompt_tokens: None,
        server_uncached_prompt_tokens: None,
        server_prefix_hit_rate: None,
        server_prefix_hit_rate_delta: None,
        finish_reason: None,
        tool_wait_after_ms: step.tool_wait_after_ms,
        arrival_time_ms: step.arrival_time,
        submit_timestamp: unix_seconds_now(),
        post_timestamp: None,
        complete_timestamp: unix_seconds_now(),
        first_token_ms: None,
        total_duration_ms: 0.0,
        chunk_count: 0,
        status: "SKIPPED_CONTEXT_OVERFLOW".to_string(),
        output_preview: String::new(),
        error: Some(format!(
            "prompt_len {} exceeds max_model_len {}",
            prompt_len, limit
        )),
    }
}

async fn wait_for_session_arrival(state: &AppState, steps: &[SessionStep]) {
    let arrival_ms = steps
        .first()
        .map(|step| step.arrival_time.max(0.0))
        .unwrap_or(0.0);
    if arrival_ms <= 0.0 {
        return;
    }

    let target = state.run_start + Duration::from_secs_f64(arrival_ms / 1000.0);
    let now = Instant::now();
    if target > now {
        tokio::time::sleep_until(tokio::time::Instant::from_std(target)).await;
    }
}

/// Periodic stderr progress reporter; exits once all sessions are finished.
pub(crate) async fn status_task(
    stats: Arc<Stats>,
    total_sessions: usize,
    total_steps: usize,
    start: Instant,
) {
    loop {
        tokio::time::sleep(Duration::from_millis(500)).await;
        let submitted = stats.submitted.load(Ordering::Relaxed);
        let completed = stats.completed.load(Ordering::Relaxed);
        let failed = stats.failed.load(Ordering::Relaxed);
        let finished_sessions = stats.finished_sessions.load(Ordering::Relaxed);
        let active = submitted.saturating_sub(completed + failed);
        let finished_steps = completed + failed;

        eprintln!(
            "sessions {}/{} | steps {}/{} completed={} submitted={} active={} failed={} | elapsed={:.1}s",
            finished_sessions,
            total_sessions,
            finished_steps,
            total_steps,
            completed,
            submitted,
            active,
            failed,
            start.elapsed().as_secs_f64(),
        );

        if finished_sessions >= total_sessions {
            break;
        }
    }
}
