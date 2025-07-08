<template>
  <form name="contact" method="POST" data-netlify="true" class="contact-form">
    <div class="form-group">
      <label for="name" class="form-label">Name</label>
      <input
        type="text"
        name="name"
        id="name"
        class="form-input"
        required
      >
    </div>

    <div class="form-group">
      <label for="email" class="form-label">Email</label>
      <input
        type="email"
        name="email"
        id="email"
        class="form-input"
        required
      >
    </div>

    <div class="form-group">
      <label for="message" class="form-label">Message</label>
      <textarea
        name="message"
        id="message"
        rows="4"
        class="form-input"
        required
      ></textarea>
    </div>

    <!-- Netlify form handling -->
    <input type="hidden" name="form-name" value="contact">

    <div class="form-submit">
      <button
        type="submit"
        class="submit-button"
      >
        Send Message
      </button>
    </div>
  </form>
</template>

<script>
export default {
  name: 'ContactForm'
}
</script>

<style scoped>
.contact-form {
  margin-top: 3rem;
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-label {
  font-size: var(--font-size-sm);
  color: var(--color-light);
}

.form-input {
  width: 100%;
  padding: 0.75rem 1rem;
  border-radius: 0.375rem;
  background-color: rgba(31, 41, 55, 0.8);
  border: 1px solid rgba(75, 85, 99, 0.8);
  color: var(--color-light);
  transition: border-color 0.2s ease;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(211, 166, 254, 0.25);
}

.submit-button {
  padding: 0.75rem 1.5rem;
  background-color: var(--primary-color);
  color: var(--color-dark);
  font-weight: var(--font-weight-medium);
  border-radius: 0.375rem;
  border: none;
  cursor: pointer;
  transition: background-color 0.2s ease, transform 0.1s ease;
}

.submit-button:hover {
  background-color: #c28ef7;
  transform: translateY(-1px);
}

.submit-button:active {
  transform: translateY(1px);
}

/* Responsive adjustments */
@media (max-width: 640px) {
  .contact-form {
    max-width: 100%;
  }
}
</style>