import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { motion } from 'motion/react';
import { useMotionPreference } from './useMotionPreference';
import { ArrowUpRight, X } from 'lucide-react';
import { appConfig } from './config';
import { content } from './content';

export function Brand({ inverse = false }: { inverse?: boolean }) {
  return <span className={`brand ${inverse ? 'brand-inverse' : ''}`}>
    <svg viewBox="0 0 34 35" fill="none" aria-hidden="true"><path d="m3 9 12 22L30 4M12 8l8 14" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
    <span>{content.brand}<span className="brand-suffix">{content.brandSuffix}</span></span>
  </span>;
}

export function Arrow({ size = 18 }: { size?: number }) { return <ArrowUpRight size={size} strokeWidth={1.5} aria-hidden="true" />; }

export function Reveal({ children, className = '', delay = 0 }: { children: ReactNode; className?: string; delay?: number }) {
  const reduced = useMotionPreference();
  return <motion.div className={className} initial={reduced ? false : { opacity: 0, y: appConfig.motion.revealDistance }}
    whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.12 }}
    transition={{ duration: reduced ? 0 : appConfig.motion.revealSeconds, delay, ease: appConfig.motion.ease }}>{children}</motion.div>;
}

export function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialog?.showModal();
    return () => { document.body.style.overflow = overflow; dialog?.close(); if (previous?.isConnected) previous.focus(); };
  }, []);
  useEffect(() => { ref.current?.querySelector<HTMLElement>('button')?.focus(); }, [title]);
  return <dialog ref={ref} className="dialog" aria-labelledby="dialog-title" onCancel={(event) => { event.preventDefault(); onClose(); }}
    onKeyDown={(event) => {
      if (event.key !== 'Tab') return;
      const dialog = ref.current;
      const focusable = [...(dialog?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]') ?? [])].filter((element) => element.getClientRects().length > 0);
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) { event.preventDefault(); return; }
      if (event.shiftKey && (document.activeElement === first || !dialog?.contains(document.activeElement))) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && (document.activeElement === last || !dialog?.contains(document.activeElement))) { event.preventDefault(); first.focus(); }
    }}
    onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <div className="dialog-inner" data-lenis-prevent>
      <div className="dialog-header"><p className="eyebrow">{content.ui.preview}</p><button className="icon-button" aria-label={content.ui.close} onClick={onClose}><X size={22} aria-hidden="true" /></button></div>
      <h2 id="dialog-title">{title}</h2>{children}
    </div>
  </dialog>;
}
