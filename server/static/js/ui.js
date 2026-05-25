function padLeft(s, length) {
    s = s.toString();
    while (s.length < length)
        s = '0' + s;
    return s;
}

function dateToString(date) {
    return padLeft(date.getFullYear(), 4) + '-' + padLeft(date.getMonth() + 1, 2) + '-' +
        padLeft(date.getDate(), 2) + ' ' +
        padLeft(date.getHours(), 2) + ':' + padLeft(date.getMinutes(), 2) + ':' +
        padLeft(date.getSeconds(), 2);
}

function escapeHtml(text) {
    return $('<div>').text(text).html();
}

function generateFlagTableRows(rows) {
    var html = '';
    rows.forEach(function (item) {
        
        var cells = [
            item.sploit,
            item.team !== null ? item.team : '',
            item.flag,
            dateToString(new Date(item.time * 1000)),
            item.status,
            item.checksystem_response !== null ? item.checksystem_response : ''
        ];

// Define your status color mapping (using nice, readable background/text combinations)
    var statusStyles = {
        'QUEUED':   { bg: '#e0f2fe', text: '#0369a1' }, // Light Blue
        'SKIPPED':  { bg: '#f3f4f6', text: '#4b5563' }, // Light Gray
        'ACCEPTED': { bg: '#dcfce7', text: '#15803d' }, // Light Green
        'REJECTED': { bg: '#fee2e2', text: '#b91c1c' }  // Light Red
    };

    var currentStatus = item.status;
    var statusHtml = escapeHtml(currentStatus);

    // If the status matches one of our keys, wrap it in a styled span
    if (statusStyles[currentStatus]) {
        var style = statusStyles[currentStatus];
        statusHtml = '<span style="background-color:' + style.bg + '; color:' + style.text + '; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; display: inline-block;">' + statusHtml + '</span>';
    }

    var cells = [
        item.sploit,
        item.team !== null ? item.team : '',
        item.flag,
        dateToString(new Date(item.time * 1000)),
        statusHtml, // Insert the styled HTML instead of raw text
        item.checksystem_response !== null ? item.checksystem_response : ''
    ];

    html += '<tr>';
    cells.forEach(function (text, index) {
        // Since statusHtml contains raw tags now, don't escape it a second time
        if (index === 4) { 
            html += '<td>' + text + '</td>';
        } else {
            html += '<td>' + escapeHtml(text) + '</td>';
        }
    });
    html += '</tr>';
    });
    return html;
}

function generatePaginator(totalCount, rowsPerPage, pageNumber) {
    var totalPages = Math.ceil(totalCount / rowsPerPage);
    var firstShown = Math.max(1, pageNumber - 3);
    var lastShown = Math.min(totalPages, pageNumber + 3);

    var html = '';
    if (firstShown > 1)
        html += '<li class="page-item"><a class="page-link" href="#" data-content="1">«</a></li>';

    for (var i = firstShown; i <= lastShown; i++) {
        var extraClasses = (i === pageNumber ? "active" : "");
        html += '<li class="page-item ' + extraClasses + '">' +
            '<a class="page-link" href="#" data-content="' + i + '">' + i + '</a>' +
        '</li>';
    }

    if (lastShown < totalPages)
        html += '<li class="page-item">' +
            '<a class="page-link" href="#" data-content="' + totalPages + '">»</a>' +
        '</li>';
    return html;
}

function getPageNumber() {
    return parseInt($('#page-number').val());
}

function setPageNumber(number) {
    $('#page-number').val(number);
}

var queryInProgress = false;

function showFlags() {
    if (queryInProgress)
        return;
    queryInProgress = true;

    $('.search-results').hide();
    $('.query-status').html('Loading...').show();

    $.post('/ui/show_flags', $('#show-flags-form').serialize())
        .done(function (response) {
            $('.search-results tbody').html(generateFlagTableRows(response.rows));

            $('.search-results .total-count').text(response.total_count);
            $('.search-results .pagination').html(generatePaginator(
                response.total_count, response.rows_per_page, getPageNumber()));
            $('.search-results .page-link').click(function (event) {
                event.preventDefault();

                setPageNumber($(this).data("content"));
                showFlags();
            });

            $('.query-status').hide();
            $('.search-results').show();
        })
        .fail(function () {
            $('.query-status').html("Failed to load flags from the farm server");
        })
        .always(function () {
            queryInProgress = false;
        });
}

function postFlagsManual() {
    if (queryInProgress)
        return;
    queryInProgress = true;

    $.post('/ui/post_flags_manual', $('#post-flags-manual-form').serialize())
        .done(function () {
            var sploitSelect = $('#sploit-select');
            if ($('#sploit-manual-option').empty())
                sploitSelect.append($('<option id="sploit-manual-option">Manual</option>'));
            sploitSelect.val('Manual');

            $('#team-select, #flag-input, #time-since-input, #time-until-input, ' +
              '#status-select, #checksystem-response-input').val('');

            queryInProgress = false;
            showFlags();
        })
        .fail(function () {
            $('.query-status').html("Failed to post flags to the farm server");
            queryInProgress = false;
        });
}

$(function () {
    showFlags();

    $('#show-flags-form').submit(function (event) {
        event.preventDefault();

        setPageNumber(1);
        showFlags();
    });
    $('#post-flags-manual-form').submit(function (event) {
        event.preventDefault();

        postFlagsManual();
    });
});
