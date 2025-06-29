// FAQ toggle
document.querySelectorAll('.faq h2').forEach(item => {
  item.addEventListener('click', () => {
    const details = item.nextElementSibling;
    details.style.display = details.style.display === 'block' ? 'none' : 'block';
  });
});

// Dropdown toggle
function toggleDropdown() {
  const dd = document.getElementById('dropdown');
  if (dd) {
    dd.style.display = dd.style.display === 'block' ? 'none' : 'block';
  }
}

// Select existing location
const savedList = document.querySelectorAll('#saved-list li');
if (savedList.length) {
  savedList.forEach(li => {
    li.addEventListener('click', () => {
      const loc = {
        id: li.dataset.id,
        zip: li.dataset.zip,
        description: li.dataset.desc,
        latitude: li.dataset.lat,
        longitude: li.dataset.lon
      };
      fetch('/save_location', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loc)
      }).then(() => location.reload());
    });
  });
}

// Add new location
const addForm = document.getElementById('add-form');
if (addForm) {
  addForm.addEventListener('submit', async e => {
    e.preventDefault();
    const zipcode = document.getElementById('zipcode').value;
    const city = document.getElementById('city').value;
    const res = await fetch('/add_location', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ zipcode, city })
    });
    if (res.ok) location.reload();
    else alert('Error adding location');
  });
}

// Close dropdown on outside click
window.addEventListener('click', e => {
  const dd = document.getElementById('dropdown');
  if (dd && !dd.contains(e.target) && !e.target.classList.contains('dropdown-btn')) {
    dd.style.display = 'none';
  }
});
