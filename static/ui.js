
(function(){
  document.addEventListener('DOMContentLoaded', function(){
    const container = document.querySelector('.container');
    if(!container) return;
    const items = container.querySelectorAll('.card, .hero, .grid, form.card');
    items.forEach((el, idx) => {
      el.style.animationDelay = (idx*80) + 'ms';
      el.classList.add('fade-up');
    });
    const firstInput = document.querySelector('form.card input');
    if(firstInput) firstInput.focus();
  });

  const toggle = document.getElementById('theme-toggle');
  function applyTheme(theme){
    if(theme === 'light'){
      document.documentElement.classList.add('light');
      if(toggle) toggle.textContent = '🌙';
    } else {
      document.documentElement.classList.remove('light');
      if(toggle) toggle.textContent = '☀️';
    }
  }
  const saved = localStorage.getItem('efs-theme') || 'dark';
  applyTheme(saved);
  if(toggle){
    toggle.addEventListener('click', function(){
      const cur = document.documentElement.classList.contains('light') ? 'light' : 'dark';
      const next = cur === 'light' ? 'dark' : 'light';
      applyTheme(next);
      localStorage.setItem('efs-theme', next);
    });
  }

  function makeConfettiPiece(root, x, y, color, delay){
    const el = document.createElement('div');
    el.className = 'confetti-piece';
    el.style.left = (x*100) + '%';
    el.style.top = (y*100) + 'px';
    el.style.background = color;
    el.style.transform = 'rotate(' + (Math.random()*360) + 'deg)';
    el.style.animationDelay = (delay || 0) + 'ms';
    root.appendChild(el);
    setTimeout(()=> el.remove(), 1700 + (delay||0));
  }
  function burstConfetti(num){
    const root = document.getElementById('confetti-root');
    if(!root) return;
    const colors = ['#f97316','#f43f5e','#06b6d4','#7c3aed','#f59e0b'];
    for(let i=0;i<num;i++){
      const x = Math.random();
      const y = -50 - Math.random()*120;
      const color = colors[Math.floor(Math.random()*colors.length)];
      const delay = Math.floor(Math.random()*200);
      makeConfettiPiece(root, x, y, color, delay);
    }
  }

  if(window.location.search.indexOf('submitted=1') !== -1){
    setTimeout(()=>{
      burstConfetti(40);
      const flash = document.querySelector('.flash.success');
      if(flash){
        flash.classList.add('feedback-burst');
      }
      if(window.history && window.history.replaceState){
        const url = new URL(window.location);
        url.searchParams.delete('submitted');
        window.history.replaceState({}, '', url.pathname + url.search);
      }
    }, 500);
  }

})();
