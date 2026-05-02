document.addEventListener('DOMContentLoaded', () => {
    // 1. Submenu Click Toggle Logic (Keep your accordion logic)
    const submenuTriggers = document.querySelectorAll('.submenu-trigger');

    submenuTriggers.forEach(trigger => {
        trigger.addEventListener('click', (e) => {
            e.preventDefault(); 
            const wrapper = trigger.nextElementSibling;
            const isExpanded = trigger.getAttribute('aria-expanded') === 'true';

            submenuTriggers.forEach(otherTrigger => {
                otherTrigger.setAttribute('aria-expanded', 'false');
                otherTrigger.nextElementSibling.classList.remove('open');
            });

            trigger.setAttribute('aria-expanded', !isExpanded);
            wrapper.classList.toggle('open', !isExpanded);
        });
    });

    // 2. TRUE URL-Based Active State Logic
    const currentPath = window.location.pathname;
    const allLinks = document.querySelectorAll('.sidebar-link:not(.submenu-trigger), .sidebar-submenu a');

    allLinks.forEach(link => {
        // Prevent JS errors on '#' links
        if (link.getAttribute('href') === '#') return;

        // Parse the link's URL to compare pathnames accurately
        const linkPath = new URL(link.href, window.location.origin).pathname;

        // If the current browser URL matches the link's URL
        if (currentPath === linkPath) {
            // Strip the hardcoded active class from Dashboard (if it's there)
            document.querySelectorAll('.active').forEach(el => el.classList.remove('active'));

            // Light up the matched link
            link.classList.add('active');

            // If it's a submenu link, light up the parent and expand it
            const submenuWrapper = link.closest('.sidebar-submenu-wrapper');
            if (submenuWrapper) {
                // Expand the parent wrapper
                submenuWrapper.classList.add('open');
                
                // Find the parent trigger (e.g. "Products") and make it active/expanded
                const parentTrigger = submenuWrapper.previousElementSibling;
                if (parentTrigger && parentTrigger.classList.contains('submenu-trigger')) {
                    parentTrigger.setAttribute('aria-expanded', 'true');
                    parentTrigger.classList.add('active');
                }
            }
        }
    });
});