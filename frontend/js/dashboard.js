
  function loadUser(){
    const user = localStorage.getItem("user_id") || "Student";
    document.getElementById("userWelcome").innerText = `Hello ${user} 👋`;
  }

  function logout(){
    localStorage.clear();
    window.location.href = "login.html"; // change if needed
  }

  window.addEventListener("load", loadUser);

/* ================= SECTION SWITCH ================= */

function showSection(id){

  document.querySelectorAll(".section").forEach(sec=>{
    sec.classList.remove("active");
  });

  document.getElementById(id).classList.add("active");
}
let isLoading = false;
function updateStreak(){

  const today = new Date().toDateString();

  let lastLogin = localStorage.getItem("lastLoginDate");
  let streak = parseInt(localStorage.getItem("streak")) || 0;

  if(lastLogin === today){
    // already counted today
  }
  else{

    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);

    if(lastLogin === yesterday.toDateString()){
      streak++; // continue streak
    }else{
      streak = 1; // reset streak
    }

    localStorage.setItem("lastLoginDate", today);
    localStorage.setItem("streak", streak);
  }

  document.getElementById("streakCount").innerText = streak;
}
/* ================= CHATGPT STYLE AI ================= */
/* ================= SUBJECT CHAT SYSTEM ================= */

let selectedSubject = "";
let currentChatId = null;

/* OPEN SUBJECT */
function openSubject(subject){
  selectedSubject = subject;

  // switch to Ask AI section
  showSection("ask");

  // load subject's last chat if exists
  let savedChat = localStorage.getItem(subject + "_currentChatId");

  if(savedChat){
    currentChatId = savedChat;
  }else{
    currentChatId = "chat_" + Date.now();
    localStorage.setItem(subject + "_currentChatId", currentChatId);
    localStorage.setItem(subject + "_" + currentChatId, JSON.stringify([]));
  }

  loadChat(currentChatId);
  renderChatList();
}

/* CREATE NEW CHAT */
function createNewChat(){

  if(!selectedSubject){
    alert("Please select a subject first!");
    return;
  }

  const chatId = "chat_" + Date.now();
  currentChatId = chatId;

  localStorage.setItem(selectedSubject + "_currentChatId", chatId);
  localStorage.setItem(selectedSubject + "_" + chatId, JSON.stringify([]));

  document.getElementById("chatArea").innerHTML = `
    <div class="subject-banner">📘 ${selectedSubject} Mode Activated</div>
  `;

  renderChatList();
}

/* RENDER CHAT LIST */
function renderChatList(){

  const chatList = document.getElementById("chatList");
  chatList.innerHTML = "";

  if(!selectedSubject){
    chatList.innerHTML = `<div class="chat-empty">Select a subject first</div>`;
    return;
  }

  Object.keys(localStorage).forEach(key => {

    if(key.startsWith(selectedSubject + "_chat_")){

      const chatId = key.replace(selectedSubject + "_", "");

      chatList.innerHTML += `
        <div class="chat-item ${chatId === currentChatId ? 'active' : ''}" onclick="loadChat('${chatId}')">
          💬 ${selectedSubject} Chat ${chatId.slice(-4)}
        </div>
      `;
    }
  });
}

/* LOAD CHAT */
function loadChat(chatId){

  currentChatId = chatId;
  localStorage.setItem(selectedSubject + "_currentChatId", chatId);

  let key = selectedSubject + "_" + chatId;
  let chatData = JSON.parse(localStorage.getItem(key)) || [];

  let chatArea = document.getElementById("chatArea");
  chatArea.innerHTML = `
    <div class="subject-banner">📘 ${selectedSubject} Mode Activated</div>
  `;

  chatData.forEach(msg => {
    chatArea.innerHTML += `
      <div class="user-msg">
        <div class="msg-text">${msg.q}</div>
      </div>
      <div class="ai-msg">${msg.a}</div>
    `;
  });

  chatArea.scrollTop = chatArea.scrollHeight;
}

/* ASK AI */
async function askAI(){

  let questionInput = document.getElementById("question");
  let question = questionInput.value.trim();

  if(!question) return;

  if(!selectedSubject){
    alert("Please select a subject first!");
    return;
  }

  const chatArea = document.getElementById("chatArea");

  // show user message only once
  chatArea.innerHTML += `
    <div class="user-msg">
      <div class="msg-text">${question}</div>
    </div>
  `;

  // loading
  let loading = document.createElement("div");
  loading.className = "ai-msg";
  loading.innerHTML = "🤖 Thinking...";
  chatArea.appendChild(loading);

  chatArea.scrollTop = chatArea.scrollHeight;

  try{

    const res = await fetch("http://127.0.0.1:8000/ask",{
      method:"POST",
      headers:{
        "Content-Type":"application/json"
      },
      body: JSON.stringify({
        question: question,
        subject: selectedSubject,
        session_id: currentChatId,
        user_id: localStorage.getItem("user_id") || null
      })
    });

    const data = await res.json();

    loading.remove();

    let answer = data.answer || "⚠ No answer found";

    // format answer
    answer = answer
      .replace(/\n/g, "<br>")
      .replace(/📘/g, "📘 ")
      .replace(/✅/g, "<br><br>✅ ");

    chatArea.innerHTML += `
      <div class="ai-msg">${answer}</div>
    `;

    // save subject-wise
    let key = selectedSubject + "_" + currentChatId;
    let chatData = JSON.parse(localStorage.getItem(key)) || [];

    chatData.push({
      q: question,
      a: answer
    });

    localStorage.setItem(key, JSON.stringify(chatData));

    renderChatList();

  }catch(error){
    loading.remove();
    chatArea.innerHTML += `
      <div class="ai-msg">⚠ Error</div>
    `;
  }

  questionInput.value = "";
  chatArea.scrollTop = chatArea.scrollHeight;
}
/* ================= VOICE INPUT ================= */
let recognition
let isListening = false

