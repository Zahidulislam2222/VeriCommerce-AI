import { useEffect, useState } from 'react';
import { ArrowDown, ArrowRight, Check, Copy, FileText, Mail, ShieldCheck } from 'lucide-react';
import { Arrow, Reveal } from './components';
import { PublicFooter, PublicHeader } from './PublicNavigation';
import { appConfig } from './config';
import data from './data/public-pages.json';
import './public-pages.css';

type Section = { id: string; title: string; body?: string[]; items?: string[] };
type Page = {
  path: string; kind: string; eyebrow: string; title: string; accent: string;
  description: string; sections: Section[]; note?: string; quote?: string;
  plans?: { name: string; label: string; price: string; period: string; description: string;
    features: string[]; action: string; href: string; featured: boolean }[];
  channels?: { title: string; description: string; subject: string }[];
  storage?: { name: string; type: string; purpose: string; duration: string }[];
  references?: { label: string; href: string }[];
};
const pages: Page[] = data.pages;

function emailHref(subject: string) { return `mailto:${data.contact.email}?subject=${encodeURIComponent(subject)}`; }

export default function PublicPage({ path }: { path: string }) {
  const page = pages.find((item) => item.path === path);
  const [notice, setNotice] = useState('');
  useEffect(() => {
    document.title = page ? `${page.title} — ${data.contact.name}` : `${data.labels.notFoundMeta} — ${data.contact.name}`;
    const description = document.querySelector('meta[name="description"]');
    description?.setAttribute('content', page?.description ?? data.labels.notFoundText);
  }, [page]);
  async function copyEmail() {
    try { await navigator.clipboard.writeText(data.contact.email); setNotice(data.labels.copied); }
    catch { setNotice(data.labels.copyFallback); }
  }
  function clearSample() {
    try { localStorage.removeItem(appConfig.storage.approvals); setNotice(data.labels.cleared); }
    catch { setNotice(data.labels.storageError); }
  }
  if (!page) return <>
    <a className="skip-link" href="#main">{data.labels.skip}</a><PublicHeader path={path} />
    <main id="main" className="public-page not-found"><p className="eyebrow">{data.labels.notFoundLabel}</p>
      <h1 tabIndex={-1}>{data.labels.notFoundTitle}</h1><p>{data.labels.notFoundText}</p>
      <a className="button" href="/">{data.labels.back}<Arrow /></a></main><PublicFooter />
  </>;
  const legal = ['legal', 'regional', 'cookies'].includes(page.kind);
  return <>
    <a className="skip-link" href="#main">{data.labels.skip}</a><PublicHeader path={path} />
    <main id="main" className={`public-page page-${page.kind}`}>
      <section className="page-hero">
        <div className="page-breadcrumb"><a href="/">{data.labels.breadcrumbsHome}</a><span aria-hidden="true">/</span><span>{page.eyebrow.split(' / ')[0].toLowerCase()}</span></div>
        <Reveal><p className="eyebrow"><span className="status-dot" />{page.eyebrow}</p></Reveal>
        <h1 tabIndex={-1}>{page.title}<em>{page.accent}</em></h1>
        <Reveal delay={appConfig.motion.staggerSeconds}><p className="page-intro">{page.description}</p></Reveal>
        {legal && <p className="page-updated">{data.labels.updated} / {data.updated}</p>}
        {page.kind === 'platform' && <div className="page-hero-actions"><a className="button" href="/engine">{data.labels.explore}<Arrow /></a><a className="text-link" href="#evidence">{data.labels.how}<ArrowDown size={16} aria-hidden="true" /></a></div>}
        {page.kind === 'about' && <div className="about-index"><span>{data.labels.evidenceIndex}</span><span>{data.labels.judgmentIndex}</span><span>{data.labels.progressIndex}</span></div>}
      </section>

      {page.kind === 'platform' && <section className="platform-process" aria-label={data.labels.workflow}>
        {data.platformSteps.map((step) => <Reveal key={step.number}><article><span className="process-number">{step.number}</span><h2>{step.title}</h2><p>{step.detail}</p><ArrowRight aria-hidden="true" size={18} /></article></Reveal>)}
      </section>}

      {page.plans && <section className="pricing-plans" aria-label={data.labels.accessOptions}>
        {page.plans.map((plan) => <Reveal key={plan.name} className={`pricing-card ${plan.featured ? 'featured' : ''}`}>
          <div className="plan-heading"><p className="eyebrow">{plan.label}</p>{plan.featured && <span className="plan-badge">{data.labels.available}</span>}</div>
          <h2>{plan.name}</h2><div className="plan-price">{plan.price}</div><p className="plan-period">{plan.period}</p>
          <p className="plan-description">{plan.description}</p><ul>{plan.features.map((feature) => <li key={feature}><Check size={16} aria-hidden="true" /><span>{feature}</span></li>)}</ul>
          <a className={`button ${plan.featured ? 'button-light' : ''}`} href={plan.href}>{plan.action}<Arrow /></a>
        </Reveal>)}
      </section>}

      {page.quote && <section className="about-statement"><div className="about-image"><img src={appConfig.media.hero} alt={data.labels.productImageAlt} /><span className="eyebrow">{data.labels.productImageCaption}</span></div>
        <div className="about-quote"><span className="quote-mark" aria-hidden="true">“</span><blockquote>{page.quote}</blockquote><p>{data.labels.principle}</p><div className="about-signature">{data.labels.aboutSignature}</div></div></section>}

      {page.channels && <section className="contact-layout" aria-label={data.labels.contactOptions}>
        <div className="contact-address"><Mail size={30} strokeWidth={1} aria-hidden="true" /><p className="eyebrow">{data.labels.directContact}</p><a className="contact-email" href={emailHref(data.labels.requestSubject)}>{data.contact.email}</a><p>{data.contact.operator}<br />{data.contact.name}</p><button className="text-link" onClick={() => void copyEmail()}>{data.labels.copy}<Copy size={14} aria-hidden="true" /></button><p className="contact-response">{data.contact.response}</p></div>
        <div className="contact-channels">{page.channels.map((channel, index) => <a href={emailHref(channel.subject)} key={channel.title}><span className="channel-number">0{index + 1}</span><div><h2>{channel.title}</h2><p>{channel.description}</p></div><Arrow /></a>)}</div>
      </section>}

      {page.kind === 'legal-hub' && <section className="legal-grid" aria-label={data.labels.legalDocuments}>{data.legalLinks.map((link, index) => <Reveal key={link.href}><a href={link.href}><span className="eyebrow">0{index + 1} / {index > 2 && index < 5 ? data.labels.regionalGuidance : data.labels.notice}</span><h2>{link.label}</h2><p>{link.description}</p><Arrow /></a></Reveal>)}</section>}

      <div className={`page-reading-layout ${legal || page.kind === 'docs' ? 'with-sidebar' : ''}`}>
        {(legal || page.kind === 'docs') && <aside className="page-toc" aria-label={data.labels.contents}><p className="eyebrow">{data.labels.contents}</p><nav>{page.sections.map((section) => <a href={`#${section.id}`} key={section.id}>{section.title}</a>)}</nav><a className="toc-contact" href="/contact">{data.labels.questions}<Arrow size={15} /></a></aside>}
        <div className="page-reading">
          {page.storage && <section className="storage-table" aria-label={data.labels.browserStorage}><div className="storage-table-head"><span>{data.labels.storage}</span><span>{data.labels.storagePurpose}</span></div>{page.storage.map((storage) => <div className="storage-row" key={storage.name}><div><code>{storage.name}</code><small>{storage.type}</small></div><div><p>{storage.purpose}</p><small>{storage.duration}</small></div></div>)}</section>}
          {page.sections.map((section, index) => <section id={section.id} key={section.id} className="page-section">
            {!legal && page.kind !== 'docs' && <span className="section-index">0{index + 1}</span>}
            <div><h2>{section.title}</h2>{section.body?.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
              {section.items && <ul className="page-list">{section.items.map((item) => <li key={item}><span className="list-mark" aria-hidden="true">↗</span><span>{item}</span></li>)}</ul>}
              {page.kind === 'cookies' && section.id === 'controls' && <button className="button" onClick={clearSample}>{data.labels.clear}<Arrow /></button>}
            </div>
          </section>)}
          {page.references && <section className="page-references" aria-label={data.labels.sources}><p className="eyebrow">{data.labels.references}</p>{page.references.map((reference) => <a key={reference.href} href={reference.href} target="_blank" rel="noopener noreferrer">{reference.label}<Arrow size={15} /></a>)}</section>}
          {legal && <div className="legal-scope-note"><ShieldCheck size={18} aria-hidden="true" /><p>{data.labels.legalNotice}</p></div>}
          {page.note && <p className="page-note">{page.note}</p>}
        </div>
      </div>
      {page.kind === 'docs' && <section className="docs-related" aria-label={data.labels.related}>{data.docsLinks.map((link) => <a href={link.href} key={link.href}><FileText size={18} strokeWidth={1.3} aria-hidden="true" /><span>{link.label}</span><Arrow /></a>)}</section>}
      <div className="page-action-status" role="status" aria-live="polite">{notice}</div>
      {!legal && page.kind !== 'contact' && <section className="page-closing"><p className="eyebrow">{data.labels.nextStep}</p><h2>{data.labels.closingFirst}<br /><em>{data.labels.closingSecond}</em></h2><a className="button" href={page.kind === 'pricing' ? '/engine' : '/contact'}>{page.kind === 'pricing' ? data.labels.explore : data.labels.contact}<Arrow /></a></section>}
    </main><PublicFooter />
  </>;
}
