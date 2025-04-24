var html1 =
    '    <link rel="stylesheet" href="' + base_url + 'assets/bot/fonts/material_style.css" rel="stylesheet"/>' +
    '    <link rel="stylesheet" href="' + base_url + 'assets/bot/css/bot.css">' +
    '    <div class="chatting-environment" id="chatting-environment">' +
    '        <div class="chat-board">' +
    '            <div class="chat-board__top">' +
    '                <img src="' + base_url + 'assets/bot/img/avatar.svg" alt="avatar">' +
    '                <h3 class="top-heading mb-0">Need Help? Ask EKAM</h3>' +
    '                <div class="staging-close-btn-new" onclick="clearChat()">' +
    '                     <span class="material-symbols-outlined" title="clear chat">delete</span>' +
    '                </div>' +
    '        <div class="staging-close-btn-chat">' +
    '               <span class="material-symbols-outlined" title="close">' +
    '                   close' +
    '          </span>' +
    '        </div>' +
    '            </div>' +
    '            <div class="chat_base_chatting">' +
    '               <div class="chat-board__chatting-area" id="staging">' +
    '                <div class="chat-board__chatting-area__heading" >' +
    '                       <span id="greeting" class="greeting" ></span>' +
    '						<span class="heading" >Hi, I am EKAM. I am here to help you with your queries related to EKAM. Please choose your preferred language to communicate</span>' +
    '                </div>' +
    '                <div class="chat_op_buttons" id="rm_lang">' +
    '                   <button class="badges" value="eng_Latn">English</button>' +
    '                   <button class="badges" value="hin_Deva">Hindi</button>' +
    '                   <button class="badges" value="tel_Telu">Telugu</button>' +
    '                   <button class="badges" value="guj_Gujr">Gujrati</button>' +
    '                   <button class="badges" value="mar_Deva">Marathi</button>' +
    '                   <button class="badges" value="ben_Beng">Bengali</button>' +
    '                </div> ' +
    '                </div>' +
    '            <div class="chat-board__bottom">' +
    '                <div class="chat-input">' +
    '                    <div class="input-sec">' +
    '                            <div class="input_img" onclick="initMicRecorder()">' +
    '                                   <span id="micIcon" class="material-symbols-outlined" style="color: rgb(6, 56, 105);">mic</span>    ' +

    '                            </div>' +

    '                        <input type="text" id="txtInput" placeholder="Type a message..." autofocus />' +
    '                        <button type="button" onclick="send_msg()" name="submit" id="press_enter_stag" hidden="">SUBMIT</button>' +
    '                    </div>' +
    '                    <div id="recordingActions" style="display: none;" class="recording-buttons">' +
    '                         <div class="wave-container" id="wave">' +
    '                         </div> ' +
    '                         <button id="sendRecording" class="btn confirm"><span class="material-symbols-outlined">check</span></button>' +
    '                         <button id="cancelRecording" class="btn cancel"><span class="material-symbols-outlined">close</span></button>' +
    '                    </div>' +
    '                    <div class="send" onclick="check_data_stag()">' +
    '                        <img src="' + base_url + 'assets/bot/img/icons/send-icon.png" alt="send-icon">' +
    '                    </div>' +
    '                    <div class="stop hidden" onclick="stopSending()" >' +
    '                        <img src="' + base_url + 'assets/bot/img/icons/stop.png" style="width: 25px;height: 25px;" alt="stop-icon">' +
    '                    </div>' +
    '                </div>' +
    '                </div>' +
    '            </div>' +
    '        </div>' +
    '        <div class="staging-close-btn">' +
    '               <span class="material-symbols-outlined">' +
    '                   <img src="static/assets/img/avatar.svg" alt="user image">' +
    '          </span>' +
    '        </div>' +
    '    </div>' +
    '    <div class="error-environment" style="display: none;" id="error-environment">' +
    '        <div class="chat-board">' +
    '            <div class="chat-board__top">' +
    '                <h3 class="top-heading">Staging Environment</h3>' +
    '            </div>' +
    '            <div class="chat-board__chatting-area" id="error">' +
    '             <div class="particular-chat-wrapper">' +
    '                    <h4 class="chat user1">Access Denied. Please contact admin</h4>' +
    '                </div>' +
    '            </div>' +
    '        </div>' +
    '        <div class="staging-close-btn">' +
    '            <span class="material-symbols-outlined">chat</span>' +
    '        </div>' +
    '    </div>';