function startVoice(){

recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)()
recognition.lang = "en-US"
recognition.continuous = true   // 🔥 continuous listening
recognition.interimResults = false

isListening = true

recognition.start()

recognition.onresult = function(e){

const transcript = e.results[e.results.length - 1][0].transcript

document.getElementById("question").value = transcript

askAI()
}

recognition.onerror = function(){
stopVoice()
}

recognition.onend = function(){
if(isListening){
recognition.start()  // 🔥 keep listening
}
}
}
/* ================= IMAGE UPLOAD (OCR + AI) ================= */
async function uploadImage(){

const fileInput = document.getElementById("imageInput")
const chat = document.getElementById("chatArea")
const questionInput = document.getElementById("question")

const file = fileInput.files[0]
if(!file) return

chat.innerHTML += `<div class="user-msg">📷 Image uploaded</div>`

const loadingDiv = document.createElement("div")
loadingDiv.className = "ai-msg"
loadingDiv.innerText = "🤖 Processing image..."
chat.appendChild(loadingDiv)

try{

const formData = new FormData()
formData.append("file", file)
formData.append("question", questionInput.value || "explain")

const res = await fetch("http://127.0.0.1:8000/ask-from-image",{
method:"POST",
body: formData
})

const data = await res.json()

loadingDiv.remove()

if(data.extracted_text){
chat.innerHTML += `<div class="ai-msg">📄 ${data.extracted_text}</div>`
}

chat.innerHTML += `<div class="ai-msg">🤖 ${data.answer}</div>`

}catch{
loadingDiv.remove()
chat.innerHTML += `<div class="ai-msg">⚠ Error</div>`
}

chat.scrollTop = chat.scrollHeight
fileInput.value = ""
}async function loadChatHistory(){

const user_id = localStorage.getItem("user_id")
if(!user_id) return

const res = await fetch(`http://127.0.0.1:8000/chat-history/${user_id}`)
const data = await res.json()

const chat = document.getElementById("chatArea")
chat.innerHTML = ""

data.forEach(msg=>{

// USER MESSAGE (RIGHT)
chat.innerHTML += `
<div class="chat-row user">
  <div class="chat-bubble user-bubble">
    ${msg.question}
  </div>
</div>
`

// AI MESSAGE (LEFT)
chat.innerHTML += `
<div class="chat-row ai">
  <div class="chat-bubble ai-bubble">
    ${msg.answer}
  </div>
</div>
`

})

chat.scrollTop = chat.scrollHeight
}
let voiceEnabled = true   // 🔥 toggle
let currentSpeech = null

function speakText(text){

if(!voiceEnabled) return

// Stop previous speech
if(currentSpeech){
window.speechSynthesis.cancel()
}

const speech = new SpeechSynthesisUtterance(text)
speech.lang = "en-US"
speech.rate = 1
speech.pitch = 1

currentSpeech = speech

window.speechSynthesis.speak(speech)
}

/* ================= REST OF YOUR CODE (UNCHANGED) ================= */

/* planner, quiz, puzzle, grammar etc remain same */
/* ================= PLANNER ================= */

function savePlanner(){

  const name = document.getElementById("studentName").value;
  const date = document.getElementById("date").value;

  const times = document.querySelectorAll(".time-box input");
  const tasks = document.querySelectorAll(".task-box input");

  const taskList = document.getElementById("taskList");

  // CLEAR OLD
  taskList.innerHTML = "";

  for(let i = 0; i < tasks.length; i++){

    let taskValue = tasks[i].value.trim();
    let timeValue = times[i].value.trim();

    if(taskValue !== ""){

      const li = document.createElement("li");

      li.innerHTML = `
        <span onclick="this.style.textDecoration='line-through'">
          ⏰ ${timeValue || "No Time"} - ${taskValue}
        </span>
        <button onclick="this.parentElement.remove()">❌</button>
      `;

      taskList.appendChild(li);
    }
  }

  alert("✅ Plan saved for " + name + " on " + date);
}

function toggleComplete(element){
  element.style.textDecoration =
    element.style.textDecoration === "line-through"
    ? "none"
    : "line-through";
}

function stopVoice(){

isListening = false

if(recognition){
recognition.stop()
}

window.speechSynthesis.cancel()
}

/* ================= QUIZ (50 QUESTIONS) ================= */

let currentQ = 0;
let score = 0;

