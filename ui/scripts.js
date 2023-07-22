function showDateTime(){
    const currentDate = new Date()
    const dateElement = document.getElementById('date_time');
    dateElement.textContent = currentDate
}

showDateTime()