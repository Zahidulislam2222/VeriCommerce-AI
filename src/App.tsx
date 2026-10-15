import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import Lenis from 'lenis';
import { AnimatePresence, motion, useScroll, useSpring, useTransform } from 'motion/react';
import { useMotionPreference } from './useMotionPreference';
import { ArrowDown, ArrowRight, Asterisk, Check, ChevronDown, FileText, Pause, Play, Plus, ScanLine, ShieldCheck, Sparkles } from 'lucide-react';
import { appConfig } from './config';
import { content, demo, products, sources } from './content';
import { Arrow, Brand, Reveal } from './components';
import Workspace from './Workspace';
import coreCopy from './data/core.json';
import PublicPage from './PublicPages';
import { isPublicPath } from './public-routes';
import { PublicFooter, PublicHeader } from './PublicNavigation';

const CoreWorkspace = lazy(() => import('./CoreWorkspace'));

function useRoute() {
  const [path, setPath] = useState(window.location.pathname);
  useEffect(() => { const update = () => setPath(window.location.pathname); window.addEventListener('popstate', update); return () => window.removeEventListener('popstate', update); }, []);
  function navigate(pathname: string) { window.history.pushState({}, '', pathname); setPath(window.location.pathname); window.scrollTo({ top: 0, behavior: 'instant' }); }
  return { path, navigate };
}

export default function App() {
  const { path, navigate } = useRoute();
  useEffect(() => { const frame = window.requestAnimationFrame(() => document.querySelector<HTMLElement>('main h1')?.focus({ preventScroll: true })); return () => window.cancelAnimationFrame(frame); }, [path]);
  if (path === appConfig.route.core) return <Suspense fallback={<main className="workspace-main"><h1>{coreCopy.loading}</h1></main>}><CoreWorkspace onBack={() => navigate(appConfig.route.home)} /></Suspense>;
  if (isPublicPath(path) || ![appConfig.route.home, appConfig.route.workspace].includes(path)) return <PublicPage path={path} />;
  return path === appConfig.route.workspace
    ? <Workspace onBack={() => navigate(appConfig.route.home)} />
    : <Landing onCore={() => navigate(appConfig.route.core)} onOpen={() => navigate(appConfig.route.workspace)} onOpenLab={() => navigate(`${appConfig.route.workspace}#lab`)} />;
}

