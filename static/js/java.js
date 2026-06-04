








window.onload = function() {
    // Check if a scroll position is saved in localStorage and directly scroll to it
    if (localStorage.getItem('scrollPosition')) {
        window.scrollTo(0, parseInt(localStorage.getItem('scrollPosition')));
    }

    // Save the scroll position when any like button is clicked
    document.querySelectorAll('.like-button').forEach(button => {
        button.addEventListener('click', function() {
            // Save the current scroll position to localStorage before the page reloads/redirects
            localStorage.setItem('scrollPosition', window.scrollY);
        });
    });

    // Optionally: Save scroll position for specific action buttons (if you have other actions)
    document.querySelector('#your-action-button')?.addEventListener('click', function() {
        localStorage.setItem('scrollPosition', window.scrollY);
    });

    // Remove scroll position from localStorage after a redirect (to avoid restoring it unnecessarily)
    const navigationEntries = window.performance.getEntriesByType('navigation');
    if (navigationEntries.length > 0 && navigationEntries[0].type === 'reload') {
        // If the page load is a reload (not a normal page load), remove the scroll position
        localStorage.removeItem('scrollPosition');
    }
};


    // Attach a click event listener to each button for toggling the visibility
    document.querySelectorAll('.toggleBtn').forEach((button, index) => {
        button.addEventListener('click', function() {
            // Get the corresponding dish details container
            var dishDetails = document.querySelectorAll('.dishDet3')[index];
            
            // Toggle visibility
            if (dishDetails.style.display === 'none' || !dishDetails.style.display) {
                dishDetails.style.display = 'block'; // Show content
                button.textContent = 'See Less';   // Change button text to "Show Less"
            } else {
                dishDetails.style.display = 'none'; // Hide content
                button.textContent = 'See More ...';   // Change button text to "Show More"
            }
        });
    });








    let timeout;

    document.getElementById('searchInput').addEventListener('input', function() {
        clearTimeout(timeout);
    
        const query = this.value;  // Get the value from the search input field
    
        timeout = setTimeout(() => {
            fetch(`/search_dishes/?q=${query}`)
                .then(response => response.json())  // Expecting JSON as response
                .then(data => {
                    const dishesSection = document.getElementById('dishes');
                    const usersSection = document.getElementById('users');
    
                    // Clear previous results
                    dishesSection.innerHTML = '';
                    usersSection.innerHTML = '';
    
                    // Populate dishes section
                    if (data.dishes.length > 0) {
                        data.dishes.forEach(dish => {
                            const dishElement = document.createElement('div');
                            dishElement.classList.add('dish-item');
                            dishElement.innerHTML = `
                                <a href="dish/${dish.id}">
                                    <img src="${dish.img_url}" alt="" class="profilePic">
                                    <div class="dish-info">
                                        <h4>${dish.name}</h4>
                                        <h6>Cuisine: ${dish.cuisine}</h6>
                                    </div>
                                </a>
                            `;
                            dishesSection.appendChild(dishElement);
                        });
                    } else {
                        dishesSection.innerHTML = '<h3>No dishes found!</h3>';
                    }
    
                    // Populate users section
                    if (data.users.length > 0) {
                        data.users.forEach(user => {
                            const userElement = document.createElement('div');
                            userElement.classList.add('user-item');
                            userElement.innerHTML = `
                                <a href="viewUser/${user.id}">
                                    <img src="${user.profile_img}" alt="" class="profilePic">
                                    <div class="user-info">
                                        <h4>${user.first_name}</h4>
                                    </div>
                                </a>
                            `;
                            usersSection.appendChild(userElement);
                        });
                    } else {
                        usersSection.innerHTML = '<h3>No users found!</h3>';
                    }
                })
                .catch(error => console.error('Error fetching search results:', error));
        }, 300);  // Wait for 300ms after the last input before sending the request
    });
    
    
    








    document.addEventListener("DOMContentLoaded", function() {
        console.log('Page Loaded');
        
        // Function to add event listeners to the buttons
        function addEventListenersToButtons() {
            const buttons = document.querySelectorAll('.toggle-button');
            
            buttons.forEach(button => {
                button.addEventListener('click', function() {
                    const target = this.getAttribute('data-target');
                    
                    // Hide both sections
                    document.getElementById('dishes').style.display = 'none';
                    document.getElementById('users').style.display = 'none';
                    
                    // Show the clicked target section
                    document.getElementById(target).style.display = 'block';
                    
                    // Optionally, highlight the active button
                    buttons.forEach(btn => btn.classList.remove('active'));
                    this.classList.add('active');
                });
            });
        }
    
        // Function to toggle visibility based on window width
        function toggleVisibility() {
            const dishesSection = document.getElementById('dishes');
            const usersSection = document.getElementById('users');
            
            if (!dishesSection || !usersSection) {
                console.error('Dishes or Users section is missing.');
                return;
            }
    
            if (window.innerWidth < 500) {
                // Attach event listeners only when screen is smaller than 500px
                dishesSection.style.display = 'block';

                addEventListenersToButtons();
            } else {
                // If the screen width is greater than or equal to 500px, show both sections
                dishesSection.style.display = 'block';
                usersSection.style.display = 'block';
                
                // Remove the active class when both sections are visible
                const buttons = document.querySelectorAll('.toggle-button');
                buttons.forEach(btn => btn.classList.remove('active'));
            }
        }
    
        // Check on page load
        toggleVisibility();
    
        // Check whenever the window is resized
        window.addEventListener('resize', toggleVisibility);
    });
    
    
    