// var base_url = 'http://127.0.0.1:6001/static/'
// var ip = '127.0.0.1:6001'

var base_url = 'http://172.27.220.210:6001/static/'
var ip = '172.27.220.210:6001'
document.addEventListener("DOMContentLoaded", function() {
    $('body').append(html1)
    var txtInputStag = document.getElementById('txtInput');
    txtInputStag.placeholder = "Type a message...";
    txtInputStag.focus()
});

function scrollToBottom() {
    $('#staging').scrollTop($('#staging')[0].scrollHeight);
}

function createAudioBars(containerId, numBars = 33, delayStep = 0.1) {
    const container = document.getElementById(containerId);
    container.innerHTML = ""; // Clear existing bars if any

    for (let i = 0; i < numBars; i++) {
        const bar = document.createElement('div');
        bar.classList.add('bar');
        bar.style.animationDelay = `${i * delayStep}s`;
        container.appendChild(bar);
    }
}

// Call the function to create the animation

function escapeHTML(str) {
    return str.replace(/[&<>"'/]/g, (char) => {
        const escapeMap = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;',
            '/': '&#x2F;',
        };
        return escapeMap[char] || char;
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // Get all the language buttons
    const languageButtons = document.querySelectorAll('.badges');

    // Add event listener to each button
    languageButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Get the value of the clicked button (the selected language)
            const selectedLanguage = this.value;
            var msg = $(this).text().trim()
                // Store the selected language in sessionStorage
            sessionStorage.setItem('preferredLanguage', selectedLanguage);
            $("#staging").append(`
                    <div class='d-flex class particular-chat-wrapper'>
                        <h4 class='chat user2'>${msg}</h4>
                        <div class='user2-name-letter name-letter'>
                            <img src='${base_url}assets/bot/img/avatar.svg' alt='user'>
                        </div>
                    </div>
                `);

            $('#txtInput').val("");

            // Add typing indicator bubble

            // Remove any previous error or processing states
            $('#rm_lang').addClass('hidden');
            var typingBubble = $("<div class='chat-bubble bot-bubble typing-indicator'>.</div>");
            $('#staging').append(typingBubble);
            scrollToBottom();
            // Scroll to the bottom to display new messages
            $('#staging').scrollTop($('#staging')[0].scrollHeight);
            $.ajax({
                type: "POST",
                contentType: "application/x-www-form-urlencoded; charset=UTF-8",
                url: "http://" + ip + "/bot_msg_llmbot",
                data: { msg: 'hi', type: 'prod', emp_no: emp_no, preferredLanguage: sessionStorage.getItem('preferredLanguage') || 'eng_Latn' },
                success: function(result) {
                    $("#txtInput").removeAttr('disabled');
                    var txtInputStag = document.getElementById('txtInput');
                    txtInputStag.disabled = false;
                    txtInputStag.placeholder = "Type a message...";
                    txtInputStag.focus()
                    typingBubble.remove();
                    // Animate the result word by word
                    animateTextInH4(result);
                    scrollToBottom()

                    $('#staging').scrollTop($('#staging')[0].scrollHeight);

                }
            });

            // Optionally, show an alert or change something on the page

        });

        // Check if there is a stored language on page load and apply it
        const storedLanguage = sessionStorage.getItem('preferredLanguage');
        if (storedLanguage) {
            console.log('Preferred Language:', storedLanguage);
        } else {
            console.log('No preferred language set.');
        }
    });
});
window.addEventListener('load', () => {
    sessionStorage.removeItem('preferredLanguage'); // Remove the language setting on page load
    console.log("Preferred language cleared on page load.");
});
window.onload = function() {
    const currentHour = new Date().getHours();
    let greeting;

    if (currentHour >= 5 && currentHour < 12) {
        greeting = "Good Morning!";
    } else if (currentHour >= 12 && currentHour < 18) {
        greeting = "Good Afternoon!";
    } else if (currentHour >= 18 && currentHour < 21) {
        greeting = "Good Evening!";
    } else {
        greeting = "Good Night!";
    }

    // Display greeting in a div with ID 'greeting'
    document.getElementById("greeting").textContent = greeting;
}

// Call the function to get the greeting

