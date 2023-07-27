function showDateTime() {
    const currentDate = new Date()
    const timeElement = document.getElementById('time')
    const dateElement = document.getElementById('date')
    dateElement.textContent = currentDate.toLocaleDateString()
    timeElement.textContent = currentDate.toLocaleTimeString()
}

showDateTime()