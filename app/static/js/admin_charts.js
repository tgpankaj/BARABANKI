/**
 * Barabanki Connect — Admin Analytics Dashboard
 * Chart.js Integration for module listing distributions and activity metrics.
 */

window.initAdminDashboardCharts = function (statsData) {
  if (typeof Chart === "undefined") return;

  // Chart 1: Distribution of Listings by Module (Doughnut)
  const distCanvas = document.getElementById("distributionChart");
  if (distCanvas) {
    new Chart(distCanvas, {
      type: "doughnut",
      data: {
        labels: ["Businesses", "Jobs", "News", "Events", "Education", "Discussions"],
        datasets: [{
          data: [
            statsData.businesses || 0,
            statsData.jobs || 0,
            statsData.news || 0,
            statsData.events || 0,
            statsData.education || 0,
            statsData.posts || 0,
          ],
          backgroundColor: [
            "#1E3A8A", // Blue
            "#D97706", // Amber
            "#0D9488", // Teal
            "#8B5CF6", // Purple
            "#EC4899", // Pink
            "#10B981", // Emerald
          ],
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { boxWidth: 12, padding: 12 },
          },
        },
      },
    });
  }

  // Chart 2: Platform Activity & Engagement (Bar)
  const actCanvas = document.getElementById("activityChart");
  if (actCanvas) {
    new Chart(actCanvas, {
      type: "bar",
      data: {
        labels: ["Civic News", "Local Events", "Business Inquiries", "Job Applications", "Forum Comments"],
        datasets: [{
          label: "Monthly Interactions",
          data: [120, 85, 230, 140, 310],
          backgroundColor: "#3B82F6",
          borderRadius: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { beginAtZero: true, grid: { color: "rgba(0,0,0,0.05)" } },
          x: { grid: { display: false } },
        },
        plugins: {
          legend: { display: false },
        },
      },
    });
  }
};
