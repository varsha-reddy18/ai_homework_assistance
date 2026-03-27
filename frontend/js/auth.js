async function signup() {
  const email = document.getElementById("email")?.value.trim();
  const password = document.getElementById("password")?.value.trim();

  if (!email || !password) {
    alert("Please enter email and password");
    return;
  }

  try {
    const res = await fetch("/signup", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (res.ok) {
      alert("Signup successful! Please login.");
      window.location.href = "/login-page";
    } else {
      alert(data.detail || "Signup failed");
    }

  } catch (error) {
    console.error("Signup error:", error);
    alert("Server error. Try again.");
  }
}


async function login() {
  const email = document.getElementById("email")?.value.trim();
  const password = document.getElementById("password")?.value.trim();

  if (!email || !password) {
    alert("Please enter email and password");
    return;
  }

  try {
    const res = await fetch("/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (res.ok) {
      alert("Login successful!");

      // ✅ Store auth data safely
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));

      window.location.href = "/dashboard";
    } else {
      alert(data.detail || "Invalid email or password");
    }

  } catch (error) {
    console.error("Login error:", error);
    alert("Server connection failed.");
  }
}