$(document).ready(function() {
    $(".staging-close-btn").click(function() {
        $(".chatting-environment .chat-board").toggle();
        if ($(".staging-close-btn span").text() == "closeclose") {
            $(".staging-close-btn span").css('transform', 'rotate(0deg)');
            $(".staging-close-btn span").html('<img src="' + base_url + 'assets/bot/img/avatar.svg" alt="avatar">');
            $(".staging-close-btn").css('background', 'transparent');


        } else {
            $(".staging-close-btn-chat").css('dispay', 'block');
            $(".staging-close-btn").hide();
            var txtInputStag = document.getElementById('txtInput');
            txtInputStag.placeholder = "Type a message...";
            txtInputStag.focus()

        }
    });


});

$(document).ready(function() {
    // Handle the click on the .staging-close-btn-chat
    $(".staging-close-btn-chat").click(function() {

        $(".chatting-environment .chat-board").toggle();
        $(".staging-close-btn").show();
        // Reset the styles and content of the .staging-close-btn span
        $(".staging-close-btn span").css('transform', 'rotate(0deg)');
        $(".staging-close-btn span").html('<img src="' + base_url + 'assets/bot/img/avatar.svg" alt="avatar">');
        $(".staging-close-btn").css('background', 'transparent');
    });
});


function animateTextInH4(result) {
    var $resultDiv = $(result);
    var $h4 = $resultDiv.find('h4');
    var $chatOpButtons = $resultDiv.find('.chat_op_buttons');
    var $feedbackdiv = $resultDiv.find('div')
    var text = $h4.text();
    var words = text.split(' ');
    var i = 0;
    var newDiv = $("<div class='class particular-chat-wrapper-user2'></div>");
    var newH4 = $("<h4 class='chat user1'></h4>");
    newDiv.append(newH4);
    $('#staging').append(newDiv);
    var interval = setInterval(function() {
        if (i < words.length) {
            newH4.append(words[i] + ' ');
            i++;
            scrollToBottom();
        } else {
            clearInterval(interval);
            $('#staging').scrollTop($('#staging')[0].scrollHeight);
            newDiv.append($feedbackdiv)
            $('#staging').append($chatOpButtons);
            var currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            var timeSpan = $("<span class='chat-time'></span>").text(currentTime); // Create a span for the time
            newH4.append(timeSpan);
            scrollToBottom()



        }
    }, 100);

    $('.stop').addClass('hidden');
    $('.send').removeClass('hidden').addClass('visible');
    scrollToBottom()
        // Adjust the interval time for speed
}

function decodeHTML(str) {
    const txt = document.createElement("textarea");
    txt.innerHTML = str;
    return txt.value;
}

function send_msg() {
    var msg = document.getElementById('txtInput').value;
    var msg = msg;
    len_count = $("#txtInput").val().length
    if (typeof emp_no === 'undefined') {
        // Assign a default value if empNumber is undefined
        emp_no = 172345689;
    }
    if (len_count < 200 && (Boolean(msg.match(/[a-zA-Z0-9]+/)))) {
        if (len_count < 200) {
            $("#txtInput_stag").attr('disabled', 'disabled');
        } else {
            if (len_count > 200) {
                $("#staging").append("<div class='d-flex class particular-chat-wrapper'><h4 class='chat user1'>Chat message is too large </h4></div>")
            } else if (len_count == 0) {}
            $('#staging').scrollTop($('#staging')[0].scrollHeight);
        }
    }
    if (msg != '' && len_count < 200 && (Boolean(msg.match(/[^\s]/)))) {
        $("#staging").append(`
        <div class='d-flex class particular-chat-wrapper'>
            <h4 class='chat user2'>${escapeHTML(msg)}</h4>
            <div class='user2-name-letter name-letter'>
                <img src='${base_url}assets/bot/img/avatar.svg' alt='user'>
            </div>
        </div>
    `);

        // Clear input field
        $('#txtInput').val("");

        // Add typing indicator bubble

        // Remove any previous error or processing states
        $('#rm_lang').addClass('hidden');
        var typingBubble = $("<div class='chat-bubble bot-bubble typing-indicator'>.</div>");
        $('#staging').append(typingBubble);
        scrollToBottom();
        // Scroll to the bottom to display new messages
        $('#staging').scrollTop($('#staging')[0].scrollHeight);
        let preferredLanguage = sessionStorage.getItem('preferredLanguage') || 'eng_Latn';

        $.ajax({
            type: "POST",
            contentType: "application/x-www-form-urlencoded; charset=UTF-8",
            url: "http://" + ip + "/bot_msg_llmbot",
            data: { msg: msg, type: 'prod', emp_no: emp_no, preferredLanguage: preferredLanguage },
            success: function(result) {
                $("#txtInput").removeAttr('disabled');
                var txtInputStag = document.getElementById('txtInput');
                txtInputStag.disabled = false;
                txtInputStag.placeholder = "Type a message...";
                txtInputStag.focus()
                typingBubble.remove();
                // Animate the result word by word
                animateTextInH4(result);
                scrollToBottom()

                $('#staging').scrollTop($('#staging')[0].scrollHeight);

            }
        });
    }
    scrollToBottom()
}

