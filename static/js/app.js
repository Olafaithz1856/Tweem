function toggleSidebar() {
    document.getElementById("sidebar").classList.toggle("collapsed");
}

function toggleTheme() {
    document.body.classList.toggle("dark");
    document.body.classList.toggle("light");
}
function switchContent(newContentHTML) {
    const content = document.querySelector(".content");

    content.classList.add("fade-out");

    setTimeout(() => {
        content.innerHTML = newContentHTML;
        content.classList.remove("fade-out");
    }, 300);
}
document.body.classList.toggle("dark");
document.body.classList.toggle("light");


function toggleMenu() {
    var sidebar = document.getElementById("sidebar");
    sidebar.classList.toggle("active");
}

function scrollToBottom() {
    const chatBox = document.getElementById("chat-box");
    if (chatBox) {
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}

function showTyping() {
    const typing = document.getElementById("typing-indicator");
    if (typing) typing.style.display = "flex";
}

function hideTyping() {
    const typing = document.getElementById("typing-indicator");
    if (typing) typing.style.display = "none";
}

// Auto scroll on load
window.onload = scrollToBottom;