/* ✅ YOUR 50 QUESTIONS */
const questions = [
{q:"Value of π (approx)?", options:["3.12","3.14","3.16","3.18"], answer:"3.14"},
{q:"√144?", options:["10","11","12","13"], answer:"12"},
{q:"HCF of 12 & 18?", options:["3","6","9","12"], answer:"6"},
{q:"Chemical symbol of Sodium?", options:["So","Na","S","N"], answer:"Na"},
{q:"Speed of light?", options:["3×10^8 m/s","3×10^6 m/s","3×10^5 m/s","3×10^3 m/s"], answer:"3×10^8 m/s"},

{q:"Who proposed relativity?", options:["Newton","Einstein","Bohr","Tesla"], answer:"Einstein"},
{q:"Atomic number of Carbon?", options:["4","6","8","12"], answer:"6"},
{q:"pH of neutral substance?", options:["5","6","7","8"], answer:"7"},
{q:"Largest gland in body?", options:["Heart","Liver","Kidney","Lung"], answer:"Liver"},
{q:"Unit of power?", options:["Joule","Watt","Newton","Volt"], answer:"Watt"},

{q:"(a+b)^2 formula?", options:["a²+b²","a²+2ab+b²","a²-2ab+b²","2a+b"], answer:"a²+2ab+b²"},
{q:"Area of circle?", options:["πr²","2πr","πd","r²"], answer:"πr²"},
{q:"Photosynthesis equation needs?", options:["O2","CO2","N2","H2"], answer:"CO2"},
{q:"SI unit of force?", options:["Watt","Joule","Newton","Pascal"], answer:"Newton"},
{q:"Which is not metal?", options:["Iron","Gold","Oxygen","Copper"], answer:"Oxygen"},

{q:"Longest bone?", options:["Femur","Tibia","Fibula","Humerus"], answer:"Femur"},
{q:"Resistance unit?", options:["Volt","Ampere","Ohm","Watt"], answer:"Ohm"},
{q:"Who discovered electron?", options:["Bohr","Rutherford","Thomson","Newton"], answer:"Thomson"},
{q:"Largest desert?", options:["Sahara","Thar","Gobi","Kalahari"], answer:"Sahara"},
{q:"Synonym of rapid?", options:["Slow","Fast","Weak","Late"], answer:"Fast"},

{q:"10^2?", options:["10","100","1000","10000"], answer:"100"},
{q:"Angle in straight line?", options:["90°","180°","270°","360°"], answer:"180°"},
{q:"Electric current unit?", options:["Volt","Ohm","Ampere","Watt"], answer:"Ampere"},
{q:"Cell powerhouse?", options:["Nucleus","Mitochondria","Ribosome","Golgi"], answer:"Mitochondria"},
{q:"Boiling point of water (K)?", options:["273K","373K","100K","200K"], answer:"373K"},

{q:"Who wrote Constitution of India?", options:["Nehru","Ambedkar","Gandhi","Patel"], answer:"Ambedkar"},
{q:"Largest island?", options:["Greenland","Australia","Borneo","Madagascar"], answer:"Greenland"},
{q:"Antonym of expand?", options:["Grow","Increase","Shrink","Spread"], answer:"Shrink"},
{q:"Gas used in balloons?", options:["Oxygen","Hydrogen","Helium","Nitrogen"], answer:"Helium"},
{q:"Unit of pressure?", options:["Pascal","Newton","Joule","Watt"], answer:"Pascal"},

{q:"Factor of 36?", options:["5","6","7","8"], answer:"6"},
{q:"Lens used for myopia?", options:["Convex","Concave","Plane","None"], answer:"Concave"},
{q:"DNA full form?", options:["Deoxyribo Nucleic Acid","Dynamic Acid","Double Acid","None"], answer:"Deoxyribo Nucleic Acid"},
{q:"Which vitamin from sun?", options:["A","B","C","D"], answer:"D"},
{q:"First law of motion by?", options:["Newton","Einstein","Galileo","Kepler"], answer:"Newton"},

{q:"Metal that rusts?", options:["Gold","Iron","Silver","Copper"], answer:"Iron"},
{q:"Plural of analysis?", options:["Analysises","Analyses","Analysis","Analys"], answer:"Analyses"},
{q:"World war II ended?", options:["1942","1945","1939","1950"], answer:"1945"},
{q:"Largest volcano?", options:["Mauna Loa","Etna","Fuji","Krakatoa"], answer:"Mauna Loa"},
{q:"Energy stored in food?", options:["Kinetic","Potential","Chemical","Heat"], answer:"Chemical"},

{q:"LCM of 4 & 6?", options:["10","12","14","16"], answer:"12"},
{q:"Refraction occurs in?", options:["Vacuum","Medium","Space","None"], answer:"Medium"},
{q:"Human normal temp?", options:["35°C","37°C","40°C","42°C"], answer:"37°C"},
{q:"Currency of Japan?", options:["Dollar","Yen","Euro","Won"], answer:"Yen"},
{q:"Gas for respiration?", options:["CO2","Oxygen","Nitrogen","Hydrogen"], answer:"Oxygen"},

{q:"Simple interest formula?", options:["PTR/100","P+R+T","PRT","P/T"], answer:"PTR/100"},
{q:"Sound speed faster in?", options:["Air","Water","Solid","Vacuum"], answer:"Solid"},
{q:"Largest organ?", options:["Heart","Skin","Liver","Brain"], answer:"Skin"},
{q:"Who invented telephone?", options:["Bell","Edison","Newton","Tesla"], answer:"Bell"},
{q:"Angle less than 90°?", options:["Obtuse","Right","Acute","Straight"], answer:"Acute"}
];