function button_intent(msg) {
    var msg = msg

    if (typeof emp_no === 'undefined') {
        // Assign a default value if empNumber is undefined
        emp_no = 451603;
    }
    emp_name = "rahul";
    $('#rm_prod').remove()
    $("#staging").append(`
        <div class='d-flex class particular-chat-wrapper'>
            <h4 class='chat user2'>${msg}</h4>
            <div class='user2-name-letter name-letter'>
                <img src='${base_url}assets/bot/img/avatar.svg' alt='user'>
            </div>
        </div>
    `);

    // Clear input field
    $('#txtInput').val("");

    // Add typing indicator bubble

    // Remove any previous error or processing states
    $('#rm_lang').addClass('hidden');
    $('#rm_stag').remove();
    var typingBubble = $("<div class='chat-bubble bot-bubble typing-indicator'>.</div>");
    $('#staging').append(typingBubble);
    scrollToBottom();
    // Scroll to the bottom to display new messages
    $('#staging').scrollTop($('#staging')[0].scrollHeight);
    let preferredLanguage = sessionStorage.getItem('preferredLanguage') || 'eng_Latn';

    $.ajax({
        type: "POST",
        contentType: "application/x-www-form-urlencoded; charset=UTF-8",
        url: "http://" + ip + "/bot_msg_llmbot",
        data: { msg: msg, type: 'prod', emp_no: emp_no, preferredLanguage: preferredLanguage },
        success: function(result) {

            $("#txtInput").removeAttr('disabled');
            var txtInputStag = document.getElementById('txtInput');
            txtInputStag.disabled = false;
            txtInputStag.placeholder = "Type a message...";
            txtInputStag.focus()
            typingBubble.remove();
            // Animate the result word by word
            animateTextInH4(result);
            scrollToBottom()

            $('#staging').scrollTop($('#staging')[0].scrollHeight);

        }
    });
}


function check_data_stag() {
    $('#press_enter_stag').click();
    $('.send').addClass('hidden');

    // Show stop button by removing the 'hidden' class and adding 'visible'
    $('.stop').removeClass('hidden').addClass('visible');

    // Trigger the click event on the #press_enter_stag
    $('#press_enter_stag').click();
}

function stopSending() {
    // Send a request to stop the process
    const data = {
        user_id: emp_no,

    };
    $.ajax({
        url: "http://" + ip + "/stop_process",
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function(response) {
            console.log(response.message);
            scrollToBottom()
        },
        error: function(xhr, status, error) {
            console.error("Error stopping process:", error);
        }
    });


}
$(document).ready(function() {
    $('#txtInput').keypress(function(e) {
        if (e.keyCode == 13) {
            $('.send').addClass('hidden');

            // Show stop button by removing the 'hidden' class and adding 'visible'
            $('.stop').removeClass('hidden').addClass('visible');

            // Trigger the click event on the #press_enter_stag
            $('#press_enter_stag').click();
            scrollToBottom()

        }
    });
});

function clearChat() {
    var chatContainer = document.getElementById('staging');

    if (chatContainer) {
        // Select all child elements except the heading
        var childrenToRemove = chatContainer.querySelectorAll(':scope > :not(.chat-board__chatting-area__heading):not(#rm_lang)');

        // Loop through the selected elements and remove them
        childrenToRemove.forEach(child => {
            child.remove();
        });
    }
    $('#rm_lang').removeClass('hidden');
}


