import os, glob, re

template_dir = r'd:\main project\foodgram\foodgram\templates'
ajax_script = """
<script>
    document.addEventListener("DOMContentLoaded", function() {
        document.querySelectorAll('a[href^="/save/"], a[href^="/unsave/"], a[href^="/report/"], a[href^="/follow/"], a[href^="/unfollow/"]').forEach(el => {
            el.addEventListener('click', function(e) {
                e.preventDefault();
                const href = this.getAttribute('href');
                
                // Visual update immediately for snappiness
                if (href.startsWith('/save/')) {
                    this.setAttribute('href', href.replace('/save/', '/unsave/'));
                    this.innerHTML = '<i class="fa-solid fa-bookmark me-2"></i> Unsave';
                } else if (href.startsWith('/unsave/')) {
                    this.setAttribute('href', href.replace('/unsave/', '/save/'));
                    this.innerHTML = '<i class="fa-regular fa-bookmark me-2"></i> Save';
                } else if (href.startsWith('/follow/')) {
                    this.setAttribute('href', href.replace('/follow/', '/unfollow/'));
                    this.innerHTML = '<i class="fa-solid fa-user-minus"></i> Unfollow';
                } else if (href.startsWith('/unfollow/')) {
                    this.setAttribute('href', href.replace('/unfollow/', '/follow/'));
                    this.innerHTML = '<i class="fa-solid fa-user-plus"></i> Follow';
                } else if (href.startsWith('/report/')) {
                    this.innerHTML = '<i class="fa-solid fa-check me-2"></i> Reported';
                    this.style.pointerEvents = 'none';
                }

                // Send background request
                fetch(href, {
                    method: 'GET',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                }).catch(err => console.error("Error:", err));
            });
        });
    });
</script>
"""

for filepath in glob.glob(os.path.join(template_dir, '*.html')):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Also add the view-transition meta tag just in case they meant page transitions too!
    if '<head>' in content and 'name="view-transition"' not in content:
        content = content.replace('<head>', '<head>\n    <meta name="view-transition" content="same-origin">')

    # Inject AJAX script right before </body> if not already there
    if '</body>' in content and 'a[href^="/save/"]' not in content:
        content = content.replace('</body>', ajax_script + '\n</body>')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Processed {os.path.basename(filepath)}')
