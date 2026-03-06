function displayTime() {
    // Get all the rows
    var rows = document.querySelectorAll('tr[data-timestamp]');

    // Loop through each row
    for (var i = 0; i < rows.length; i++) {
        // Get the timestamp
        var timestamp = rows[i].getAttribute('data-timestamp');

        // Convert the timestamp to milliseconds
        var date = new Date(timestamp * 1000);

        // Format the date and time
        var dateString = date.toLocaleString();

        // Create a new element for the date
        var dateElement = document.createElement('p');
        dateElement.textContent = dateString;

        // Add the date element to the post header
        var postHeader = rows[i].querySelector('.post-header div');
        postHeader.appendChild(dateElement);
    }
}

// Call the function when the page loads
window.onload = displayTime;