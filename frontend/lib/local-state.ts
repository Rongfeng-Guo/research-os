const LAST_PROJECT_KEY = "research_os_last_project_id";
const PROJECT_TOUR_DISMISSED_KEY = "research_os_project_tour_dismissed";

function canUseStorage() {
  return typeof window !== "undefined";
}

export function getLastProjectId(): number | null {
  if (!canUseStorage()) return null;
  const value = window.localStorage.getItem(LAST_PROJECT_KEY);
  if (!value) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function setLastProjectId(projectId: number) {
  if (!canUseStorage()) return;
  window.localStorage.setItem(LAST_PROJECT_KEY, String(projectId));
}

export function isProjectTourDismissed() {
  if (!canUseStorage()) return false;
  return window.localStorage.getItem(PROJECT_TOUR_DISMISSED_KEY) === "true";
}

export function dismissProjectTour() {
  if (!canUseStorage()) return;
  window.localStorage.setItem(PROJECT_TOUR_DISMISSED_KEY, "true");
}
