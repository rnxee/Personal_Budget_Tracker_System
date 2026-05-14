document.addEventListener("submit", (event) => {
  const form = event.target;
  const message = form.getAttribute("data-confirm");
  if (message && !window.confirm(message)) {
    event.preventDefault();
  }
});

function filterCategoryOptions(form) {
  const typeSelect = form.querySelector("[data-transaction-type]");
  const categorySelect = form.querySelector("[data-category-select]");
  if (!typeSelect || !categorySelect) {
    return;
  }

  const selectedType = typeSelect.value;
  let firstVisible = null;

  Array.from(categorySelect.options).forEach((option) => {
    const shouldShow = option.dataset.type === selectedType;
    option.hidden = !shouldShow;
    option.disabled = !shouldShow;
    if (shouldShow && firstVisible === null) {
      firstVisible = option;
    }
  });

  const currentOption = categorySelect.options[categorySelect.selectedIndex];
  if (currentOption && currentOption.hidden && firstVisible) {
    firstVisible.selected = true;
  }
}

document.querySelectorAll("[data-category-filter]").forEach((form) => {
  filterCategoryOptions(form);
  form.querySelector("[data-transaction-type]").addEventListener("change", () => {
    filterCategoryOptions(form);
  });
});