/* START */
function startQuiz(){
document.querySelector(".quiz-start-screen").style.display = "none";
currentQ = 0;
score = 0;
showQuestion();
}

/* SHOW */
function showQuestion(){
const q = questions[currentQ];

let html = `
<div class="quiz-card">
<h3>Q${currentQ+1}. ${q.q}</h3>
<div class="options">
`;

q.options.forEach(opt=>{
html += `<button class="option-btn" onclick="selectAnswer('${opt}')">${opt}</button>`;
});

html += `</div></div>`;

document.getElementById("quizArea").innerHTML = html;
}

/* ANSWER */
function selectAnswer(ans){

if(ans === questions[currentQ].answer){
score++;
}

currentQ++;

if(currentQ < questions.length){
showQuestion();
}else{
document.getElementById("quizArea").innerHTML = "";
document.getElementById("resultBox").innerHTML = `
<div class="result">
🎉 Your Score: ${score}/${questions.length}
<br><br>
<button class="start-btn" onclick="location.reload()">Play Again</button>
</div>
`;
}
}
/* ================= PUZZLE ================= */

const words = [
/* English */
"grammar","noun","verb","adjective","adverb",
"sentence","paragraph","poetry","prose","synonym",
"antonym","tense","voice","clause","phrase",

/* Social */
"history","culture","society","economy","government",
"democracy","constitution","citizen","rights","duties",
"geography","climate","continent","population","trade",

/* Maths */
"addition","subtraction","multiplication","division","fraction",
"decimal","percentage","ratio","equation","algebra",
"geometry","angle","triangle","circle","perimeter",

/* Science */
"experiment","hypothesis","theory","observation","research",
"matter","energy","force","motion","element",
"compound","mixture","reaction","lab","analysis",

/* Physics */
"velocity","acceleration","gravity","friction","pressure",
"work","power","energy","wave","sound",
"light","reflection","refraction","electricity","magnetism",

/* Biology */
"cell","tissue","organ","system","organism",
"photosynthesis","respiration","digestion","circulation","enzyme",
"dna","gene","evolution","species","habitat",

/* Extra mixed to reach 100 */
"ecosystem","biodiversity","atom","molecule","neutron",
"proton","electron","formula","solution","density"
];
let currentWord = "";

/* SCRAMBLE FUNCTION */
function scramble(word){
return word.split('').sort(()=>Math.random()-0.5).join('');
}

/* NEW PUZZLE */
function newPuzzle(){

currentWord = words[Math.floor(Math.random()*words.length)];

let scrambled = scramble(currentWord);

document.getElementById("scrambledWord").innerText = scrambled.toUpperCase();

document.getElementById("userAnswer").value = "";
document.getElementById("puzzleResult").innerText = "";
}

/* CHECK ANSWER */
function checkPuzzle(){

let user = document.getElementById("userAnswer").value.toLowerCase();

if(user === currentWord){
document.getElementById("puzzleResult").innerText = "✅ Correct!";
document.getElementById("puzzleResult").style.color = "green";
}else{
document.getElementById("puzzleResult").innerText = "❌ Try Again!";
document.getElementById("puzzleResult").style.color = "red";
}
}
window.addEventListener("load", function () {
  newPuzzle();
  updateStreak();
  renderChatList();
  updateDisplay();

  const savedChat = localStorage.getItem("currentChatId");

  if (savedChat) {
    loadChat(savedChat);
  }

  if (localStorage.getItem("theme") === "dark") {
    document.body.classList.add("dark-mode");
  }
});
function savePlanner(){

const name = document.getElementById("studentName").value
const date = document.getElementById("date").value

alert("✅ Plan saved for " + name + " on " + date)

}

async function checkGrammar(){

let text = document.getElementById("grammarInput").value;

if(text.trim() === ""){
document.getElementById("grammarResult").innerText = "⚠️ Please enter a sentence";
return;
}

// LOADING
document.getElementById("grammarResult").innerText = "⏳ Checking...";

try{

const res = await fetch("http://127.0.0.1:8000/grammar-check",{
method:"POST",
headers:{
"Content-Type":"application/json"
},
body: JSON.stringify({
text: text
})
});

const data = await res.json();

// SHOW RESULT
document.getElementById("grammarResult").innerHTML =
`✅ Corrected: <b>${data.corrected_text}</b>`;

}catch(error){

document.getElementById("grammarResult").innerText =
"⚠️ Error checking grammar";

}

}


function openVideo(videoId){
window.open(`https://www.youtube.com/watch?v=${videoId}`, "_blank");
}

let flashcards = [];
let currentIndex = 0;

function addFlashcard(){

const q = document.getElementById("questionInput").value;
const a = document.getElementById("answerInput").value;

if(!q || !a) return alert("Enter both question and answer");

flashcards.push({q,a});

document.getElementById("questionInput").value="";
document.getElementById("answerInput").value="";

currentIndex = flashcards.length - 1;
showCard();
updateFlashList();
}

function showCard(){

if(flashcards.length === 0){
document.getElementById("cardQuestion").innerText = "No cards yet";
document.getElementById("cardAnswer").innerText = "";
return;
}

document.getElementById("cardQuestion").innerText = flashcards[currentIndex].q;
document.getElementById("cardAnswer").innerText = flashcards[currentIndex].a;

document.getElementById("flashcard").classList.remove("flip");
}