function submitFeedback(action, conversationId) {
    const feedbackData = {
        action: action,
        conversation_id: conversationId,
        emp_no: emp_no
    };

    const feedbackContainer = document.querySelector(`#sendfeedback-${conversationId}`);

    // Determine the icons based on the container
    const likeIcon = feedbackContainer.querySelector('.like-icon');
    const dislikeIcon = feedbackContainer.querySelector('.dislike-icon');

    // If user clicks "comment" or "dislike", open the feedback form
    if (action === 'comment' || action === 'dislike') {
        $.ajax({
            url: "http://" + ip + "/submit_feedback",
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(feedbackData),
            success: function(response) {
                if (response.action === 'like') {
                    likeIcon.style.color = '#24568f';
                    dislikeIcon.style.color = '#aaa';
                } else if (response.action === 'dislike') {
                    dislikeIcon.style.color = '#24568f';
                    likeIcon.style.color = '#aaa';
                }
                scrollToBottom();
            },
            error: function(xhr, status, error) {
                console.error("Error during feedback submission:", status, error);
            }
        });
        $('.particular-chat-wrapper-user2').css('display', 'block');
        $('.chat_op_buttons').addClass('hidden')
        likeIcon.classList.add('hidden');
        dislikeIcon.classList.add('hidden');

        // Check if a feedback form already exists, remove it
        if (feedbackContainer.querySelector('.feedback-form')) {
            feedbackContainer.querySelector('.feedback-form').remove();
        }

        // Create a textarea for feedback
        const textarea = document.createElement('textarea');
        textarea.classList.add('feedback-textarea');
        textarea.placeholder = 'Add your query here to raise ticket...';
        textarea.rows = 2;
        textarea.style.width = '100%';

        // Create a submit button
        const submitButton = document.createElement('button');
        submitButton.classList.add('feedback-submit-btn');
        submitButton.textContent = 'Submit';
        submitButton.style.backgroundColor = 'blue';

        // Create a cancel button
        const cancelButton = document.createElement('button');
        cancelButton.classList.add('feedback-cancel-btn');
        cancelButton.textContent = 'Cancel';
        submitButton.addEventListener('click', () => {
            const feedbackText = textarea.value.trim();
            const wordCount = feedbackText.split(/\s+/).filter(word => word.length > 0).length;

            let errorMessage = document.getElementById('wordCountError');

            textarea.addEventListener('input', () => {
                if (errorMessage) {
                    errorMessage.remove();
                    errorMessage = null;
                }
            });

            if (wordCount < 10) {
                if (!errorMessage) {
                    errorMessage = document.createElement('p');
                    errorMessage.id = 'wordCountError';
                    errorMessage.style.color = 'red';
                    errorMessage.style.fontSize = '10px';
                    errorMessage.style.marginBottom = '5px';
                    errorMessage.textContent = 'Please enter at least 10 words before submitting.';
                    const feedbackForm = submitButton.parentNode; // Get the container of buttons
                    if (feedbackForm) {
                        feedbackForm.insertBefore(errorMessage, submitButton); // Insert before Submit button
                    }
                } else {
                    errorMessage.textContent = 'Please enter at least 10 words before submitting.';
                }
                return;
            } else {
                if (errorMessage) {
                    errorMessage.remove();
                    errorMessage = null;
                }
            }
            if (feedbackText) {
                feedbackData.text = feedbackText;
                $.ajax({
                    url: "http://" + ip + "/submit_feedback",
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify(feedbackData),
                    success: function(response) {
                        if (document.querySelector('.feedback-form')) {
                            document.querySelector('.feedback-form').remove();
                        }

                        likeIcon.classList.remove('hidden');
                        dislikeIcon.classList.remove('hidden');
                        dislikeIcon.style.color = '#24568f';
                        likeIcon.style.color = '#aaa';

                        $('.particular-chat-wrapper-user2').css('display', 'flex');
                        $('.chat_op_buttons').removeClass('hidden')
                        scrollToBottom();
                    },
                    error: function(xhr, status, error) {
                        console.error('Error during feedback submission:', status, error);
                    }
                });
            }
        });

        cancelButton.addEventListener('click', () => {
            if (document.querySelector('.feedback-form')) {
                document.querySelector('.feedback-form').remove();
            }
            likeIcon.classList.remove('hidden');
            dislikeIcon.classList.remove('hidden');
            $('.particular-chat-wrapper-user2').css('display', 'flex');
            $('.chat_op_buttons').removeClass('hidden')
            scrollToBottom();
        });

        // Append textarea and buttons
        const formContainer = document.createElement('div');
        formContainer.classList.add('feedback-form');
        formContainer.appendChild(textarea);
        formContainer.appendChild(submitButton);
        formContainer.appendChild(cancelButton);
        feedbackContainer.parentNode.append(formContainer); // Append formContainer after feedbackContainer

    } else {
        // Normal like/dislike behavior without opening feedback form
        $.ajax({
            url: "http://" + ip + "/submit_feedback",
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(feedbackData),
            success: function(response) {
                if (response.action === 'like') {
                    likeIcon.style.color = '#24568f';
                    dislikeIcon.style.color = '#aaa';
                } else if (response.action === 'dislike') {
                    dislikeIcon.style.color = '#24568f';
                    likeIcon.style.color = '#aaa';
                }
                scrollToBottom();
            },
            error: function(xhr, status, error) {
                console.error("Error during feedback submission:", status, error);
            }
        });
    }
}

