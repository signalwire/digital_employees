document.addEventListener('DOMContentLoaded', function() {
    const eventsTextarea = document.getElementById('events');
    const homeButton = document.getElementById('homeButton');
    const hangupButton = document.getElementById('hangupButton');
    const messageInput = document.getElementById("message-input");

    homeButton.addEventListener('click', function() {
        window.location.href = '/';
    });

    hangupButton.addEventListener('click', function() {
        // Send hangup request
        const uuid = getUrlParameter('uuid');
        if (uuid) {
            fetch('/hangup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ uuid: uuid })
            })
            .then(response => response.json())
            .then(data => {
                console.log('Hangup successful:', data);
                window.location.href = '/';
            })
            .catch(error => {
                console.error('Error:', error);
                window.location.href = '/';
            });
        }
    });

    // Function to get URL parameters
    function getUrlParameter(name) {
        const params = new URLSearchParams(window.location.search);
        return params.get(name);
    }

    // Get UUID from URL parameters
    const uuid = getUrlParameter('uuid');

    // Establish WebSocket connection
    const ws = new WebSocket(`wss://${window.location.host}/websocket`);

    if (uuid) {

        ws.onopen = function() {
            console.log('WebSocket connection established');
            // Send subscription message
            ws.send(JSON.stringify({ action: 'subscribe', uuid: uuid }));
        };

        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            const formattedMessage = JSON.stringify(data, null, 2);
            eventsTextarea.value += formattedMessage + '\n\n';
            eventsTextarea.scrollTop = eventsTextarea.scrollHeight;
        };

        ws.onclose = function() {
            const closeMessage = 'Connection closed';
            eventsTextarea.value += closeMessage + '\n';
            eventsTextarea.scrollTop = eventsTextarea.scrollHeight;
        };

        ws.onerror = function(error) {
            console.error('WebSocket error:', error);
        };
    } else {
        console.error('UUID not found in URL');
    }

    function appendMessage(message) {
        eventsTextarea.value += message + "\n";
        eventsTextarea.scrollTop = eventsTextarea.scrollHeight;
    }

    function sendMessage() {
        var message = messageInput.value.trim();
        if (message && ws && ws.readyState === WebSocket.OPEN) {
            var data = {
                uuid: uuid,
                timestamp: new Date().toISOString(),
                message: message
            };
            ws.send(JSON.stringify(data));
            appendMessage("Sent:\n" + JSON.stringify(data, null, 2));
            messageInput.value = "";
        }
    }

    document.getElementById("message-input").addEventListener("keypress", function(event) {
        if (event.keyCode === 13) {
            event.preventDefault();
            sendMessage();
        }
    });

});