function flipCard(){
document.getElementById("flashcard").classList.toggle("flip");
}

function nextCard(){
if(currentIndex < flashcards.length - 1){
currentIndex++;
showCard();
}
}

function prevCard(){
if(currentIndex > 0){
currentIndex--;
showCard();
}
}

function deleteCard(){

if(flashcards.length === 0) return;

flashcards.splice(currentIndex,1);

if(currentIndex > 0) currentIndex--;

showCard();
updateFlashList();
}

function updateFlashList(){

  const list = document.getElementById("flashList");
  list.innerHTML = "";

  flashcards.forEach((card, index)=>{

    const div = document.createElement("div");

    div.className = "flash-mini-card";
    div.innerText = card.q;

    // click to flip (Q → A)
    div.onclick = function(){

      if(div.classList.contains("back")){
        div.classList.remove("back");
        div.innerText = card.q;
      }else{
        div.classList.add("back");
        div.innerText = card.a;
      }

    };

    list.appendChild(div);
  });
}
let time = 1500;
let timerInterval;

function updateDisplay() {
  let min = Math.floor(time / 60);
  let sec = time % 60;
  document.getElementById("timer").innerText =
    `${min}:${sec < 10 ? "0" : ""}${sec}`;
}

function startTimer() {
  if (timerInterval) return;
  timerInterval = setInterval(() => {
    if (time > 0) {
      time--;
      updateDisplay();
    } else {
      alert("Time's up!");
      clearInterval(timerInterval);
    }
  }, 1000);
}

function pauseTimer() {
  clearInterval(timerInterval);
  timerInterval = null;
}

function resetTimer() {
  pauseTimer();
  time = 1500;
  updateDisplay();
}


function toggleDark(){
  document.body.classList.toggle("dark-mode");
}

// Load theme




let draggedItem = null;

// Drag Start
document.querySelectorAll(".drag-item").forEach(item => {
  item.addEventListener("dragstart", function () {
    draggedItem = this;
  });
});

// Allow Drop
document.querySelectorAll(".drop-box").forEach(box => {
  box.addEventListener("dragover", function (e) {
    e.preventDefault();
  });

  box.addEventListener("drop", function () {
    if (!this.querySelector(".drag-item")) {
      this.appendChild(draggedItem);
    }
  });
});

// Check Answers
function checkDragQuiz() {
  let correct = 0;

  document.querySelectorAll(".drop-box").forEach(box => {
    const item = box.querySelector(".drag-item");

    if (item && item.innerText === box.dataset.match) {
      correct++;
      box.style.background = "#c8f7c5"; // green
    } else {
      box.style.background = "#f7c5c5"; // red
    }
  });

  document.getElementById("dragResult").innerText =
    `Score: ${correct}/3`;
}



function loadGeo(type) {
    const result = document.getElementById("geoResult");
    result.innerHTML = "";

    let data = [];

    if(type === "countries"){
        data = [
            {name:"Afghanistan", capital:"Kabul"},
            {name:"India", capital:"New Delhi"},
            {name:"USA", capital:"Washington DC"},
            {name:"Japan", capital:"Tokyo"},
            {name:"France", capital:"Paris"},
            {name:"Brazil", capital:"Brasília"},
            {name:"Australia", capital:"Canberra"},
            {name:"Canada", capital:"Ottawa"},
            {name:"China", capital:"Beijing"},
            {name:"Russia", capital:"Moscow"},
            // add more as needed
        ];
    }

    if(type === "india"){
        data = [
            {name:"Andhra Pradesh", capital:"Amaravati"},
            {name:"Arunachal Pradesh", capital:"Itanagar"},
            {name:"Assam", capital:"Dispur"},
            {name:"Bihar", capital:"Patna"},
            {name:"Chhattisgarh", capital:"Raipur"},
            {name:"Goa", capital:"Panaji"},
            {name:"Gujarat", capital:"Gandhinagar"},
            {name:"Haryana", capital:"Chandigarh"},
            {name:"Himachal Pradesh", capital:"Shimla"},
            {name:"Jharkhand", capital:"Ranchi"},
            {name:"Karnataka", capital:"Bengaluru"},
            {name:"Kerala", capital:"Thiruvananthapuram"},
            {name:"Madhya Pradesh", capital:"Bhopal"},
            {name:"Maharashtra", capital:"Mumbai"},
            {name:"Manipur", capital:"Imphal"},
            {name:"Meghalaya", capital:"Shillong"},
            {name:"Mizoram", capital:"Aizawl"},
            {name:"Nagaland", capital:"Kohima"},
            {name:"Odisha", capital:"Bhubaneswar"},
            {name:"Punjab", capital:"Chandigarh"},
            {name:"Rajasthan", capital:"Jaipur"},
            {name:"Sikkim", capital:"Gangtok"},
            {name:"Tamil Nadu", capital:"Chennai"},
            {name:"Telangana", capital:"Hyderabad"},
            {name:"Tripura", capital:"Agartala"},
            {name:"Uttar Pradesh", capital:"Lucknow"},
            {name:"Uttarakhand", capital:"Dehradun"},
            {name:"West Bengal", capital:"Kolkata"},
            // add Union Territories if needed
        ];
    }

    if(type === "oceans"){
        data = [
            {name:"Pacific Ocean"},
            {name:"Atlantic Ocean"},
            {name:"Indian Ocean"},
            {name:"Arctic Ocean"},
            {name:"Southern Ocean"}
        ];
    }

    if(type === "continents"){
        data = [
            {name:"Asia"},
            {name:"Europe"},
            {name:"Africa"},
            {name:"North America"},
            {name:"South America"},
            {name:"Australia"},
            {name:"Antarctica"}
        ];
    }

    if(type === "deserts"){
        data = [
            {name:"Sahara Desert"},
            {name:"Thar Desert"},
            {name:"Gobi Desert"},
            {name:"Kalahari Desert"},
            {name:"Patagonian Desert"},
            {name:"Arabian Desert"}
        ];
    }

    if(type === "rivers"){
        data = [
            {name:"Ganga"},
            {name:"Yamuna"},
            {name:"Brahmaputra"},
            {name:"Indus"},
            {name:"Nile"},
            {name:"Amazon"},
            {name:"Yangtze"},
            {name:"Mississippi"}
        ];
    }

    if(type === "places"){
        data = [
            {name:"Taj Mahal"},
            {name:"Charminar"},
            {name:"Red Fort"},
            {name:"Gateway of India"},
            {name:"Qutub Minar"},
            {name:"Mysore Palace"},
            {name:"India Gate"},
            {name:"Meenakshi Temple"},
            {name:"Golden Temple"},
            {name:"Hawa Mahal"},
            {name:"Ajanta & Ellora Caves"}
        ];
    }

    // DISPLAY
    data.forEach(item => {
        result.innerHTML += `
            <div class="geo-item">
                <h4>${item.name}</h4>
                ${item.capital ? `<p>Capital: ${item.capital}</p>` : ""}
            </div>
        `;
    });
}
/* ================= SCIENCE DATA ================= */

