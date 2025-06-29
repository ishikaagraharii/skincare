
  let map = null;
  let marker = null;

  // Initialize map
  function initMap() {
      if (map) {
          map.remove();
      }
      map = L.map('map').setView([20.5937, 78.9629], 5); // Default to India
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '© OpenStreetMap contributors'
      }).addTo(map);
  }

  // Update map with city coordinates
  async function updateMap(cityName) {
      try {
          // Use a geocoding service to get coordinates
          const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(cityName)}&limit=1`);
          const data = await response.json();

          if (data && data.length > 0) {
              const lat = parseFloat(data[0].lat);
              const lon = parseFloat(data[0].lon);

              // Show map section
              document.getElementById('mapSection').style.display = 'block';

              // Initialize map if not already done
              if (!map) {
                  initMap();
              }

              // Update map view
              map.setView([lat, lon], 12);

              // Remove existing marker
              if (marker) {
                  map.removeLayer(marker);
              }

              // Add new marker
              marker = L.marker([lat, lon]).addTo(map)
                  .bindPopup(`<b>${cityName}</b><br>Your skincare analysis location`)
                  .openPopup();
          }
      } catch (error) {
          console.log('Map update failed:', error);
          // Map functionality is optional, so we don't show error to user
      }
  }

  document.getElementById('cityForm').addEventListener('submit', async function(e) {
      e.preventDefault();

      const city = document.getElementById('cityInput').value.trim();
      const loadingDiv = document.getElementById('loadingDiv');
      const resultsDiv = document.getElementById('resultsDiv');
      const searchBtn = document.getElementById('searchBtn');

      if (!city) {
          alert('Please enter a city name');
          return;
      }

      // Show loading
      loadingDiv.style.display = 'block';
      resultsDiv.innerHTML = '';
      searchBtn.disabled = true;

      // Update map with searched city
      await updateMap(city);

      try {
          const response = await fetch('/get_products_by_city', {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json',
              },
              body: JSON.stringify({ city: city })
          });

          const data = await response.json();

          if (data.error) {
              throw new Error(data.error);
          }

          displayResults(data);

      } catch (error) {
          console.error('Error:', error);
          resultsDiv.innerHTML = `
              <div class="error-message">
                  <i class="fas fa-exclamation-triangle"></i>
                  <strong>Error:</strong> ${error.message}
                  <br><small>Please check the city name and try again.</small>
              </div>
          `;
      } finally {
          loadingDiv.style.display = 'none';
          searchBtn.disabled = false;
      }
  });


  async function getRecommendationsByCity() {
      const city = document.getElementById('cityInput').value.trim();

      if (!city) {
          showError('Please enter a city name');
          return;
      }

      showLoading(true);
      hideError();

      try {
          const response = await fetch('/get_products_by_city', {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json',
              },
              body: JSON.stringify({ city: city })
          });

          if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
          }

          const data = await response.json();

          if (data.error) {
              showError(data.error);
              return;
          }

          displayRecommendations(data);
          displayEnvironmentalData(data);

      } catch (error) {
          console.error('Error:', error);
          showError('Failed to get recommendations. Please try again.');
      } finally {
          showLoading(false);
      }
  }

  /**
   * Get recommendations with manual environmental data
   */


  function displayResults(data) {
      const resultsDiv = document.getElementById('resultsDiv');

      // Get ML recommendation
      const mlRecommendation = data.ml_recommendation ? data.ml_recommendation.recommendation : null;

      console.log('=== DEBUGGING ===');
      console.log('ML Recommendation:', mlRecommendation);
      console.log('Products:', data.products.map(p => ({ name: p.name, id: p.id })));
      console.log('================');

      let html = '';

      // Weather Information
      html += `
          <div class="weather-info">
              <div class="weather-card">
                  <i class="fas fa-thermometer-half"></i>
                  <h3>${Math.round(data.current_temp)}°C</h3>
                  <p>Temperature</p>
              </div>
              <div class="weather-card">
                  <i class="fas fa-tint"></i>
                  <h3>${data.humidity}%</h3>
                  <p>Humidity</p>
              </div>
              <div class="weather-card">
                  <i class="fas fa-wind"></i>
                  <h3>${data.wind_speed} m/s</h3>
                  <p>Wind Speed</p>
              </div>
              <div class="weather-card">
                  <i class="fas fa-smog"></i>
                  <h3>AQI ${data.pollution_data.aqi}</h3>
                  <p>Air Quality</p>
              </div>
          </div>
      `;

      // ML Recommendation Info
      // if (data.ml_recommendation) {
      //     const confidence = Math.round(data.ml_recommendation.confidence * 100);
      //     html += `
      //         <div class="ml-info">
      //             <h3>
      //                 <i class="fas fa-robot"></i>
      //                 AI Analysis Complete
      //             </h3>
      //             <p><strong>Recommended Product:</strong> ${data.ml_recommendation.recommendation}</p>
      //             <p><strong>Confidence:</strong> ${confidence}%</p>
      //             <div class="confidence-bar">
      //                 <div class="confidence-fill" style="width: ${confidence}%"></div>
      //             </div>
      //             ${data.ml_recommendation.environmental_analysis ? `
      //                 <p style="margin-top: 15px; opacity: 0.9;">
      //                     <small>
      //                         Environment: ${data.ml_recommendation.environmental_analysis.pollution_level} pollution, 
      //                         ${data.ml_recommendation.environmental_analysis.humidity_category} humidity, 
      //                         ${data.ml_recommendation.environmental_analysis.temp_category} temperature
      //                     </small>
      //                 </p>
      //             ` : ''}
      //         </div>
      //     `;
      // }

      // Separate recommended and other products
      const recommendedProducts = [];
      const otherProducts = [];

      if (data.products && data.products.length > 0) {
          data.products.forEach(product => {
              const isRecommended = mlRecommendation && product.name === mlRecommendation;
              if (isRecommended) {
                  recommendedProducts.push(product);
              } else {
                  otherProducts.push(product);
              }
          });
      }

      // Recommended Products Section (at top)
      if (recommendedProducts.length > 0) {
          // html += '<h2 class="section-title">✨ AI Recommended for You</h2>';
          html += '<div class="recommended-section">';
          html += '<div class="products-grid">';

          recommendedProducts.forEach(product => {
              html += `
                  <div class="product-card recommended">
                      <div class="recommended-badge">  Recommended</div>
                      <img src="${product.image_url || 'https://via.placeholder.com/300x250?text=VÉRAÉ+Product'}" 
                           alt="${product.name}" class="product-image" 
                           onerror="this.src='https://via.placeholder.com/300x250?text=VÉRAÉ+Product'">
                      <div class="product-info">
                          <h3 class="product-name">${product.name}</h3>
                          <div class="product-category">${product.category || 'Skincare'}</div>
                          <p class="product-description">${product.description || 'Premium skincare product for your daily routine.'}</p>
                          <div class="product-price">₹${product.price || '999'}</div>
                          <button class="buy-btn recommended-btn" onclick="buyProduct('${product.name}')">
                              <i class="fas fa-shopping-cart"></i> Add to Cart
                          </button>
                      </div>
                  </div>
              `;
          });

          html += '</div>';
          html += '</div>';
      }

      // Other Products Section
      if (otherProducts.length > 0) {
          html += '<h2 class="section-title other-products">Other Skincare Products</h2>';
          html += '<div class="products-grid">';

          otherProducts.forEach(product => {
              html += `
                  <div class="product-card">
                      <img src="${product.image_url || 'https://via.placeholder.com/300x250?text=VÉRAÉ+Product'}" 
                           alt="${product.name}" class="product-image" 
                           onerror="this.src='https://via.placeholder.com/300x250?text=VÉRAÉ+Product'">
                      <div class="product-info">
                          <h3 class="product-name">${product.name}</h3>
                          <div class="product-category">${product.category || 'Skincare'}</div>
                          <p class="product-description">${product.description || 'Premium skincare product for your daily routine.'}</p>
                          <div class="product-price">₹${product.price || '999'}</div>
                          <button class="buy-btn" onclick="buyProduct('${product.name}')">
                              <i class="fas fa-shopping-cart"></i> Add to Cart
                          </button>
                      </div>
                  </div>
              `;
          });

          html += '</div>';
      }

      // No products fallback
      if (recommendedProducts.length === 0 && otherProducts.length === 0) {
          html += `
              <div class="no-products">
                  <i class="fas fa-search"></i>
                  <h3>No products found</h3>
                  <p>We couldn't find any products for your location. Please try a different city.</p>
              </div>
          `;
      }

      resultsDiv.innerHTML = html;
  }

  function buyProduct(productName) {
      alert(`Adding "${productName}" to cart! This would redirect to payment page in a real application.`);
  }

  // Add some sample interactions
  document.getElementById('cityInput').addEventListener('input', function() {
      this.value = this.value.replace(/[^a-zA-Z\s]/g, '');
  });

  // Enter key support
  document.getElementById('cityInput').addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
          document.getElementById('cityForm').dispatchEvent(new Event('submit'));
      }
  });