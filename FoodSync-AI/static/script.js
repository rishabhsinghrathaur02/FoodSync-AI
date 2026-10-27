// Small progressive enhancement: confirm high-impact demo actions.
document.querySelectorAll('form[action$="/disruption"]').forEach((form) => {
  form.addEventListener("submit", (event) => {
    const confirmed = window.confirm(
      "Run the simulated delivery-partner disruption? This changes demo availability and attempts recovery."
    );
    if (!confirmed) event.preventDefault();
  });
});

document.querySelectorAll('form[action$="/allocate"]').forEach((form) => {
  form.addEventListener("submit", (event) => {
    const confirmed = window.confirm(
      "Run allocation using eligible listings, NGO demand and available NGO delivery partners?"
    );
    if (!confirmed) event.preventDefault();
  });
});