function removeFeedbackButtons(conversationId) {
    // Find the feedback section for this specific conversation
    const feedbackWrapper = document.getElementById(`sendfeedback-${conversationId}`);
    if (feedbackWrapper) {
        feedbackWrapper.remove();
    }

}




function addChatBubble(message, type) {
    $('#staging').append(`
        <div class="chat-bubble ${type}">
            <span>${message}</span>
        </div>
    `);
    scrollToBottom();
}

function addTypingIndicator() {
    var typingBubble = $('<div class="chat-bubble bot-bubble typing-indicator">...</div>');
    $('#staging').append(typingBubble);
    scrollToBottom();
    return typingBubble;
}

function removeTypingIndicator(typingBubble) {
    typingBubble.remove();
}


// Main function to initialize recording logic
let micInitialized = false;
let mediaRecorder;
let isRecording = false;
let audioChunks = [];

function initMicRecorder() {
    if (micInitialized) return;
    micInitialized = true;

    const micIcon = document.getElementById('micIcon');
    const inputImgDiv = document.querySelector('.input_img');
    const actionsDiv = document.getElementById('recordingActions');
    const sendBtn = document.getElementById('sendRecording');
    const cancelBtn = document.getElementById('cancelRecording');
    const inputSec = document.querySelector('.input-sec');
    const sendDiv = document.querySelector('.send');
    const stopDiv = document.querySelector('.stop');

    let shouldSend = false; // flag to check if audio should be sent

    inputImgDiv.addEventListener('click', () => {
        if (!isRecording) {
            startRecording();
        }
    });

    sendBtn.addEventListener('click', () => {
        shouldSend = true;
        stopRecording();
    });

    cancelBtn.addEventListener('click', () => {
        shouldSend = false;
        stopRecording();
    });

    async function startRecording() {
        try {
            // Hide UI and add wave animation
            inputSec.classList.add('hidden');
            sendDiv.classList.add('hidden');
            stopDiv.classList.add('hidden');
            createAudioBars('wave');
            const waveContainer = document.getElementById('wave');
            waveContainer.style.visibility = 'visible';
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = () => {
                actionsDiv.style.display = 'none';

                // Restore UI and remove wave effect
                inputSec.classList.remove('hidden');
                sendDiv.classList.remove('hidden');
                inputImgDiv.classList.remove('wave');

                if (!audioChunks.length || !shouldSend) return;

                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                const formData = new FormData();
                formData.append('audio', audioBlob);
                formData.append('emp_no', emp_no);
                formData.append('preferredLanguage', sessionStorage.getItem('preferredLanguage') || 'eng_Latn')
                    // Replace with actual value
                $.ajax({
                    url: "http://" + ip + "/transcribe",
                    method: "POST",
                    data: formData,
                    processData: false,
                    contentType: false,
                    success: function(response) {
                        console.log("Audio uploaded successfully", response);
                        const transcribedText = response.text || response.message || ""; // adjust based on actual key

                        if (transcribedText.trim()) {
                            $('#txtInput').val(transcribedText);
                            send_msg();
                        } else {
                            console.error("No valid transcription found.");
                        }
                    },
                    error: function(error) {
                        console.error("Error uploading audio", error);
                    }
                });

                inputImgDiv.classList.remove('recording');
                isRecording = false;
            };

            mediaRecorder.start();
            isRecording = true;
            inputImgDiv.classList.add('recording');
            actionsDiv.style.display = 'flex';

        } catch (error) {
            console.error("Microphone access denied or error:", error);
        }
    }

    function stopRecording() {
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
            isRecording = false;
        }
    }
}