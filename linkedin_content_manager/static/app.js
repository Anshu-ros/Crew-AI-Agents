const stageNames = ["research", "write", "critique", "optimize", "schedule"];
const stageLabels = {
  research: "Research",
  write: "Write",
  critique: "Critique",
  optimize: "Optimize",
  schedule: "Schedule",
};

const form = document.querySelector("#run-form");
const topicInput = document.querySelector("#topic-input");
const runButton = document.querySelector("#run-button");
const formStatus = document.querySelector("#form-status");
const activityMessage = document.querySelector("#activity-message");
const activityMarker = document.querySelector("#activity-marker");
const runStatusLabel = document.querySelector("#run-status-label");
const progressBar = document.querySelector("#progress-bar");
const queueList = document.querySelector("#queue-list");
const resultSection = document.querySelector("#result-section");
let activePostText = "";

function setNotice(message, isError = false) {
  formStatus.textContent = message;
  formStatus.classList.toggle("error", isError);
}

function renderStages(completedStages = [], activeStage = null, failed = false) {
  document.querySelectorAll("[data-stage]").forEach((item) => {
    const name = item.dataset.stage;
    const state = item.querySelector(".stage-state");
    item.classList.toggle("done", completedStages.includes(name));
    item.classList.toggle("active", name === activeStage && !failed);
    if (completedStages.includes(name)) state.textContent = "COMPLETE";
    else if (name === activeStage && !failed) state.textContent = "RUNNING";
    else if (failed && name === activeStage) state.textContent = "STOPPED";
    else state.textContent = "READY";
  });
  const count = completedStages.length;
  progressBar.style.width = `${Math.round((count / stageNames.length) * 100)}%`;
}

function setActivity(status, message) {
  activityMessage.textContent = message;
  activityMarker.className = "activity-marker";
  runStatusLabel.className = "run-status-label";
  runStatusLabel.textContent = status.toUpperCase();
  if (status === "running" || status === "queued") {
    activityMarker.classList.add("running");
    runStatusLabel.classList.add("running");
  } else if (status === "completed") {
    activityMarker.classList.add("done");
  } else if (status === "failed") {
    activityMarker.classList.add("failed");
    runStatusLabel.classList.add("failed");
  }
}

function formatDate(value, timezone) {
  if (!value) return "Time not provided";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: timezone || undefined,
  }).format(new Date(value));
}

function makeQueueEntry(post) {
  const entry = document.createElement("article");
  entry.className = "queue-entry";

  const meta = document.createElement("div");
  meta.className = "queue-entry-meta";
  const time = document.createElement("span");
  time.textContent = formatDate(post.scheduled_post.publish_at, post.scheduled_post.timezone);
  const timezone = document.createElement("span");
  timezone.textContent = post.scheduled_post.timezone;
  meta.append(time, timezone);

  const topic = document.createElement("h3");
  topic.className = "queue-entry-topic";
  topic.textContent = post.topic;

  const copy = document.createElement("p");
  copy.className = "queue-entry-copy";
  copy.textContent = post.scheduled_post.post_text;

  entry.append(meta, topic, copy);
  return entry;
}

function renderPosts(posts) {
  queueList.replaceChildren();
  document.querySelector("#post-count").textContent = String(posts.length).padStart(2, "0");
  document.querySelector("#queue-total").textContent = String(posts.length).padStart(2, "0");
  if (!posts.length) {
    const empty = document.createElement("p");
    empty.className = "empty-queue";
    empty.textContent = "No scheduled posts yet.";
    queueList.append(empty);
    return;
  }
  posts.forEach((post) => queueList.append(makeQueueEntry(post)));
}

async function loadPosts() {
  const response = await fetch("/api/posts?limit=8");
  if (!response.ok) throw new Error("Could not load the schedule queue.");
  renderPosts(await response.json());
}

async function loadHealth() {
  try {
    const response = await fetch("/api/health");
    const health = await response.json();
    document.querySelector("#service-label").textContent = health.configured ? "Service ready" : "Needs configuration";
    document.querySelector("#model-label").textContent = health.configured ? health.model.toUpperCase() : "MODEL UNSET";
    document.querySelector("#timezone-label").textContent = health.configured ? health.timezone : "TIMEZONE UNSET";
    if (!health.configured) setNotice(health.message, true);
  } catch {
    document.querySelector("#service-label").textContent = "Service unavailable";
    setNotice("Could not reach the local dashboard service.", true);
  }
}

async function watchRun(runId) {
  try {
    const response = await fetch(`/api/runs/${encodeURIComponent(runId)}`);
    const run = await response.json();
    if (!response.ok) throw new Error(run.detail || "Could not read pipeline status.");

    const completed = run.completed_stages || [];
    const activeStage = run.status === "running" ? stageNames[completed.length] : null;
    renderStages(completed, activeStage, run.status === "failed");

    if (run.status === "completed") {
      setActivity("completed", "All five stages completed. The schedule is saved locally.");
      setNotice("Scheduled post saved to the local queue.");
      runButton.disabled = false;
      resultSection.hidden = false;
      activePostText = run.scheduled_post.post_text;
      document.querySelector("#result-copy").textContent = activePostText;
      document.querySelector("#result-schedule").textContent = `${formatDate(run.scheduled_post.publish_at, run.scheduled_post.timezone)} / ${run.scheduled_post.timezone}`;
      await loadPosts();
      return;
    }

    if (run.status === "failed") {
      setActivity("failed", run.error || "The pipeline stopped before scheduling.");
      setNotice("Run failed. Review the status for details.", true);
      runButton.disabled = false;
      return;
    }

    setActivity(run.status, run.status === "queued" ? "Run queued..." : `${stageLabels[activeStage] || "Pipeline"} in progress...`);
    setNotice("The five stages are running in order.");
    window.setTimeout(() => watchRun(runId), 1200);
  } catch (error) {
    setActivity("failed", error.message);
    setNotice(error.message, true);
    runButton.disabled = false;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const topic = topicInput.value.trim();
  if (topic.length < 3) {
    setNotice("Enter a topic with at least 3 characters.", true);
    topicInput.focus();
    return;
  }

  runButton.disabled = true;
  resultSection.hidden = true;
  renderStages([], "research");
  setActivity("queued", "Sending topic to the pipeline...");
  setNotice("Creating a new run...");
  try {
    const response = await fetch("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Could not start the pipeline.");
    await watchRun(data.run_id);
  } catch (error) {
    setActivity("failed", error.message);
    setNotice(error.message, true);
    runButton.disabled = false;
  }
});

document.querySelector("#copy-button").addEventListener("click", async () => {
  if (!activePostText) return;
  try {
    await navigator.clipboard.writeText(activePostText);
    document.querySelector("#copy-button").textContent = "Copied";
    window.setTimeout(() => { document.querySelector("#copy-button").textContent = "Copy post"; }, 1400);
  } catch {
    setNotice("Clipboard access is unavailable in this browser.", true);
  }
});

document.querySelector("#today-label").textContent = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date());
loadHealth();
loadPosts().catch((error) => {
  queueList.replaceChildren();
  const message = document.createElement("p");
  message.className = "empty-queue";
  message.textContent = error.message;
  queueList.append(message);
});