function Landing({ onOpen, onOpenLab, onCore }: { onOpen: () => void; onOpenLab: () => void; onCore: () => void }) {
  const reduced = useMotionPreference();
  const [videoPaused, setVideoPaused] = useState(false);
  const [videoFailed, setVideoFailed] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const heroRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll();
  const progress = useSpring(scrollYProgress, { stiffness: appConfig.motion.springStiffness, damping: appConfig.motion.springDamping });
  const { scrollYProgress: heroProgress } = useScroll({ target: heroRef, offset: ['start start', 'end start'] });
  const imageY = useTransform(heroProgress, [0, 1], [0, 70]);
  useEffect(() => {
    if (reduced) return;
    const lenis = new Lenis({ autoRaf: true, duration: appConfig.motion.smoothScrollSeconds, anchors: true, smoothWheel: true });
    return () => lenis.destroy();
  }, [reduced]);
  useEffect(() => {
    const video = videoRef.current;
    const hero = heroRef.current;
    if (!video || !hero || reduced) return;
    let inView = true;
    const syncPlayback = () => {
      if (!inView || document.hidden || videoPaused) video.pause();
      else void video.play().catch(() => setVideoFailed(true));
    };
    const observer = new IntersectionObserver(([entry]) => { inView = entry.isIntersecting; syncPlayback(); });
    observer.observe(hero);
    document.addEventListener('visibilitychange', syncPlayback);
    syncPlayback();
    return () => { observer.disconnect(); document.removeEventListener('visibilitychange', syncPlayback); };
  }, [reduced, videoPaused, videoFailed]);
  function toggleVideo() {
    const next = !videoPaused;
    setVideoPaused(next);
    if (next) videoRef.current?.pause(); else void videoRef.current?.play().catch(() => setVideoFailed(true));
  }
  return <>
    <a className="skip-link" href="#main">{content.labels.app01}</a>
    <motion.div className="scroll-progress" style={{ scaleX: reduced ? scrollYProgress : progress }} />
    <PublicHeader path="/" onOpenWorkspace={onCore} />
    <main id="main">
      <section className="hero" ref={heroRef}>
        <div className="hero-copy">
          <Reveal><p className="eyebrow"><span className="status-dot" />{content.hero.eyebrow}</p></Reveal>
          <h1 tabIndex={-1}>{content.hero.lines.map((line, i) => <span className="hero-line" key={line}><motion.span initial={reduced ? false : { y: '110%' }} animate={{ y: 0 }} transition={{ duration: reduced ? 0 : appConfig.motion.heroSeconds, delay: i * appConfig.motion.staggerSeconds, ease: appConfig.motion.ease }} className={i === 2 ? 'serif-italic' : ''}>{line}</motion.span></span>)}</h1>
          <Reveal delay={appConfig.motion.introDelay}><p className="hero-description">{content.hero.description}</p><div className="hero-actions"><button className="button" onClick={onOpen}>{content.hero.primary}<Arrow /></button><a className="text-link" href="#platform">{content.hero.secondary}<ArrowDown size={15} aria-hidden="true" /></a></div></Reveal>
          <Reveal delay={appConfig.motion.footnoteDelay} className="hero-footnote"><span className="mini-mark">v.</span><p>{content.hero.footnote}</p></Reveal>
        </div>
        <div className="hero-visual">
          <motion.div className="hero-media" style={reduced ? undefined : { y: imageY }}>
            <img className="hero-image" src={appConfig.media.hero} width="1536" height="1024" alt={products[0].alt} fetchPriority="high" />
            {appConfig.assetVideoEnabled && !reduced && !videoFailed && <video ref={videoRef} className="hero-video" muted autoPlay loop playsInline preload="none" poster={appConfig.media.hero} onError={() => setVideoFailed(true)}><source src={appConfig.media.heroVideo} type="video/mp4" /></video>}
          </motion.div>
          <div className="hero-visual-top"><span>{content.hero.caption}</span><span className="crosshair">+</span></div>
          <div className="hero-product-label"><span className="eyebrow">{content.hero.product}</span><span>{content.hero.category}</span></div>
          <motion.div className="evidence-float" initial={reduced ? false : { opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: reduced ? 0 : appConfig.motion.floatDelay, duration: appConfig.motion.revealSeconds }}>
            <span className="evidence-float-icon"><Check size={16} aria-hidden="true" /></span><div><span className="micro-label">{content.hero.sourceLabel}</span><strong>{content.hero.claim}</strong><span className="evidence-float-source"><FileText size={12} aria-hidden="true" />{content.hero.source}</span></div><span className="connecting-line" />
          </motion.div>
          {appConfig.assetVideoEnabled && !reduced && !videoFailed && <button className="video-control" aria-label={videoPaused ? content.ui.play : content.ui.pause} onClick={toggleVideo}>{videoPaused ? <Play size={14} aria-hidden="true" /> : <Pause size={14} aria-hidden="true" />}</button>}
          <span className="hero-image-note">{content.labels.app02}</span>
        </div>
      </section>
      <div className="principles-strip">{content.principles.map((principle, i) => <span key={principle}><span className="principle-number">0{i + 1}</span>{principle}<Plus size={14} strokeWidth={1} aria-hidden="true" /></span>)}</div>
      <section className="platform section-space" id="platform">
        <div className="section-intro"><Reveal><p className="eyebrow">{content.intro.eyebrow}</p><h2>{content.intro.title}<br /><em>{content.intro.emphasis}</em></h2></Reveal><Reveal className="intro-copy"><p>{content.intro.description}</p><a className="text-link" href="#studio">{content.intro.link}<Arrow /></a></Reveal></div>
        <div className="feature-grid">{content.features.map((feature, i) => <Reveal key={feature.number} className="feature" delay={i * appConfig.motion.staggerSeconds}><div className="feature-top"><span className="feature-number">{feature.number}</span>{feature.icon === 'scan' ? <ScanLine aria-hidden="true" /> : feature.icon === 'sparkles' ? <Sparkles aria-hidden="true" /> : <ShieldCheck aria-hidden="true" />}</div><p className="eyebrow">{feature.label}</p><h3>{feature.title}</h3><p>{feature.description}</p></Reveal>)}</div>
      </section>
      <section className="product-story">
        <Reveal className="story-image-wrap"><img src={products[1].image} width="1024" height="1536" alt={products[1].alt} loading="lazy" /><div className="story-image-caption"><span>{content.labels.app03}</span><span>{products[1].name}</span></div></Reveal>
        <div className="story-copy"><Reveal><p className="eyebrow">{content.labels.app04}</p><h2>{content.labels.app05}<br />{content.labels.app06}<br /><em>{content.labels.app07}</em></h2><p>{content.labels.app08}</p><a className="text-link" href="#studio">{content.labels.app09}<Arrow /></a></Reveal><Reveal className="source-note"><span className="source-note-number">↗</span><div><p className="micro-label">{content.labels.app10}</p><p>{content.previewUI.detail}<br /><span>{content.labels.app11}</span></p></div></Reveal></div>
      </section>
      <StudioPreview onOpen={onOpen} />
      <section className="process section-space" id="process"><Reveal><p className="eyebrow">{content.process.eyebrow}</p><h2>{content.process.title}<br /><em>{content.process.emphasis}</em></h2></Reveal><div className="process-grid">{content.process.steps.map((step, i) => <Reveal className="process-step" key={step.number} delay={i * appConfig.motion.staggerSeconds}><div className="process-top"><span>{step.number}</span>{i < content.process.steps.length - 1 && <ArrowRight size={20} strokeWidth={1} aria-hidden="true" />}</div><p className="eyebrow">{step.label}</p><h3>{step.title}</h3><p>{step.description}</p></Reveal>)}</div></section>
      <section className="lab-section" id="lab"><div className="lab-copy"><Reveal><p className="eyebrow">{content.lab.eyebrow}</p><h2>{content.lab.title}<br /><em>{content.lab.emphasis}</em></h2><p>{content.lab.description}</p><button className="button button-light" onClick={onOpenLab}>{content.lab.button}<Arrow /></button></Reveal><span className="lab-status"><span className="status-dot" />{content.labels.app12}</span></div><div className="lab-visual"><div className="orbital-graphic" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orbit orbit-three" /><div className="orb-core"><span>v.</span></div><span className="orbit-point orbit-point-one" /><span className="orbit-point orbit-point-two" /><span className="orbit-label orbit-label-one">EVIDENCE</span><span className="orbit-label orbit-label-two">EVALUATION</span><span className="orbit-label orbit-label-three">INTELLIGENCE</span></div>{content.lab.items.map((item) => <div className="lab-item" key={item.number}><span>{item.number}</span><div><h3>{item.title}</h3><p>{item.detail}</p></div><Plus size={15} aria-hidden="true" /></div>)}<p className="lab-caption">{content.lab.caption}</p></div></section>
      <section className="faq-section section-space"><Reveal><p className="eyebrow">{content.faq.eyebrow}</p><h2>{content.labels.app13}<br /><em>understanding.</em></h2></Reveal><div className="faq-list">{content.faq.items.map((item, index) => <FAQItem item={item} index={index} key={item.question} />)}</div></section>
      <section className="closing-section"><div className="closing-image"><img src={products[2].image} width="1024" height="1536" alt={products[2].alt} loading="lazy" /></div><div className="closing-copy"><Reveal><p className="eyebrow">{content.cta.eyebrow}</p><h2>{content.cta.title}<br /><em>{content.cta.emphasis}</em></h2><p>{content.cta.description}</p><button className="button" onClick={onOpen}>{content.cta.button}<Arrow /></button></Reveal></div><div className="closing-monogram" aria-hidden="true">v.</div></section>
    </main>
    <PublicFooter />
  </>;
}

