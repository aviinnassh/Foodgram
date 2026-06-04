console.log("Script loaded successfully");

const signUpButton = document.getElementById('signUp');
const signInButton = document.getElementById('signIn');
const container = document.getElementById('container');

signUpButton.addEventListener('click', () => {
    container.classList.add("right-panel-active");
});

signInButton.addEventListener('click', () => {
    container.classList.remove("right-panel-active");
});



let passwd = document.getElementById("pass")
let len = document.getElementById("len")
let cap = document.getElementById("cap")
let sml = document.getElementById("sml")
let dig = document.getElementById("dig")
let char = document.getElementById("char")

passwd.addEventListener('input', function () {
    const password = passwd.value
    len.style.color = password.length >= 8 ? 'green' : 'red'
    cap.style.color = /[A-Z]/.test(password) ? 'green' : 'red'
    sml.style.color = /[a-z]/.test(password) ? 'green' : 'red'
    dig.style.color = /\d/.test(password) ? 'green' : 'red'
    char.style.color = /[!@#$%&*]/.test(password) ? 'green' : 'red'
})
document.getElementById("registerForm").addEventListener('submit', function (event) {
    event.preventDefault();  // Prevent form submission for validation
    let pwd = passwd.value;
    let messageContainer = document.createElement('div');
    messageContainer.classList.add('alert', 'alert-warning', 'alert-dismissible', 'fade', 'show');

    if (/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@.#$!%*?&])[A-Za-z\d@.#$!%*?&]{8,}$/.test(pwd)) {
        this.submit();  // Submit form if password is valid
    } else {
        messageContainer.innerHTML = 'Please ensure your password meets all the criteria.<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>';
        // Add the message container to the form or any section on the page
        document.body.appendChild(messageContainer);
    }
});


