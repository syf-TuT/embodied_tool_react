const frame = document.querySelector("#frame");
const emptyFrame = document.querySelector("#empty-frame");
const connection = document.querySelector("#connection");
const task = document.querySelector("#task");
const scene = document.querySelector("#scene");
const step = document.querySelector("#step");
const statusLabel = document.querySelector("#status");
const currentTool = document.querySelector("#current-tool");
const objects = document.querySelector("#objects");
const timeline = document.querySelector("#timeline");

const seenEvents = new Set();
let socket = null;
let reconnectTimer = null;

function setConnection(label, state) {
  connection.textContent = label;
  connection.className = `connection is-${state}`;
}

function connect() {
  window.clearTimeout(reconnectTimer);
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${protocol}://${window.location.host}/ws`);

  setConnection("Connecting", "connecting");

  socket.addEventListener("open", () => {
    setConnection("Connected", "connected");
    socket.send("observer_ready");
  });

  socket.addEventListener("message", (message) => {
    try {
      renderEvent(JSON.parse(message.data));
    } catch (error) {
      renderEvent({
        type: "observer_error",
        message: `Invalid observer event: ${error.message}`,
        success: false,
      });
    }
  });

  socket.addEventListener("error", () => {
    setConnection("Socket Error", "error");
  });

  socket.addEventListener("close", () => {
    setConnection("Disconnected", "disconnected");
    reconnectTimer = window.setTimeout(connect, 1400);
  });
}

function renderEvent(event) {
  const eventKey = event.sequence ?? `${event.type}:${event.step_id ?? ""}:${event.tool_name ?? ""}:${event.message ?? ""}`;
  if (seenEvents.has(eventKey)) {
    updateStatus(event);
    return;
  }
  seenEvents.add(eventKey);
  if (seenEvents.size > 500) {
    seenEvents.delete(seenEvents.values().next().value);
  }

  updateStatus(event);
  renderFrame(event.frame);

  if (event.tool_name || event.type === "observer_error") {
    renderTool(event);
  }
  if (Array.isArray(event.visible_objects)) {
    renderObjects(event.visible_objects);
  }
  appendTimeline(event);
}

function updateStatus(event) {
  if (event.task_id) task.textContent = event.task_id;
  if (event.scene) scene.textContent = event.scene;
  if (event.step_id !== undefined && event.step_id !== null) step.textContent = event.step_id;

  if (event.type === "episode_start") statusLabel.textContent = "Running";
  if (event.type === "episode_end") statusLabel.textContent = event.success ? "Success" : "Failed";
  if (event.type === "observer_error" || event.observer_warning) statusLabel.textContent = "Observer warning";
}

function renderFrame(source) {
  if (!source) return;
  frame.src = source;
  frame.style.display = "block";
  emptyFrame.style.display = "none";
}

function renderTool(event) {
  currentTool.textContent = JSON.stringify({
    type: event.type,
    tool: event.tool_name || "observer",
    args: event.args || event.tool_args || {},
    success: event.success,
    message: event.message || event.observer_warning || "",
    failure_type: event.failure_type || "",
  }, null, 2);
}

function renderObjects(items) {
  objects.replaceChildren();
  items.slice(0, 24).forEach((item) => {
    const li = document.createElement("li");
    const name = document.createElement("span");
    const meta = document.createElement("small");
    const label = item.objectType || item.objectId || "Object";
    const id = item.objectId && item.objectId !== label ? ` ${item.objectId}` : "";
    const distance = Number.isFinite(item.distance) ? `${item.distance.toFixed(2)}m` : "";

    name.textContent = `${label}${id}`;
    meta.textContent = distance || (item.visible === false ? "hidden" : "visible");
    li.append(name, meta);
    objects.appendChild(li);
  });
}

function appendTimeline(event) {
  const li = document.createElement("li");
  const label = document.createElement("span");
  const meta = document.createElement("small");
  const type = event.type || "event";
  const tool = event.tool_name ? `: ${event.tool_name}` : "";

  li.className = timelineClass(event);
  label.textContent = `${type}${tool}`;
  meta.textContent = event.sequence ? `#${event.sequence}` : step.textContent ? `step ${step.textContent}` : "";
  li.append(label, meta);
  timeline.prepend(li);

  while (timeline.children.length > 80) {
    timeline.lastElementChild.remove();
  }
}

function timelineClass(event) {
  if (event.type === "observer_error" || event.success === false) return "failed";
  if (event.observer_warning) return "warning";
  if (event.type === "episode_start" || event.type === "episode_end") return "info";
  return "ok";
}

connect();
