document.addEventListener("DOMContentLoaded", () => {
  const copyBtn = document.getElementById("copyBtn");
  const cloneCmd = "git clone https://github.com/jpXproject/OnyxPad.git";

  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(cloneCmd).then(() => {
        copyBtn.innerHTML = '<i class="fa-solid fa-check" style="color: #38ef7d;"></i>';
        setTimeout(() => {
          copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i>';
        }, 2000);
      });
    });
  }
});
