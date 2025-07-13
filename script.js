function generatePassword() {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()";
  let password = "";
  for (let i = 0; i < 12; i++) {
    password += chars[Math.floor(Math.random() * chars.length)];
  }
  document.getElementById("passwordOutput").innerText = password;
}

function calculate() {
  const input = document.getElementById("calcInput").value;
  try {
    const result = eval(input);
    document.getElementById("calcOutput").innerText = "ÇáäÊíÌÉ: " + result;
  } catch {
    document.getElementById("calcOutput").innerText = "ÎØÃ Ýí ÇáÕíÛÉ!";
  }
}

function showColor() {
  const color = document.getElementById("colorPicker").value;
  const output = document.getElementById("colorOutput");
  output.innerText = "Çááæä ÇáãÎÊÇÑ: " + color;
  output.style.background = color;
  output.style.color = "#fff";
}

function reverseText() {
  const input = document.getElementById("reverseInput").value;
  document.getElementById("reverseOutput").innerText = input.split("").reverse().join("");
}

function convertToBase64() {
  const input = document.getElementById("base64Input").value;
  const encoded = btoa(input);
  document.getElementById("base64Output").innerText = encoded;
}

function countWords() {
  const text = document.getElementById("wordCountInput").value.trim();
  const wordCount = text === "" ? 0 : text.split(/\s+/).length;
  document.getElementById("wordCountOutput").innerText = "ÚÏÏ ÇáßáãÇÊ: " + wordCount;
}

function updateClock() {
  const now = new Date();
  const time = now.toLocaleTimeString();
  document.getElementById("clockOutput").innerText = time;
}

setInterval(updateClock, 1000);
updateClock();
