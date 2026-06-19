const state = {
  section: "all",
  source: "all",
  workflow: "all",
  query: "",
  minimumScore: 45,
  selectedRank: null
};

const WORKFLOW_STORAGE_KEY = "inspectionFilesWorkflowStatus";
const workflowLabels = {
  pending: "Pending Future Show",
  used: "Used on Show",
  declined: "Decline"
};

const data = window.VIOLATION_DESK_DATA;
const leadList = document.querySelector("#leadList");
const caseDetail = document.querySelector("#caseDetail");
const searchInput = document.querySelector("#searchInput");
const scoreInput = document.querySelector("#scoreInput");
const scoreOutput = document.querySelector("#scoreOutput");
const leadCount = document.querySelector("#leadCount");
const topScore = document.querySelector("#topScore");
const visibleCount = document.querySelector("#visibleCount");
const generatedAt = document.querySelector("#generatedAt");
const sectionButtons = [...document.querySelectorAll(".section-button")];
const sourceButtons = [...document.querySelectorAll(".source-button")];
const workflowButtons = [...document.querySelectorAll(".workflow-button")];
let workflowStatus = loadWorkflowStatus();

function leadKey(lead) {
  if (lead.id) return lead.id;
  return [
    sourceName(lead),
    lead.case,
    lead.location,
    lead.inspectionDate,
    lead.violationType
  ].join("|");
}

function loadWorkflowStatus() {
  try {
    return JSON.parse(localStorage.getItem(WORKFLOW_STORAGE_KEY)) || {};
  } catch {
    return {};
  }
}

function saveWorkflowStatus() {
  localStorage.setItem(WORKFLOW_STORAGE_KEY, JSON.stringify(workflowStatus));
}

function getWorkflowStatus(lead) {
  return workflowStatus[leadKey(lead)] || "";
}

function setWorkflowStatus(lead, status) {
  const key = leadKey(lead);
  if (status) {
    workflowStatus[key] = status;
  } else {
    delete workflowStatus[key];
  }
  saveWorkflowStatus();
}

function sourceName(lead) {
  if (/Los Angeles County/i.test(lead.agency) || /lacounty|lacounty.gov|LA County/i.test(lead.officialRecord)) return "LA County";
  if (/OC Health|Orange County/i.test(lead.agency) || /Orange County/i.test(lead.officialRecord)) return "Orange County";
  if (/Mecklenburg/i.test(lead.agency) || /NCENVPBL|cdpehs/i.test(lead.officialRecord)) return "Mecklenburg County";
  if (/Multiple My Health Department|My Health Department/i.test(lead.agency) || /myhealthdepartment/i.test(lead.officialRecord)) return "My Health Dept";
  if (/San Francisco/i.test(lead.agency)) return "San Francisco";
  if (/DC Health/i.test(lead.agency)) return "DC";
  if (/Chicago/i.test(lead.agency)) return "Chicago";
  if (/NYC|New York/i.test(lead.agency)) return "NYC";
  return "Other";
}

function matchesQuery(lead) {
  const haystack = [
    lead.case,
    lead.section,
    lead.violationType,
    lead.location,
    lead.agency,
    lead.status,
    lead.grossestDetail,
    workflowLabels[getWorkflowStatus(lead)] || ""
  ].join(" ").toLowerCase();

  return haystack.includes(state.query.toLowerCase());
}

function filteredLeads() {
  return data.leads.filter((lead) => {
    const sectionMatch = state.section === "all" || lead.section === state.section;
    const sourceMatch = state.source === "all" || sourceName(lead) === state.source;
    const currentWorkflow = getWorkflowStatus(lead);
    const workflowMatch =
      state.workflow === "all" ||
      (state.workflow === "unmarked" && !currentWorkflow) ||
      currentWorkflow === state.workflow;
    return sectionMatch && sourceMatch && workflowMatch && lead.score >= state.minimumScore && matchesQuery(lead);
  });
}

function scoreClass(score) {
  if (score >= 85) return "score-hot";
  if (score >= 75) return "score-warm";
  return "score-watch";
}

function renderStats(leads) {
  leadCount.textContent = data.leadsReviewed.toLocaleString();
  topScore.textContent = data.leads.length ? Math.max(...data.leads.map((lead) => lead.score)) : 0;
  visibleCount.textContent = `${leads.length} visible`;
  if (generatedAt && data.generatedAt) {
    generatedAt.textContent = `Updated ${new Date(data.generatedAt).toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit"
    })}`;
  }
}

function workflowBadge(lead) {
  const status = getWorkflowStatus(lead);
  if (!status) return "";
  return `<span class="workflow-badge workflow-${status}">${workflowLabels[status]}</span>`;
}