const scienceData = {

  physics: [
    { name: "Gravity", info: "Force that attracts objects toward Earth" },
    { name: "Velocity", info: "Speed with direction" },
    { name: "Energy", info: "Ability to do work" },
    { name: "Force", info: "Push or pull acting on an object" },
    { name: "Electricity", info: "Flow of electric charge" }
  ],

  chemistry: [
    { name: "Atom", info: "Basic unit of matter" },
    { name: "Molecule", info: "Group of atoms bonded together" },
    { name: "Element", info: "Pure substance made of one type of atom" },
    { name: "Compound", info: "Combination of elements" },
    { name: "Reaction", info: "Process where substances change" }
  ],

  biology: [
    { name: "Cell", info: "Basic unit of life" },
    { name: "DNA", info: "Genetic material of organisms" },
    { name: "Photosynthesis", info: "Plants make food using sunlight" },
    { name: "Respiration", info: "Energy release process" },
    { name: "Organism", info: "Living being" }
  ],

  space: [
    { name: "Sun", info: "Star at center of solar system" },
    { name: "Moon", info: "Earth's natural satellite" },
    { name: "Planet", info: "Body orbiting a star" },
    { name: "Galaxy", info: "System of stars and planets" },
    { name: "Black Hole", info: "Region with strong gravity" }
  ],

  environment: [
    { name: "Ecosystem", info: "Living + non-living interaction" },
    { name: "Pollution", info: "Harmful substances in environment" },
    { name: "Climate", info: "Weather over long period" },
    { name: "Biodiversity", info: "Variety of life forms" },
    { name: "Conservation", info: "Protection of nature" }
  ],

  inventions: [
    { name: "Electric Bulb", info: "Invented by Thomas Edison" },
    { name: "Telephone", info: "Invented by Alexander Graham Bell" },
    { name: "Internet", info: "Global network system" },
    { name: "Computer", info: "Electronic computing device" },
    { name: "Airplane", info: "Invented by Wright brothers" }
  ]

};


/* ================= LOAD SCIENCE ================= */

function loadScience(type){

  const result = document.getElementById("geoResult");

  result.innerHTML = "";

  const data = scienceData[type];

  if(!data) return;

  data.forEach(item => {

    const div = document.createElement("div");
    div.className = "geo-item";

    div.innerHTML = `
      <h4>${item.name}</h4>
      <p>${item.info}</p>
    `;

    result.appendChild(div);
  });

}
function toggleSidebar(){
  const sidebar = document.getElementById("sidebar");
  const main = document.querySelector(".main");

  sidebar.classList.toggle("hidden");
  main.classList.toggle("full");

  const sidebar1 = document.getElementById("sidebar");

  sidebar1.classList.toggle("hide");

}


function toggleProfileMenu(){
  document.getElementById("profileMenu").classList.toggle("show");
}

function editProfile(){
  alert("Edit Profile");
}

function openSettings(){
  alert("Settings");
}

document.addEventListener("click", function(e){
  const menu = document.getElementById("profileMenu");
  const profile = document.querySelector(".profile-circle");

  if(!profile.contains(e.target) && !menu.contains(e.target)){
    menu.classList.remove("show");
  }
});


/* ================= GRAMMAR TOPIC DISPLAY ================= */

