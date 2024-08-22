document.addEventListener('DOMContentLoaded', function() {
    // Set default webhook URL
    const webhookInput = document.getElementById('webhook');
    webhookInput.value = `${window.location.origin}/webhook`;

    // Load languages
    fetch('/js/languages.json')
        .then(response => response.json())
        .then(languages => {
            const fromLangSelect = document.getElementById('fromLang');
            const toLangSelect = document.getElementById('toLang');

            languages.forEach(lang => {
                const option = document.createElement('option');
                option.value = lang.code;
                option.textContent = lang.name;
                fromLangSelect.appendChild(option);
                toLangSelect.appendChild(option.cloneNode(true));
            });

            // Set default languages
            fromLangSelect.value = 'en-US';
            toLangSelect.value = 'es';
        })
        .catch(error => console.error('Error loading languages:', error));

    // Load voices
    fetch('/js/voices.json')
        .then(response => response.json())
        .then(voices => {
            const fromVoiceSelect = document.getElementById('fromVoice');
            const toVoiceSelect = document.getElementById('toVoice');

            voices.forEach(voice => {
                if (voice.id !== 'nPczCjzI2devNBz1zQrb') { // Remove Brian from the list
                    const option = document.createElement('option');
                    option.value = voice.id;
                    option.textContent = voice.name;
                    fromVoiceSelect.appendChild(option);
                    toVoiceSelect.appendChild(option.cloneNode(true));
                }
            });
        })
        .catch(error => console.error('Error loading voices:', error));

    document.getElementById('callForm').addEventListener('submit', function(event) {
        event.preventDefault();

        const caller = document.getElementById('caller').value;
        const callee = document.getElementById('callee').value;
        const fromLang = document.getElementById('fromLang').value;
        const toLang = document.getElementById('toLang').value;
        const fromVoice = document.getElementById('fromVoice').value;
        const toVoice = document.getElementById('toVoice').value;
        const recordCall = document.getElementById('recordCall').checked;
        const aiSummary = true;
        const liveEvents = true;
        const webhook = document.getElementById('webhook').value;

        const formData = {
            caller,
            callee,
            fromLang,
            toLang,
            fromVoice,
            toVoice,
            recordCall,
            aiSummary,
            liveEvents,
            webhook
        };

        fetch('/call', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById('callMessage').textContent = data.message;
            document.getElementById('uuid').textContent = data.uuid;
            document.getElementById('result').classList.remove('hidden');
            document.getElementById('callForm').classList.add('hidden');

            setTimeout(() => {
		if ((webhook && liveEvents) || (webhook && aiSummary)) {
		    const serverUrl = `${window.location.protocol}//${window.location.host}`;
		    window.location.href = `${serverUrl}/events?uuid=${data.uuid}`;
		} else {
                    document.getElementById('callForm').classList.remove('hidden');
                    document.getElementById('result').classList.add('hidden');
                    validateForm();
		}
            }, 5000); // 5 seconds

            document.getElementById('hangupButton').addEventListener('click', function() {
                fetch('/hangup', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ uuid: data.uuid })
                })
                .then(() => {
                    document.getElementById('callForm').classList.remove('hidden');
                    document.getElementById('result').classList.add('hidden');
                    validateForm();
                })
                .catch(error => {
                    console.error('Error:', error);
                    document.getElementById('callForm').classList.remove('hidden');
                    document.getElementById('result').classList.add('hidden');
                    validateForm();
                });
            });
        })
        .catch(error => {
            console.error('Error:', error);
            alert('There was an error starting the call. Please try again.');
        });
    });

    function validatePhoneNumber(phone) {
        try {
            const phoneNumber = libphonenumber.parsePhoneNumber(phone, 'US');
            return phoneNumber.isValid() && phoneNumber.format('E.164');
        } catch (error) {
            return false;
        }
    }

    function validateForm() {
        const caller = document.getElementById('caller').value;
        const callee = document.getElementById('callee').value;

        if (validatePhoneNumber(caller) && validatePhoneNumber(callee)) {
            document.querySelector('form button[type="submit"]').classList.remove('disabled');
            document.querySelector('form button[type="submit"]').disabled = false;
        } else {
            document.querySelector('form button[type="submit"]').classList.add('disabled');
            document.querySelector('form button[type="submit"]').disabled = true;
        }
    }

    document.addEventListener('input', validateForm);

    function toggleAdvancedOptions() {
        const advancedOptions = document.getElementById('advancedOptions');
        if (advancedOptions.classList.contains('hidden')) {
            advancedOptions.classList.remove('hidden');
        } else {
            advancedOptions.classList.add('hidden');
        }
    }

    document.querySelector('.advanced-toggle').addEventListener('click', toggleAdvancedOptions);
});

