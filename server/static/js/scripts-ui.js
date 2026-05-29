$(document).ready(function() {

    // 1. Add/Update Script Form Async Submission
    $('#add-script-form').on('submit', function(e) {
        e.preventDefault();
        $.ajax({
            url: '/api/scripts/add',
            type: 'POST',
            data: $(this).serialize(),
            success: function(response) {
                location.reload();
            },
            error: function(err) {
                alert('Failed to save script components.');
            }
        });
    });

    // 2. Async Script Viewer Fetch and Markdown Parsing Action
    $('.view-script-btn').on('click', function() {
        const scriptPath = $(this).data('path');
        
        $.get('/api/scripts/view?path=' + encodeURIComponent(scriptPath), function(data) {
            $('#modal-script-title').text(scriptPath);
            
            // Wrap plain code in markdown code blocks natively
            const markdownContent = "```python\n" + data.content + "\n```";
            
            // Transform raw markdown structure into readable HTML strings
            const parsedHtml = marked.parse(markdownContent);
            
            // Populate content and apply Highlight.js styling logic
            $('#modal-script-markdown-body').html(parsedHtml);
            $('#modal-script-markdown-body pre code').each(function(i, block) {
                hljs.highlightElement(block);
            });
            
            $('#viewScriptModal').modal('show');
        }).fail(function() {
            alert('Could not locate file records.');
        });
    });

    // 3. Delete Script Operations
    $('.delete-script-btn').on('click', function() {
        const scriptPath = $(this).data('path');
        if (confirm('Are you certain you want to erase ' + scriptPath + '?')) {
            $.ajax({
                url: '/api/scripts/delete',
                type: 'POST',
                data: { path: scriptPath },
                success: function(response) {
                    location.reload();
                },
                error: function(err) {
                    alert('Error running deletion routine.');
                }
            });
        }
    });
});