function openGrammarTopic(topic) {
  const display = document.getElementById("grammarTopicDisplay");

  if (topic === "tenses") {
    display.innerHTML = `
      <div class="grammar-topic-box">
        <h2 class="topic-main-title">📘 Tenses Chart</h2>

        <div class="tense-wrapper">
          <div class="tense-column present">
            <h3>Present Tenses</h3>

            <div class="tense-card-box">
              <h4>Simple Present Tense</h4>
              <p><b>Structure:</b> Subject + V1 + Object</p>
              <p><b>Example:</b> I always speak the truth.</p>
            </div>

            <div class="tense-card-box">
              <h4>Present Continuous Tense</h4>
              <p><b>Structure:</b> Subject + is/am/are + V1 + ing + Object</p>
              <p><b>Example:</b> Ali is riding a bicycle.</p>
            </div>

            <div class="tense-card-box">
              <h4>Present Perfect Tense</h4>
              <p><b>Structure:</b> Subject + has/have + V3 + Object</p>
              <p><b>Example:</b> The sun has set.</p>
            </div>

            <div class="tense-card-box">
              <h4>Present Perfect Continuous Tense</h4>
              <p><b>Structure:</b> Subject + has/have + been + V1 + ing + since/for</p>
              <p><b>Example:</b> The sun has been shining since morning.</p>
            </div>
          </div>

          <div class="tense-column past">
            <h3>Past Tenses</h3>

            <div class="tense-card-box">
              <h4>Simple Past Tense</h4>
              <p><b>Structure:</b> Subject + V2 + Object</p>
              <p><b>Example:</b> We went to the zoo yesterday.</p>
            </div>

            <div class="tense-card-box">
              <h4>Past Continuous Tense</h4>
              <p><b>Structure:</b> Subject + was/were + V1 + ing + Object</p>
              <p><b>Example:</b> He was smiling.</p>
            </div>

            <div class="tense-card-box">
              <h4>Past Perfect Tense</h4>
              <p><b>Structure:</b> Subject + had + V3 + Object</p>
              <p><b>Example:</b> They had already finished their work.</p>
            </div>

            <div class="tense-card-box">
              <h4>Past Perfect Continuous Tense</h4>
              <p><b>Structure:</b> Subject + had been + V1 + ing + since/for</p>
              <p><b>Example:</b> The carpenter had been making chairs for many days.</p>
            </div>
          </div>

          <div class="tense-column future">
            <h3>Future Tenses</h3>

            <div class="tense-card-box">
              <h4>Simple Future Tense</h4>
              <p><b>Structure:</b> Subject + will/shall + V1 + Object</p>
              <p><b>Example:</b> You will pass the examination.</p>
            </div>

            <div class="tense-card-box">
              <h4>Future Continuous Tense</h4>
              <p><b>Structure:</b> Subject + will/shall + be + V1 + ing + Object</p>
              <p><b>Example:</b> They will be visiting the zoo.</p>
            </div>

            <div class="tense-card-box">
              <h4>Future Perfect Tense</h4>
              <p><b>Structure:</b> Subject + will/shall + have + V3 + Object</p>
              <p><b>Example:</b> I shall have finished my homework.</p>
            </div>

            <div class="tense-card-box">
              <h4>Future Perfect Continuous Tense</h4>
              <p><b>Structure:</b> Subject + will/shall + have been + V1 + ing + since/for</p>
              <p><b>Example:</b> She will have been sleeping since evening.</p>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  else if (topic === "parts") {
    display.innerHTML = `
      <div class="grammar-topic-box">
        <h2 class="topic-main-title">🧩 Parts of Speech</h2>

        <div class="parts-grid">

          <div class="part-card noun">
            <h3>Noun</h3>
            <p><b>Definition:</b> A word that names a person, place, thing, or idea.</p>
            <p><b>Examples:</b> cat, John, park, happiness</p>
          </div>

          <div class="part-card pronoun">
            <h3>Pronoun</h3>
            <p><b>Definition:</b> A word that takes the place of a noun.</p>
            <p><b>Examples:</b> she, they, it</p>
          </div>

          <div class="part-card verb">
            <h3>Verb</h3>
            <p><b>Definition:</b> A word that expresses action or state of being.</p>
            <p><b>Examples:</b> runs, sings, are</p>
          </div>

          <div class="part-card adjective">
            <h3>Adjective</h3>
            <p><b>Definition:</b> A word that describes a noun.</p>
            <p><b>Examples:</b> fluffy, tall, delicious</p>
          </div>

          <div class="part-card adverb">
            <h3>Adverb</h3>
            <p><b>Definition:</b> A word that modifies a verb, adjective, or adverb.</p>
            <p><b>Examples:</b> beautifully, quickly, confidently</p>
          </div>

          <div class="part-card preposition">
            <h3>Preposition</h3>
            <p><b>Definition:</b> Shows relationship of a noun/pronoun to another word.</p>
            <p><b>Examples:</b> under, through, beside</p>
          </div>

          <div class="part-card conjunction">
            <h3>Conjunction</h3>
            <p><b>Definition:</b> Connects words, phrases, or clauses.</p>
            <p><b>Examples:</b> and, or, because</p>
          </div>

          <div class="part-card interjection">
            <h3>Interjection</h3>
            <p><b>Definition:</b> A word that expresses emotion or exclamation.</p>
            <p><b>Examples:</b> wow!, ouch!, yay!</p>
          </div>

        </div>
      </div>
    `;
  }

  else if (topic === "voice") {
    display.innerHTML = `
      <div class="grammar-topic-box">
        <h2 class="topic-main-title">🔄 Active & Passive Voice</h2>

        <div class="voice-grid">
          <div class="voice-card active-box">
            <h3>Active Voice</h3>
            <p>Tells us what a <b>person or thing does</b>.</p>
            <p>The subject performs the action on the object.</p>
            <p class="formula">Subject + Verb + Object</p>

            <h4>Examples:</h4>
            <ul>
              <li>Anna painted the house.</li>
              <li>The teacher answers the student's questions.</li>
              <li>Ali posted the video online.</li>
            </ul>
          </div>

          <div class="voice-card passive-box">
            <h3>Passive Voice</h3>
            <p>Tells us what is <b>done to someone or something</b>.</p>
            <p>The subject is being acted upon.</p>
            <p class="formula">Object + Verb + Subject</p>

            <h4>Examples:</h4>
            <ul>
              <li>The house was painted by Anna.</li>
              <li>The student's questions are answered by the teacher.</li>
              <li>The video was posted online by Ali.</li>
            </ul>
          </div>
        </div>
      </div>
    `;
  }

  else if (topic === "vocabulary") {
    display.innerHTML = `
      <div class="grammar-topic-box">
        <h2 class="topic-main-title">📚 Vocabulary Levels</h2>

        <div class="vocab-grid">
          <div class="vocab-card beginner">
            <h3>Beginner</h3>
            <ul>
              <li>keep</li><li>run</li><li>walk</li><li>wait</li><li>happy</li>
              <li>sad</li><li>afraid</li><li>tiny</li><li>cold</li><li>big</li>
            </ul>
          </div>

          <div class="vocab-card intermediate">
            <h3>Intermediate</h3>
            <ul>
              <li>hold</li><li>jog</li><li>stroll</li><li>delay</li><li>glad</li>
              <li>anxious</li><li>starving</li><li>clear</li><li>massive</li><li>simple</li>
            </ul>
          </div>

          <div class="vocab-card advanced">
            <h3>Advanced</h3>
            <ul>
              <li>retain</li><li>sprint</li><li>wander</li><li>postpone</li><li>delighted</li>
              <li>terrified</li><li>famished</li><li>enormous</li><li>intricate</li><li>effortless</li>
            </ul>
          </div>
        </div>
      </div>
    `;
  }

  else if (topic === "punctuation") {
    display.innerHTML = `
      <div class="grammar-topic-box">
        <h2 class="topic-main-title">✍️ Punctuation Marks</h2>

        <div class="punctuation-grid">

          <div class="punc-card"><h3>Period (.)</h3><p>Sophia loves playing hockey.</p></div>
          <div class="punc-card"><h3>Question Mark (?)</h3><p>Are you hungry?</p></div>
          <div class="punc-card"><h3>Comma (,)</h3><p>I like novels, stories, plays, and poems.</p></div>
          <div class="punc-card"><h3>Exclamation Mark (!)</h3><p>Wow! What a lovely scene!</p></div>
          <div class="punc-card"><h3>Colon (:)</h3><p>She likes three countries: Italy, USA, and UAE.</p></div>
          <div class="punc-card"><h3>Semicolon (;)</h3><p>I will not prefer cola; I will drink juice.</p></div>
          <div class="punc-card"><h3>Braces { }</h3><p>Choose one of three colors {red, pink, black}.</p></div>
          <div class="punc-card"><h3>Parentheses ( )</h3><p>I love to visit UK (United Kingdom).</p></div>
          <div class="punc-card"><h3>Dashes (—)</h3><p>USA—Japan is almost 13 hours long flight.</p></div>
          <div class="punc-card"><h3>Brackets [ ]</h3><p>She [Jenny] is crazy for driving a truck.</p></div>
          <div class="punc-card"><h3>Hyphen (-)</h3><p>I love ice-cream.</p></div>
          <div class="punc-card"><h3>Quotation Marks (" ")</h3><p>Ali asked, “When can I put the pen back?”</p></div>
          <div class="punc-card"><h3>Ellipsis (...)</h3><p>Julie... Julie is the girl who...</p></div>
          <div class="punc-card"><h3>Apostrophe (')</h3><p>Roger’s dog is weak.</p></div>

        </div>
      </div>
    `;
  }

  else if (topic === "sentence") {
    display.innerHTML = `
      <div class="grammar-topic-box">
        <h2 class="topic-main-title">📝 Sentence Structures</h2>

        <div class="sentence-grid">

          <div class="sentence-card simple-box">
            <h3>Simple Sentence</h3>
            <p><b>1 Independent Clause</b></p>
            <p class="example">Children played.</p>
          </div>

          <div class="sentence-card compound-box">
            <h3>Compound Sentence</h3>
            <p><b>2 Independent Clauses</b></p>
            <p class="example">Children played, and their parents chatted.</p>
          </div>

          <div class="sentence-card complex-box">
            <h3>Complex Sentence</h3>
            <p><b>1 Independent Clause + 1 or More Dependent Clauses</b></p>
            <p class="example">Children played after the rain stopped.</p>
          </div>

          <div class="sentence-card compoundcomplex-box">
            <h3>Compound-Complex Sentence</h3>
            <p><b>2 or More Independent Clauses + 1 or More Dependent Clauses</b></p>
            <p class="example">After the rain stopped, the children played, and their parents chatted.</p>
          </div>

        </div>
      </div>
    `;
  }
}