function renderLeadList() {
  const leads = filteredLeads();
  renderStats(leads);

  if (!leads.length) {
    leadList.innerHTML = `<div class="empty-list">No leads match this view.</div>`;
    renderDetail(null);
    return;
  }

  if (!leads.some((lead) => lead.rank === state.selectedRank)) {
    state.selectedRank = leads[0].rank;
  }

  leadList.innerHTML = leads.map((lead) => `
    <button class="lead-row ${lead.rank === state.selectedRank ? "selected" : ""}" data-rank="${lead.rank}">
      <span class="rank">#${lead.rank}</span>
      <span class="lead-main">
        <strong>${lead.case}</strong>
        <span><em>${sourceName(lead)}</em> · ${lead.violationType} · ${lead.location}</span>
        ${workflowBadge(lead)}
      </span>
      <span class="score-pill ${scoreClass(lead.score)}">${lead.score}</span>
    </button>
  `).join("");

  const selected = data.leads.find((lead) => lead.rank === state.selectedRank);
  renderDetail(selected);
}

function renderDetail(lead) {
  if (!lead) {
    caseDetail.innerHTML = `
      <div class="empty-state">
        <p class="kicker">No match</p>
        <h3>Adjust the filters</h3>
        <p>Try a lower score threshold or a broader search term.</p>
      </div>
    `;
    return;
  }

  caseDetail.innerHTML = `
    <div class="detail-header">
      <div>
        <p class="kicker">${lead.section}</p>
        <h3>${lead.case}</h3>
        <div class="detail-badges">
          <span class="source-badge">${sourceName(lead)}</span>
          ${workflowBadge(lead)}
        </div>
      </div>
      <span class="score-medallion ${scoreClass(lead.score)}">${lead.score}</span>
    </div>

    <section class="workflow-panel" data-rank="${lead.rank}">
      <h4>Editorial Status</h4>
      <div class="workflow-actions">
        <button class="status-action ${getWorkflowStatus(lead) === "pending" ? "active" : ""}" data-status="pending">Pending Future Show</button>
        <button class="status-action ${getWorkflowStatus(lead) === "used" ? "active" : ""}" data-status="used">Used on Show</button>
        <button class="status-action ${getWorkflowStatus(lead) === "declined" ? "active" : ""}" data-status="declined">Decline</button>
        <button class="status-action clear" data-status="">Clear</button>
      </div>
    </section>

    <div class="meta-grid">
      <div><span>Inspection Date</span><strong>${lead.inspectionDate}</strong></div>
      <div><span>Status</span><strong>${lead.status}</strong></div>
      <div><span>Violation Type</span><strong>${lead.violationType}</strong></div>
      <div><span>Agency</span><strong>${lead.agency}</strong></div>
    </div>

    <section class="detail-section">
      <h4>Grossest Official Detail</h4>
      <p class="quote">${lead.grossestDetail}</p>
    </section>

    <section class="detail-section">
      <h4>Producer Recommendation</h4>
      <p>${lead.producerRecommendation}</p>
    </section>

    <section class="detail-section">
      <h4>Follow-Up Needed</h4>
      <ul>
        ${lead.followUp.map((item) => `<li>${item}</li>`).join("")}
      </ul>
    </section>

    <section class="detail-section">
      <h4>Official Record</h4>
      <a href="${lead.officialRecord}" target="_blank" rel="noreferrer">${lead.officialRecord}</a>
    </section>

    <section class="legal-note">
      Attribute claims to the inspection record and use the inspection date. Confirm reinspection status before recording.
    </section>
  `;
}

leadList.addEventListener("click", (event) => {
  const row = event.target.closest(".lead-row");
  if (!row) return;
  state.selectedRank = Number(row.dataset.rank);
  renderLeadList();
});

searchInput.addEventListener("input", (event) => {
  state.query = event.target.value;
  renderLeadList();
});

scoreInput.addEventListener("input", (event) => {
  state.minimumScore = Number(event.target.value);
  scoreOutput.textContent = event.target.value;
  renderLeadList();
});

sectionButtons.forEach((button) => {
  button.addEventListener("click", () => {
    sectionButtons.forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.section = button.dataset.section;
    renderLeadList();
  });
});

sourceButtons.forEach((button) => {
  button.addEventListener("click", () => {
    sourceButtons.forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.source = button.dataset.source;
    renderLeadList();
  });
});

workflowButtons.forEach((button) => {
  button.addEventListener("click", () => {
    workflowButtons.forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.workflow = button.dataset.workflow;
    renderLeadList();
  });
});

caseDetail.addEventListener("click", (event) => {
  const action = event.target.closest(".status-action");
  if (!action) return;

  const lead = data.leads.find((item) => item.rank === state.selectedRank);
  if (!lead) return;

  setWorkflowStatus(lead, action.dataset.status);
  renderLeadList();
});

renderLeadList();
