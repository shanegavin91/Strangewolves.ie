const ENDPOINT='https://twe56rauf9.execute-api.eu-west-1.amazonaws.com/prod/signup';
const routeInput=document.getElementById('route');
const kicker=document.getElementById('form-kicker');
const title=document.getElementById('form-title');
const help=document.getElementById('form-help');
const submit=document.querySelector('#signup-form .submit');
const status=document.getElementById('form-status');

const routeCopy={
  beginner_waitlist:{k:'BEGINNERS WAITLIST',t:'Get on the next course list.',h:'Leave your details and we’ll contact you when the next complete beginners course is opening.',b:'Join the beginners list'},
  experienced_dropin:{k:'SOME EXPERIENCE',t:'Tell us what you’ve trained.',h:'Boxing, judo, jiu-jitsu, wrestling, kickboxing or something similar? Give us your background and we’ll point you toward the right session.',b:'Send my details'},
  experienced_mma:{k:'EXPERIENCED MMA',t:'Register before you drop in.',h:'Already comfortable in an MMA room? Drop-in is €10 on arrival. Send your details here and complete the online waiver before training.',b:'Register a drop-in'}
};
function setRoute(route){
  const copy=routeCopy[route]||routeCopy.beginner_waitlist;
  routeInput.value=route;kicker.textContent=copy.k;title.textContent=copy.t;help.textContent=copy.h;submit.textContent=copy.b;
  document.querySelectorAll('.path-card').forEach(el=>el.classList.toggle('active',el.dataset.route===route));
  status.textContent='';
}
document.querySelectorAll('.path-card').forEach(btn=>btn.addEventListener('click',()=>setRoute(btn.dataset.route)));
document.querySelectorAll('[data-route-link]').forEach(link=>link.addEventListener('click',()=>setRoute(link.dataset.routeLink)));

const form=document.getElementById('signup-form');
form.addEventListener('submit',async e=>{
  e.preventDefault();
  const fd=new FormData(form);
  if(fd.get('website')) return;
  const payload={
    name:String(fd.get('name')||'').trim(),
    email:String(fd.get('email')||'').trim(),
    phone:String(fd.get('phone')||'').trim(),
    route:String(fd.get('route')||'beginner_waitlist'),
    experience:fd.getAll('experience').join(', '),
    notes:String(fd.get('notes')||'').trim()
  };
  if(!payload.name||(!payload.email&&!payload.phone)){
    status.textContent='Please add your name and either an email address or phone number.';return;
  }
  submit.disabled=true;submit.textContent='Sending…';status.textContent='';
  try{
    const res=await fetch(ENDPOINT,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!res.ok) throw new Error('Request failed');
    const current=payload.route;
    form.reset();setRoute(current);
    status.textContent=current==='beginner_waitlist'?'You’re on the list. We’ll be in touch when the next beginners course is opening.':'Thanks — your details are in. We’ll be in touch.';
  }catch(err){
    status.textContent='That didn’t go through. Please try again or contact the club directly.';
  }finally{
    submit.disabled=false;submit.textContent=routeCopy[routeInput.value]?.b||'Send';
  }
});

const year=document.getElementById('year');if(year)year.textContent=new Date().getFullYear();