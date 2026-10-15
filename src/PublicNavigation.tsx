import { useEffect, useId, useRef, useState } from 'react';
import { ArrowUpRight, Menu, X } from 'lucide-react';
import { Brand } from './components';
import { content } from './content';
import navigation from './data/public-navigation.json';
import './public-navigation.css';

interface HeaderProps { path?: string; onOpenWorkspace?: () => void }

if (navigation.groups.length !== 4 || [...navigation.primary, ...navigation.groups.flatMap((group) => group.links)]
  .some((link) => !link.label.trim() || !/^\/[A-Za-z0-9/_.-]+$/.test(link.href))) {
  throw new Error('Public navigation requires named local routes and four footer groups.');
}

export function PublicHeader({ path = window.location.pathname, onOpenWorkspace }: HeaderProps) {
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  const header = useRef<HTMLElement>(null);
  const menuId = useId();
  useEffect(() => {
    if (!open) return;
    const closeOutside = (event: PointerEvent) => {
      if (event.target instanceof Node && !header.current?.contains(event.target)) setOpen(false);
    };
    const closeEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setOpen(false); button.current?.focus(); }
    };
    document.addEventListener('pointerdown', closeOutside);
    document.addEventListener('keydown', closeEscape);
    return () => {
      document.removeEventListener('pointerdown', closeOutside);
      document.removeEventListener('keydown', closeEscape);
    };
  }, [open]);
  const workspace = <a className="button button-small public-workspace" href={navigation.workspacePath} aria-label={navigation.workspaceLabel}
    onClick={(event) => {
      if (onOpenWorkspace && event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) {
        event.preventDefault(); setOpen(false); onOpenWorkspace();
      }
    }}><span className="public-workspace-full">{navigation.workspaceLabel}</span><span className="public-workspace-short" aria-hidden="true">{navigation.workspaceShortLabel}</span><ArrowUpRight size={16} aria-hidden="true" /></a>;
  return <header className="site-header public-header" ref={header}
    onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false); }}>
    <a className="brand-link" href="/" aria-label={navigation.homeLabel}><Brand /></a>
    <nav className="public-desktop-nav" aria-label={navigation.mainLabel}>
      {navigation.primary.map((item) => <a href={item.href} key={item.href} aria-current={path === item.href ? 'page' : undefined}>{item.label}</a>)}
    </nav>
    <div className="public-header-action">{workspace}</div>
    <button ref={button} className="icon-button public-menu-toggle" aria-label={open ? navigation.closeMenu : navigation.openMenu}
      aria-expanded={open} aria-controls={menuId} onClick={() => setOpen(!open)}>
      {open ? <X size={22} aria-hidden="true" /> : <Menu size={22} aria-hidden="true" />}
    </button>
    <nav id={menuId} className="public-menu-panel" aria-label={navigation.mobileLabel} hidden={!open}>
      {navigation.primary.map((item) => <a href={item.href} key={item.href} aria-current={path === item.href ? 'page' : undefined} onClick={() => setOpen(false)}>{item.label}<ArrowUpRight size={18} aria-hidden="true" /></a>)}
    </nav>
  </header>;
}

export function PublicFooter() {
  return <footer className="public-footer">
    <div className="public-footer-main">
      <div className="public-footer-brand"><a className="brand-link" href="/" aria-label={navigation.homeLabel}><Brand /></a>
        <p>{navigation.footerDescription}</p><span>{navigation.operator}</span>
      </div>
      <nav className="public-footer-groups" aria-label={navigation.footerLabel}>
        {navigation.groups.map((group) => <div className="public-footer-group" key={group.label}>
          <h2>{group.label}</h2>{group.links.map((link) => <a key={link.href} href={link.href}>{link.label}</a>)}
        </div>)}
      </nav>
    </div>
    <div className="public-footer-bottom"><span>{content.footer.copyright}</span><span>{navigation.status}</span></div>
  </footer>;
}
