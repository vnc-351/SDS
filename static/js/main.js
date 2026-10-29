// ==========================================================================
// CampusFix - Main Frontend Script
// Preserves form submission integrity, vote handling, and adds subtle UI polish
// ==========================================================================

document.addEventListener('DOMContentLoaded', function () {
  // Preserve original form submission behavior
  const forms = document.querySelectorAll('form');

  forms.forEach(function (form) {
    form.addEventListener('submit', function (event) {
      // Use the button that was actually clicked (e.g. Upvote vs Downvote),
      // falling back to the form's first submit button.
      const submitButton = event.submitter || form.querySelector('button[type="submit"]');

      if (!submitButton) {
        return;
      }

      // Disable AFTER the browser has collected the form data.
      // A disabled button's name/value is not sent, which used to drop the vote value.
      setTimeout(function () {
        submitButton.dataset.originalText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.textContent = 'Submitting...';
      }, 0);
    });
  });

  // If the user comes back with the browser's Back button,
  // re-enable the buttons.
  window.addEventListener('pageshow', function (event) {
    if (!event.persisted) {
      return;
    }

    document.querySelectorAll('button[data-original-text]').forEach(function (button) {
      button.disabled = false;
      button.textContent = button.dataset.originalText;
    });
  });

  // Smooth dismiss animation for alerts (pure visual enhancement)
  const alerts = document.querySelectorAll('.alert');

  alerts.forEach(function (alert) {
    alert.addEventListener('close.bs.alert', function () {
      alert.style.transition = 'opacity 250ms ease, transform 250ms ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-6px)';
    });
  });
});