function updateNav() {
    const btn = document.getElementById("authButton");
    const nameSpan = document.getElementById("userName");
    const createTopicBtn = document.querySelector('.nav button[data-view="create-topic"]');
    const registerBtn = document.querySelector('.nav button[data-view="register"]');
    const userName = localStorage.getItem("userName");

    if (token) {
        btn.innerText = "Logga ut";
        btn.onclick = logout;
        btn.removeAttribute("data-view");
        nameSpan.innerText = userName ? "Inloggad som " + userName : "";
        createTopicBtn.classList.remove("hidden");
        registerBtn.classList.add("hidden");
    } else {
        btn.innerText = "Logga in";
        btn.onclick = () => showView("login");
        btn.setAttribute("data-view", "login");
        nameSpan.innerText = "";
        createTopicBtn.classList.add("hidden");
        registerBtn.classList.remove("hidden");
    }
}

async function logout() {
    const ok = await confirmDialog("Är du säker på att du vill logga ut?", "Ja, logga ut");
    if (!ok) return;
    token = null;
    localStorage.removeItem("token");
    localStorage.removeItem("userName");
    localStorage.removeItem("userId");
    updateNav();
    getTopics();
    showView("home");
}

async function createUser() {
    const username = document.getElementById("registerUsername").value;
    const password = document.getElementById("registerPassword").value;
    const name = document.getElementById("registerName").value;

    const response = await fetch(apiUrl + "/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, name })
    });

    const data = await response.json();

    if (response.ok) {
        document.getElementById("registerMessage").innerText = "Konto skapat! Du kan nu logga in.";
        showView("login");
    } else {
        document.getElementById("registerMessage").innerText = data.error;
    }
}

async function login() {
    const username = document.getElementById("loginUsername").value;
    const password = document.getElementById("loginPassword").value;

    const response = await fetch(apiUrl + "/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
    });

    const data = await response.json();

    if (response.ok) {
        token = data.access_token;
        localStorage.setItem("token", token);
        if (data.user && data.user.name) {
            localStorage.setItem("userName", data.user.name);
        }
        if (data.user && data.user.id !== undefined) {
            localStorage.setItem("userId", String(data.user.id));
        }
        document.getElementById("loginMessage").innerText = "Du är inloggad!";
        updateNav();
        showView("home");
    } else {
        document.getElementById("loginMessage").innerText = data.error;
    }
}
