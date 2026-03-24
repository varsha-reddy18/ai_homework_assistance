function signup(){

const email = document.getElementById("email").value
const password = document.getElementById("password").value

if(email && password){

localStorage.setItem("user", email)

alert("Signup Successful")

window.location.href="dashboard.html"

}else{

alert("Please enter email and password")

}

}


async function login(){

const email=document.getElementById("email").value
const password=document.getElementById("password").value

const res=await fetch("http://127.0.0.1:8000/login",{

method:"POST",

headers:{
"Content-Type":"application/json"
},

body:JSON.stringify({
email:email,
password:password
})

})

const data=await res.json()

// save user email as user_id
localStorage.setItem("user_id",email)

window.location.href="dashboard.html"

}