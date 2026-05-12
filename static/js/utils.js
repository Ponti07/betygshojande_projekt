const apiUrl = "http://127.0.0.1:3001";
let token = localStorage.getItem("token");

function showView(name) {
    document.querySelectorAll(".view").forEach(v => v.classList.add("hidden"));
    const target = document.getElementById("view-" + name);
    if (target) target.classList.remove("hidden");
    document.querySelectorAll(".nav button").forEach(b => {
        b.classList.toggle("active", b.dataset.view === name);
    });
}

function confirmDialog(message, okText = "Ja", cancelText = "Avbryt") {
    return new Promise((resolve) => {
        const modal = document.getElementById("confirmModal");
        const okBtn = document.getElementById("confirmOk");
        const cancelBtn = document.getElementById("confirmCancel");
        document.getElementById("confirmMessage").innerText = message;
        okBtn.innerText = okText;
        cancelBtn.innerText = cancelText;

        function close(result) {
            modal.classList.add("hidden");
            okBtn.onclick = null;
            cancelBtn.onclick = null;
            modal.onclick = null;
            resolve(result);
        }

        okBtn.onclick = () => close(true);
        cancelBtn.onclick = () => close(false);
        modal.onclick = (e) => { if (e.target === modal) close(false); };

        modal.classList.remove("hidden");
        okBtn.focus();
    });
}

async function openTopic(topicId, replyId = null) {
    document.getElementById("filterCategory").value = "";
    document.getElementById("filterSearch").value = "";
    showView("home");
    await getTopics();
    const topic = document.querySelector(`[data-topic-id="${topicId}"]`);
    if (!topic) return;
    if (topic.classList.contains("minimized")) {
        topic.classList.remove("minimized");
        await loadReplies(topicId);
    }
    if (replyId) {
        const reply = document.querySelector(`[data-reply-id="${replyId}"]`);
        if (reply) {
            reply.scrollIntoView({ behavior: "smooth", block: "center" });
            reply.classList.add("highlighted");
            setTimeout(() => reply.classList.remove("highlighted"), 2000);
            return;
        }
    }
    topic.scrollIntoView({ behavior: "smooth", block: "start" });
}

function currentUserId() {
    return localStorage.getItem("userId");
}

async function deleteResource(url, confirmMessage, onSuccess) {
    const ok = await confirmDialog(confirmMessage, "Ja, ta bort");
    if (!ok) return;
    const response = await fetch(apiUrl + url, {
        method: "DELETE",
        headers: { "Authorization": "Bearer " + token }
    });
    if (response.ok) {
        onSuccess();
    } else {
        const data = await response.json().catch(() => ({}));
        alert(data.error || "Något gick fel");
    }
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}
