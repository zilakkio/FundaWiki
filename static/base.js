document.addEventListener('DOMContentLoaded', () => {
    const body = document.body;
    const toggleButton = document.getElementById('dark-mode-toggle');
    const darkIcon = document.getElementById('dark-icon');
    const lightIcon = document.getElementById('light-icon');
    const darkRnd = document.getElementById('dark-rnd')
    const lightRnd = document.getElementById('light-rnd')
    const currentTheme = localStorage.getItem('theme') || 'dark'; // Default to dark mode

    // Set the initial icon and theme
    if (currentTheme === 'light') {
        body.classList.add('light-mode');
        darkIcon.style.display = 'block'; // Show moon icon
        lightIcon.style.display = 'none'; // Hide sun icon
        darkRnd.style.display = 'block';
        lightRnd.style.display = 'none';
    } else {
        darkIcon.style.display = 'none'; // Hide moon icon
        lightIcon.style.display = 'block'; // Show sun icon
        darkRnd.style.display = 'none';
        lightRnd.style.display = 'block';
    }

    toggleButton.addEventListener('click', () => {
        const isLightMode = body.classList.toggle('light-mode');
        if (isLightMode) {
            localStorage.setItem('theme', 'light');
            darkIcon.style.display = 'block';
            lightIcon.style.display = 'none';
            darkRnd.style.display = 'block';
            lightRnd.style.display = 'none';
        } else {
            localStorage.setItem('theme', 'dark');
            darkIcon.style.display = 'none';
            lightIcon.style.display = 'block';
            darkRnd.style.display = 'none';
            lightRnd.style.display = 'block';
        }
    });
});
