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
      // Disable AFTER the browser has collected the form data. A disabled
      // button's name/value is not sent, which used to drop the vote value.
      setTimeout(function () {
        submitButton.dataset.originalText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.textContent = 'Submitting...';
      }, 0);
    });
  });

  // If the user comes back with the browser's Back button, re-enable the buttons.
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

  // Landing Page Hero Title: Select title per session and apply entrance animation
  const rotatingTitle = document.querySelector('.hero-rotating-title');
  if (rotatingTitle && !rotatingTitle.dataset.initialized) {
    const phrases = Array.from(rotatingTitle.querySelectorAll('.rotate-phrase'));
    if (phrases.length > 0) {
      let targetIndex = 0;
      try {
        const sessionIndex = sessionStorage.getItem('campusfix_session_title_index');
        if (sessionIndex !== null && !isNaN(parseInt(sessionIndex, 10))) {
          // Preserve the same title during the current session
          targetIndex = parseInt(sessionIndex, 10) % phrases.length;
        } else {
          // Advance to the next title in order for a new session
          const lastIndex = localStorage.getItem('campusfix_last_title_index');
          if (lastIndex !== null && !isNaN(parseInt(lastIndex, 10))) {
            targetIndex = (parseInt(lastIndex, 10) + 1) % phrases.length;
          } else {
            targetIndex = 0;
          }
          localStorage.setItem('campusfix_last_title_index', targetIndex.toString());
          sessionStorage.setItem('campusfix_session_title_index', targetIndex.toString());
        }
      } catch (e) {
        // Fallback to first title if browser storage is unavailable
        targetIndex = 0;
      }

      phrases.forEach(function (phrase, index) {
        if (index === targetIndex) {
          phrase.classList.add('is-active', 'hero-title-animate');
          phrase.setAttribute('aria-hidden', 'false');
        } else {
          phrase.classList.remove('is-active', 'hero-title-animate');
          phrase.setAttribute('aria-hidden', 'true');
        }
      });
      rotatingTitle.dataset.initialized = 'true';
    }
  }
});