function StudioPreview({ onOpen }: { onOpen: () => void }) {
  const [active, setActive] = useState('catalog');
  const [activeClaim, setActiveClaim] = useState(0);
  const product = products[0];
  const claim = product.claims[activeClaim];
  const source = sources.find((source) => source.id === claim.sourceId)!;
  return <section className="studio section-space" id="studio"><div className="section-intro"><Reveal><p className="eyebrow">{content.studio.eyebrow}</p><h2>{content.studio.title}<br /><em>{content.studio.emphasis}</em></h2></Reveal><Reveal className="intro-copy"><p>{content.studio.description}</p></Reveal></div><div className="studio-controls"><div className="segmented-control" aria-label="Collection workspace view">{content.studio.tabs.map((tab) => <button key={tab.id} onClick={() => setActive(tab.id)} aria-pressed={active === tab.id} className={active === tab.id ? 'active' : ''}>{tab.label}{active === tab.id && <span className="tab-dot" />}</button>)}</div><button className="text-link" onClick={onOpen}>{content.studio.open}<Arrow /></button></div>
    <Reveal className="studio-window"><div className="window-chrome"><div className="window-dots"><i /><i /><i /></div><span>VeriCommerce / {demo.store}</span><span className="sample-badge">{content.labels.app16}</span></div><div className="window-layout"><aside className="preview-sidebar" aria-hidden="true"><Brand /><div><span className={active === 'catalog' ? 'active' : ''}><ScanLine size={16} />Collection</span><span className={active === 'evidence' ? 'active' : ''}><FileText size={16} />Evidence</span><span className={active === 'drafts' ? 'active' : ''}><Sparkles size={16} />{content.labels.app17}</span></div><p>{content.labels.app18}</p></aside><div className="preview-main"><div className="preview-heading"><div><p className="micro-label">{content.previewUI.eyebrows[active as keyof typeof content.previewUI.eyebrows]}</p><h3>{content.previewUI.headings[active as keyof typeof content.previewUI.headings]}</h3></div><span className="preview-flower" aria-hidden="true"><Asterisk size={34} strokeWidth={1} /></span></div>
      {active === 'catalog' && <div className="preview-products">{products.map((item) => <button className="preview-product" key={item.id} onClick={onOpen}><div className={`preview-product-image ${item.color}`}><img src={item.image} alt="" loading="lazy" /></div><div className="preview-product-copy"><span className="micro-label">{item.category}</span><strong>{item.name}</strong><span>{item.subtitle}</span><span className="connected-status"><span className="status-dot" />{item.claims.length} connected details</span></div><Arrow size={16} /></button>)}</div>}
      {active === 'evidence' && <div className="preview-evidence"><div className="claim-list">{product.claims.map((item, i) => <button className={`claim-row ${activeClaim === i ? 'active' : ''}`} key={item.label} onClick={() => setActiveClaim(i)}><span className="claim-check"><Check size={13} aria-hidden="true" /></span><span><small>{item.label}</small><strong>{item.value}</strong></span><Arrow size={16} /></button>)}</div><div className="passage-card"><div className="passage-header"><FileText size={20} aria-hidden="true" /><span>{content.labels.app19}</span></div><p>“{claim.passage}”</p><div className="passage-footer"><span>{source.name}<br /><small>Revision {source.version} · Page {claim.page}</small></span><ShieldCheck size={18} aria-hidden="true" /></div></div></div>}
      {active === 'drafts' && <div className="preview-draft"><div className="draft-paper"><span className="eyebrow">{content.labels.app20}</span><h4>{product.name}</h4><p>{product.draft}</p><span className="connected-status"><Check size={13} aria-hidden="true" />{product.claims.length} {content.previewUI.connectedDetails}</span></div><div className="draft-review"><span className="draft-review-icon"><ShieldCheck size={27} strokeWidth={1.2} aria-hidden="true" /></span><h4>{content.labels.app21}<br />{content.labels.app22}</h4><p>{content.labels.app23}</p><button className="button button-small" onClick={onOpen}>{content.ui.review}<Arrow size={15} /></button></div></div>}
    </div></div></Reveal><p className="studio-caption">{content.studio.caption}<span>01—03 / EXPLORE THE POSSIBILITY</span></p></section>;
}

function FAQItem({ item, index }: { item: { question: string; answer: string }; index: number }) {
  const [open, setOpen] = useState(false);
  const reduced = useMotionPreference();
  return <div className={`faq-item ${open ? 'open' : ''}`}><h3><button aria-expanded={open} aria-controls={`faq-${index}`} onClick={() => setOpen(!open)}><span>{item.question}</span><ChevronDown size={19} strokeWidth={1.5} aria-hidden="true" /></button></h3><AnimatePresence initial={false}>{open && <motion.div id={`faq-${index}`} initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: reduced ? 0 : appConfig.motion.hoverSeconds }}><p>{item.answer}</p></motion.div>}</AnimatePresence></div>;
}
