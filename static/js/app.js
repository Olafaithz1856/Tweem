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
